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
- --host compares every variable an image: line names in a live .env with the
  pin in .env.example: a difference is a hint and leaves the exit status alone
- --host names the Docker and VPN package versions below their minimum,
  live-restore off, a docker.service bound to tailscaled and the package
  updates apt has pending — hints that leave the exit status alone
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


class ImagePins(Scratch):
    def pinned(self, project, example, live):
        d = self.root / "apps" / project
        d.mkdir(parents=True)
        (d / "docker-compose.yml").write_text(
            "services:\n  app:\n    image: example/app:${APP_TAG}\n  db:\n    image: ${DB_IMAGE:-postgres:18}\n",
            encoding="utf-8")
        (d / ".env.example").write_text(example, encoding="utf-8")
        if live is not None:
            (d / ".env").write_text(live, encoding="utf-8")

    def test_a_tag_older_than_the_pin_is_named(self):
        self.pinned("old", "APP_TAG=2.4.1\nDB_IMAGE=postgres:18.6\nAPP_HOST=a.example.com\n",
                    'APP_TAG="2.0.0"\nDB_IMAGE=postgres:18.6\nAPP_HOST=b.example.com\n')
        rc, out = self.run_tool("--host")
        self.assertEqual(rc, 0, out)
        self.assertIn("apps/old APP_TAG=2.0.0 — this checkout pins 2.4.1", out)
        self.assertNotIn("DB_IMAGE=", out)
        self.assertNotIn("APP_HOST", out)   # not an image variable
        self.assertIn("a hint, not a failure", out)

    def test_the_pins_alone_say_as_pinned(self):
        self.pinned("same", "APP_TAG=2.4.1\n", "APP_TAG=2.4.1\n")
        rc, out = self.run_tool("--host")
        self.assertEqual(rc, 0, out)
        self.assertIn("as pinned — the .env of 1 stack(s) names the images .env.example pins", out)

    def test_without_a_live_env_nothing_is_compared(self):
        self.pinned("example", "APP_TAG=2.4.1\n", None)
        rc, out = self.run_tool("--host")
        self.assertIn("Image pins", out)
        self.assertIn("no stack has a .env — nothing to compare", out)


STUB_DOCKER = """#!/bin/sh
case "$1 $2" in
  "version --format") echo "$STUB_ENGINE";;
  "info --format") echo "$STUB_LIVE_RESTORE";;
  "compose version") echo v5.7.0;;
esac
"""
STUB_APT = """#!/bin/sh
echo "Listing..."
echo "docker-ce/trixie 5:29.10.0-1~debian.13~trixie amd64 [upgradable from: 5:29.9.3-1~debian.13~trixie]"
echo "curl/trixie 8.14.1-2 amd64 [upgradable from: 8.14.1-1]"
"""


class HostPackages(Scratch):
    def run_with_stubs(self, engine, live_restore, requires, apt=True):
        bin_dir = self.root / "stubs"
        bin_dir.mkdir()
        stubs = {
            "docker": STUB_DOCKER,
            "containerd": "#!/bin/sh\necho 'containerd containerd.io v2.4.2 abc'\n",
            "tailscale": "#!/bin/sh\necho 1.104.5\necho 'tailscale commit: x'\n",
            "systemctl": f"#!/bin/sh\necho 'Requires={requires}'\necho BindsTo=\necho PartOf=\n",
        }
        if apt:
            stubs["apt"] = STUB_APT
        for name, body in stubs.items():
            (bin_dir / name).write_text(body, encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        env = dict(os.environ, HOST_FILES_PREFIX=str(self.root / "host"),
                   STUB_ENGINE=engine, STUB_LIVE_RESTORE=live_restore,
                   PATH=f"{bin_dir}:/usr/bin:/bin")
        r = subprocess.run(["bash", str(self.root / "scripts" / "overview.sh"), "--host"],
                           capture_output=True, text=True, cwd=str(self.root), env=env)
        return r.returncode, ANSI.sub("", r.stdout + r.stderr)

    def test_an_old_engine_without_live_restore_bound_to_tailscaled_is_named(self):
        rc, out = self.run_with_stubs("27.5.1", "false", "containerd.service tailscaled.service")
        self.assertEqual(rc, 0, out)
        self.assertIn("Docker Engine    27.5.1 — below the minimum 28.0", out)
        self.assertIn("Compose          5.7.0", out)
        self.assertIn("live-restore off", out)
        self.assertIn("docker.service requires tailscaled", out)
        self.assertIn("docker-ce 5:29.10.0-1~debian.13~trixie — installed 5:29.9.3-1~debian.13~trixie", out)
        self.assertNotIn("curl", out)   # not a Docker or VPN package

    def test_a_current_host_reports_no_warning(self):
        rc, out = self.run_with_stubs("29.10.0", "true", "containerd.service", apt=False)
        self.assertEqual(rc, 0, out)
        self.assertIn("Docker Engine    29.10.0\n", out)
        self.assertIn("live-restore on", out)
        self.assertNotIn("requires tailscaled", out)
        self.assertNotIn("below the minimum", out)


if __name__ == "__main__":
    unittest.main()
