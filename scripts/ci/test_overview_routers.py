#!/usr/bin/env python3
"""scripts/overview.sh — the Traefik router report, against a scratch checkout.

- the summary counts routers, the stacks still on the old names, the empty
  positions Traefik would disable, and the routers naming a TLS option other
  than the deployment standard
- --routers lists every router with its four positions, read from the
  compose labels with the stack's .env (or .env.example) values
- --host compares the TLS option per host name across the stacks with a live
  .env: two different options for one name are reported and exit 1; the
  example files are not compared
- an unknown option is refused

Run:
    python3 scripts/ci/test_overview_routers.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts" / "overview.sh"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

COMPOSE = """services:
  {project}-app:
    image: example/app:1.0
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${{COMPOSE_PROJECT_NAME}}.rule=Host(`${{APP_TRAEFIK_HOST}}`)"
      - "traefik.http.routers.${{COMPOSE_PROJECT_NAME}}.entrypoints=websecure"
      - "traefik.http.routers.${{COMPOSE_PROJECT_NAME}}.tls=true"
{tls}      - "traefik.http.routers.${{COMPOSE_PROJECT_NAME}}.middlewares={mw}"
      - "traefik.http.services.${{COMPOSE_PROJECT_NAME}}.loadbalancer.server.port=8080"
"""
TLS_LABEL = '      - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"\n'
MODEL_MW = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
OLD_MW = "${APP_TRAEFIK_THREAT}${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"


class Scratch(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "scripts").mkdir()
        shutil.copy(TOOL, self.root / "scripts" / "overview.sh")
        # --host runs the host-files check first; a stub keeps /etc out of the test.
        (self.root / "scripts" / "host-files.sh").write_text("#!/usr/bin/env bash\necho '  (host files: stub)'\nexit 0\n", encoding="utf-8")
        core = self.root / "core" / "traefik"
        core.mkdir(parents=True)
        (core / ".env.example").write_text("COMPOSE_PROJECT_NAME=traefik\nTLS_DEFAULT_OPTION=tls-standard\n", encoding="utf-8")
        (core / "docker-compose.yml").write_text("services:\n  traefik:\n    image: traefik:v3.7\n", encoding="utf-8")

    def stack(self, root, project, env, mw, tls_label=False, live=False):
        d = self.root / root / project
        d.mkdir(parents=True, exist_ok=True)
        (d / (".env" if live else ".env.example")).write_text(f"COMPOSE_PROJECT_NAME={project}\n" + env, encoding="utf-8")
        (d / "docker-compose.yml").write_text(COMPOSE.format(project=project, mw=mw, tls=TLS_LABEL if tls_label else ""), encoding="utf-8")
        return d

    def run_tool(self, *args):
        env = dict(os.environ, HOST_FILES_PREFIX=str(self.root / "host"))
        r = subprocess.run(["bash", str(self.root / "scripts" / "overview.sh"), *args],
                           capture_output=True, text=True, cwd=str(self.root), env=env)
        return r.returncode, ANSI.sub("", r.stdout + r.stderr)


class Summary(Scratch):
    def test_old_names_empty_positions_and_tls_exceptions_are_counted(self):
        self.stack("apps", "old", "APP_TRAEFIK_HOST=old.example.com\nAPP_TRAEFIK_TLS_OPTION=tls-aplus\nAPP_TRAEFIK_ACCESS=acc-public\nAPP_TRAEFIK_SECURITY=sec-2\nAPP_TRAEFIK_THREAT=\n", OLD_MW, tls_label=True)
        self.stack("apps", "new", "APP_TRAEFIK_HOST=new.example.com\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-standard\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\n", MODEL_MW)
        self.stack("apps", "bare", "APP_TRAEFIK_HOST=bare.example.com\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\n", MODEL_MW)
        self.stack("business", "strict", "APP_TRAEFIK_HOST=strict.example.com\nAPP_TRAEFIK_TLS_OPTION=tls-strict\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-strict\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\n", MODEL_MW, tls_label=True)
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("4 router(s) in 4 stack(s) · TLS standard: tls-standard (TLS_DEFAULT_OPTION, core/traefik/.env.example)", out)
        self.assertIn("old names:       1 router(s) in 1 stack(s)", out)
        self.assertIn("empty positions: 1 router(s)", out)
        self.assertIn("TLS exceptions:  1 router(s) — strict:strict=tls-strict", out)
        self.assertNotIn("STACK", out, "the table needs --routers")

    def test_a_tree_in_the_model_reports_none_of_each(self):
        self.stack("apps", "new", "APP_TRAEFIK_HOST=new.example.com\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-standard\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\n", MODEL_MW)
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("old names:       none", out)
        self.assertIn("empty positions: none", out)
        self.assertIn("TLS exceptions:  none", out)


class Table(Scratch):
    def test_routers_lists_the_positions_from_the_labels_and_the_env(self):
        self.stack("apps", "old", "APP_TRAEFIK_HOST=old.example.com\nAPP_TRAEFIK_TLS_OPTION=tls-modern\nAPP_TRAEFIK_ACCESS=acc-local\nAPP_TRAEFIK_SECURITY=sec-3-spa\nAPP_TRAEFIK_THREAT=\n", OLD_MW, tls_label=True)
        self.stack("apps", "gate", "APP_TRAEFIK_HOST=gate.example.com\nAPP_TRAEFIK_ACCESS=access-lan-vpn\nAPP_TRAEFIK_LIMIT=limit-sync\nAPP_TRAEFIK_HEADERS=headers-application-owned\nAPP_TRAEFIK_AUTH=gate-auth@docker\n", MODEL_MW)
        self.stack("apps", "bare", "APP_TRAEFIK_HOST=bare.example.com\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-standard\nAPP_TRAEFIK_HEADERS=\nAPP_TRAEFIK_AUTH=auth-none@file\n", MODEL_MW)
        rc, out = self.run_tool("--routers")
        self.assertEqual(rc, 0, out)
        rows = {line.split()[1]: line.split() for line in out.splitlines() if line.startswith(" apps/")}
        self.assertEqual(rows["old"][:7], ["apps/old", "old", "acc-local", "-", "sec-3-spa", "-", "tls-modern"])
        self.assertIn("old names; TLS exception", out)
        self.assertEqual(rows["gate"][:7], ["apps/gate", "gate", "access-lan-vpn", "limit-sync", "headers-application-owned", "gate-auth@docker", "default"])
        self.assertEqual(rows["bare"][:7], ["apps/bare", "bare", "access-vpn", "limit-standard", "-", "auth-none@file", "default"])
        self.assertIn("empty: APP_TRAEFIK_HEADERS", out)
        self.assertNotIn("--routers lists", out)


class HostCheck(Scratch):
    LIVE = "APP_TRAEFIK_HOST=shared.example.org\nAPP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-standard\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\n"

    def test_two_live_stacks_naming_different_options_for_one_host_exit_1(self):
        self.stack("apps", "one", self.LIVE + "APP_TRAEFIK_TLS_OPTION=tls-strict\n", MODEL_MW, tls_label=True, live=True)
        self.stack("apps", "two", self.LIVE, MODEL_MW, live=True)
        rc, out = self.run_tool("--host")
        self.assertEqual(rc, 1, out)
        self.assertIn("(host files: stub)", out)
        self.assertIn("shared.example.org is served with different options", out)
        self.assertIn("tls-strict", out)
        self.assertIn("default (tls-standard)", out)
        self.assertIn("apps/one:one", out)
        self.assertIn("apps/two:two", out)

    def test_the_same_option_passes_and_example_files_are_not_compared(self):
        self.stack("apps", "one", self.LIVE, MODEL_MW, live=True)
        self.stack("apps", "two", self.LIVE, MODEL_MW, live=True)
        self.stack("apps", "ex", self.LIVE + "APP_TRAEFIK_TLS_OPTION=tls-strict\n", MODEL_MW, tls_label=True)
        rc, out = self.run_tool("--host")
        self.assertEqual(rc, 0, out)
        self.assertIn("no conflict — one TLS option per host name", out)

    def test_without_any_live_env_there_is_nothing_to_compare(self):
        self.stack("apps", "ex", self.LIVE, MODEL_MW)
        rc, out = self.run_tool("--host")
        self.assertEqual(rc, 0, out)
        self.assertIn("no stack has a .env — nothing to compare", out)

    def test_an_unknown_option_is_refused(self):
        rc, out = self.run_tool("--hosts")
        self.assertEqual(rc, 2, out)
        self.assertIn("usage:", out)


if __name__ == "__main__":
    unittest.main()
