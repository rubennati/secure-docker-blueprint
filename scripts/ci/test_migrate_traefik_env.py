#!/usr/bin/env python3
"""scripts/migrate-traefik-env.sh — a deployment's .env files from the
sec-*/acc-* names to the middleware model, against scratch copies.

- every old value the templates define is mapped: each sec-* chain of
  security-chains.yml.tmpl, each acc-* policy of access.yml.tmpl, the three
  TLS names — none is refused
- the dry run writes nothing; --write keeps the previous file as
  .env.pre-model and the second run finds nothing to change
- a value the script does not know stops the run before anything is written;
  so does a .pre-model file left by a previous run
- the shape of each change: SECURITY becomes LIMIT + HEADERS (+ AUTH where the
  file has none), THREAT is removed, quotes are kept, comments and order stay
- the notes name what is not a rename: the wider bucket, the HSTS extension
  the sec-3 tier sent, the frame and CSP blocks that move to the compose file
- core/traefik/.env: the dashboard's option renamed, HSTS_MAX_AGE added

Run:
    python3 scripts/ci/test_migrate_traefik_env.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts" / "migrate-traefik-env.sh"
TEMPLATES = REPO / "core" / "traefik" / "ops" / "templates" / "dynamic"

STACK_ENV = """# --- Project ---
COMPOSE_PROJECT_NAME=demo

# --- Domain & Traefik ---
APP_TRAEFIK_HOST=demo.example.com
APP_TRAEFIK_CERT_RESOLVER=cloudflare-dns
APP_TRAEFIK_TLS_OPTION={tls}
APP_TRAEFIK_ACCESS={access}
APP_TRAEFIK_SECURITY={chain}
APP_TRAEFIK_THREAT={threat}
TRAEFIK_NETWORK=proxy-public

# --- Images ---
APP_TAG=1.0.0
"""


def old_names():
    chains = re.findall(r"^    (sec-[a-z0-9-]+):", (TEMPLATES / "security-chains.yml.tmpl").read_text(encoding="utf-8"), re.M)
    policies = re.findall(r"^    (acc-[a-z0-9-]+):", (TEMPLATES / "access.yml.tmpl").read_text(encoding="utf-8"), re.M)
    return sorted(set(chains)), sorted(set(policies)), ["tls-basic", "tls-aplus", "tls-modern"]


class Scratch(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "scripts").mkdir()
        shutil.copy(TOOL, self.root / "scripts" / "migrate-traefik-env.sh")

    def stack(self, name, text):
        d = self.root / "apps" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / ".env").write_text(text, encoding="utf-8")
        return d

    def run_tool(self, *args):
        r = subprocess.run(["bash", str(self.root / "scripts" / "migrate-traefik-env.sh"), *args],
                           capture_output=True, text=True, cwd=str(self.root))
        return r.returncode, r.stdout + r.stderr

    def values(self, path):
        out = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                out[k] = v
        return out


class EveryOldValue(Scratch):
    def test_every_chain_policy_and_tls_name_of_the_templates_is_mapped(self):
        chains, policies, tls = old_names()
        self.assertGreaterEqual(len(chains), 14, chains)
        self.assertEqual(len(policies), 5, policies)
        targets = []
        for i, chain in enumerate(chains):
            d = self.stack(f"c{i}", STACK_ENV.format(tls=tls[i % 3], access=policies[i % 5], chain=chain, threat=""))
            targets.append(str(d))
        rc, out = self.run_tool(*targets)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("!", out.replace("auth-none@file", ""), out)
        for i, chain in enumerate(chains):
            self.assertIn(f"- APP_TRAEFIK_SECURITY={chain}\n", out)
            self.assertRegex(out, rf"\+ APP_TRAEFIK_LIMIT=limit-(none|standard|extra-large|sync|strict)\n  \+ APP_TRAEFIK_HEADERS=headers-(standard|none)")
        for policy in policies:
            self.assertRegex(out, rf"- APP_TRAEFIK_ACCESS={policy}\n  \+ APP_TRAEFIK_ACCESS=access-(public|lan|vpn|lan-vpn|blocked)")
        for name in tls:
            self.assertRegex(out, rf"- APP_TRAEFIK_TLS_OPTION={name}\n  \+ APP_TRAEFIK_TLS_OPTION=tls-(compatible|standard|strict)")
        self.assertIn("dry run, nothing written", out)

    def test_the_decided_values_per_name(self):
        expect = {
            "sec-0": ("limit-none", "headers-none"), "sec-1": ("limit-none", "headers-standard"),
            "sec-2": ("limit-standard", "headers-standard"), "sec-2-spa": ("limit-standard", "headers-standard"),
            "sec-2-spa-xl": ("limit-extra-large", "headers-standard"), "sec-2-sync": ("limit-sync", "headers-standard"),
            "sec-3": ("limit-standard", "headers-standard"), "sec-3e-sync": ("limit-sync", "headers-standard"),
            "sec-4": ("limit-strict", "headers-standard"), "sec-5": ("limit-strict", "headers-standard"),
        }
        access = {"acc-public": "access-public", "acc-local": "access-lan", "acc-tailscale": "access-vpn",
                  "acc-private": "access-lan-vpn", "acc-deny": "access-blocked"}
        for chain, (limit, headers) in expect.items():
            d = self.stack("x", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain=chain, threat=""))
            rc, out = self.run_tool(str(d))
            self.assertEqual(rc, 0, out)
            self.assertIn(f"+ APP_TRAEFIK_LIMIT={limit}\n  + APP_TRAEFIK_HEADERS={headers}\n", out, chain)
        for old, new in access.items():
            d = self.stack("x", STACK_ENV.format(tls="tls-aplus", access=old, chain="sec-2", threat=""))
            rc, out = self.run_tool(str(d))
            self.assertIn(f"- APP_TRAEFIK_ACCESS={old}\n  + APP_TRAEFIK_ACCESS={new}\n", out, old)
        for old, new in (("tls-basic", "tls-compatible"), ("tls-aplus", "tls-standard"), ("tls-modern", "tls-strict")):
            d = self.stack("x", STACK_ENV.format(tls=old, access="acc-public", chain="sec-2", threat=""))
            rc, out = self.run_tool(str(d))
            self.assertIn(f"- APP_TRAEFIK_TLS_OPTION={old}\n  + APP_TRAEFIK_TLS_OPTION={new}\n", out, old)


class WriteAndRefuse(Scratch):
    def test_dry_run_writes_nothing_and_write_keeps_the_previous_file(self):
        d = self.stack("demo", STACK_ENV.format(tls="tls-basic", access="acc-tailscale", chain="sec-3e", threat="crowdsec-basic@file,"))
        before = (d / ".env").read_text(encoding="utf-8")
        rc, out = self.run_tool(str(d))
        self.assertEqual(rc, 0, out)
        self.assertEqual((d / ".env").read_text(encoding="utf-8"), before)
        self.assertFalse((d / ".env.pre-model").exists())

        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 0, out)
        self.assertIn("written", out)
        self.assertEqual((d / ".env.pre-model").read_text(encoding="utf-8"), before)
        v = self.values(d / ".env")
        self.assertEqual(v["APP_TRAEFIK_TLS_OPTION"], "tls-compatible")
        self.assertEqual(v["APP_TRAEFIK_ACCESS"], "access-vpn")
        self.assertEqual(v["APP_TRAEFIK_LIMIT"], "limit-standard")
        self.assertEqual(v["APP_TRAEFIK_HEADERS"], "headers-standard")
        self.assertEqual(v["APP_TRAEFIK_AUTH"], "auth-none@file")
        self.assertNotIn("APP_TRAEFIK_SECURITY", v)
        self.assertNotIn("APP_TRAEFIK_THREAT", v)
        text = (d / ".env").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# --- Project ---\nCOMPOSE_PROJECT_NAME=demo\n"), "comments and order stay")
        self.assertIn("APP_TRAEFIK_ACCESS=access-vpn\nAPP_TRAEFIK_LIMIT=limit-standard\nAPP_TRAEFIK_HEADERS=headers-standard\nAPP_TRAEFIK_AUTH=auth-none@file\nTRAEFIK_NETWORK=proxy-public\n", text)
        self.assertIn("named the bouncer for this router", out)

    def test_the_second_run_finds_nothing_to_change(self):
        d = self.stack("demo", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain="sec-2", threat=""))
        self.run_tool("--write", str(d))
        (d / ".env.pre-model").unlink()
        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 0, out)
        self.assertIn("already in the model — nothing to change", out)
        self.assertIn("nothing to write", out)
        self.assertFalse((d / ".env.pre-model").exists())

    def test_an_unknown_value_stops_the_run_before_anything_is_written(self):
        good = self.stack("good", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain="sec-2", threat=""))
        bad = self.stack("bad", STACK_ENV.format(tls="tls-aplus", access="acc-everyone", chain="sec-7", threat=""))
        rc, out = self.run_tool("--write", str(good), str(bad))
        self.assertEqual(rc, 2, out)
        self.assertIn("! APP_TRAEFIK_ACCESS=acc-everyone — not an access policy this script knows", out)
        self.assertIn("! APP_TRAEFIK_SECURITY=sec-7 — not a security chain this script knows", out)
        self.assertIn("nothing written", out)
        self.assertFalse((good / ".env.pre-model").exists())
        self.assertIn("APP_TRAEFIK_SECURITY=sec-2", (good / ".env").read_text(encoding="utf-8"))

    def test_a_pre_model_file_left_behind_is_refused(self):
        d = self.stack("demo", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain="sec-2", threat=""))
        (d / ".env.pre-model").write_text("old\n", encoding="utf-8")
        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 2, out)
        self.assertIn(".pre-model exists", out)
        self.assertIn("APP_TRAEFIK_SECURITY=sec-2", (d / ".env").read_text(encoding="utf-8"))
        self.assertEqual((d / ".env.pre-model").read_text(encoding="utf-8"), "old\n")

    def test_a_missing_file_and_an_unknown_option_are_refused(self):
        rc, out = self.run_tool(str(self.root / "apps" / "none"))
        self.assertEqual(rc, 2, out)
        self.assertIn("no such file", out)
        rc, out = self.run_tool("--force", str(self.root))
        self.assertEqual(rc, 2, out)
        rc, out = self.run_tool()
        self.assertEqual(rc, 2, out)


class Shape(Scratch):
    def test_a_second_access_variable_and_an_existing_auth_are_handled(self):
        text = STACK_ENV.format(tls="tls-basic", access="acc-private", chain="sec-2", threat="") \
            + "APP_TRAEFIK_API_ACCESS=acc-tailscale\nCLIENT_TRAEFIK_ACCESS=acc-deny\nAPP_TRAEFIK_AUTH=demo-auth@docker\n"
        d = self.stack("shlink", text)
        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 0, out)
        v = self.values(d / ".env")
        self.assertEqual(v["APP_TRAEFIK_API_ACCESS"], "access-vpn")
        self.assertEqual(v["CLIENT_TRAEFIK_ACCESS"], "access-blocked")
        self.assertEqual(v["APP_TRAEFIK_AUTH"], "demo-auth@docker", "an existing gate is kept")
        self.assertEqual((d / ".env").read_text(encoding="utf-8").count("APP_TRAEFIK_AUTH="), 1)

    def test_quotes_are_kept_and_a_trailing_comment_does_not_confuse_the_value(self):
        d = self.stack("q", 'COMPOSE_PROJECT_NAME=q\nAPP_TRAEFIK_ACCESS="acc-local"\nAPP_TRAEFIK_SECURITY=\'sec-4\'\nAPP_TRAEFIK_TLS_OPTION=tls-modern # consoles\n')
        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 0, out)
        text = (d / ".env").read_text(encoding="utf-8")
        self.assertIn('APP_TRAEFIK_ACCESS="access-lan"\n', text)
        self.assertIn("APP_TRAEFIK_LIMIT='limit-strict'\nAPP_TRAEFIK_HEADERS='headers-standard'\nAPP_TRAEFIK_AUTH='auth-none@file'\n", text)
        self.assertIn("APP_TRAEFIK_TLS_OPTION=tls-strict\n", text)

    def test_crlf_is_read_and_written_as_lf_with_a_note(self):
        d = self.stack("crlf", "COMPOSE_PROJECT_NAME=c\r\nAPP_TRAEFIK_ACCESS=acc-public\r\n")
        rc, out = self.run_tool("--write", str(d))
        self.assertEqual(rc, 0, out)
        self.assertIn("CRLF", out)
        self.assertEqual((d / ".env").read_bytes(), b"COMPOSE_PROJECT_NAME=c\nAPP_TRAEFIK_ACCESS=access-public\n")

    def test_the_notes_name_what_is_not_a_rename(self):
        d = self.stack("n", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain="sec-3e", threat=""))
        rc, out = self.run_tool(str(d))
        self.assertIn("burst of 500 (D3)", out)
        self.assertIn("includeSubDomains and preload", out)
        self.assertIn("hsts-include-subdomains", out)
        self.assertIn("frame-self", out)
        self.assertIn("is the deployment standard", out)
        d = self.stack("n5", STACK_ENV.format(tls="tls-aplus", access="acc-tailscale", chain="sec-5", threat=""))
        rc, out = self.run_tool(str(d))
        self.assertIn("csp-self-only", out)
        d = self.stack("n0", STACK_ENV.format(tls="tls-aplus", access="acc-tailscale", chain="sec-0", threat=""))
        rc, out = self.run_tool(str(d))
        self.assertIn("headers-none still sends the HSTS base", out)
        d = self.stack("nx", STACK_ENV.format(tls="tls-aplus", access="acc-tailscale", chain="sec-2-spa-xl", threat=""))
        rc, out = self.run_tool(str(d))
        self.assertIn("accepted by CI only behind", out)

    def test_the_core_env_renames_the_dashboard_option_and_adds_the_hsts_age(self):
        core = self.root / "core" / "traefik"
        core.mkdir(parents=True)
        (core / ".env").write_text("TLS_DEFAULT_OPTION=tls-aplus\nTRAEFIK_DASHBOARD_TLS_OPTION=tls-modern\nTAILSCALE_CIDR_V4=100.64.0.0/10\n", encoding="utf-8")
        rc, out = self.run_tool("--write", str(core))
        self.assertEqual(rc, 0, out)
        v = self.values(core / ".env")
        self.assertEqual(v["TLS_DEFAULT_OPTION"], "tls-standard")
        self.assertEqual(v["TRAEFIK_DASHBOARD_TLS_OPTION"], "tls-strict")
        self.assertEqual(v["HSTS_MAX_AGE"], "63072000")
        self.assertEqual(v["TAILSCALE_CIDR_V4"], "100.64.0.0/10")
        (core / ".env.pre-model").unlink()
        rc, out = self.run_tool(str(core))
        self.assertIn("already in the model", out)

    def test_all_finds_every_env_under_the_roots(self):
        self.stack("a", STACK_ENV.format(tls="tls-aplus", access="acc-public", chain="sec-2", threat=""))
        b = self.root / "business" / "b"
        b.mkdir(parents=True)
        (b / ".env").write_text("APP_TRAEFIK_ACCESS=acc-deny\n", encoding="utf-8")
        (self.root / "business" / "c").mkdir()
        (self.root / "business" / "c" / ".env.example").write_text("APP_TRAEFIK_ACCESS=acc-deny\n", encoding="utf-8")
        rc, out = self.run_tool("--all")
        self.assertEqual(rc, 0, out)
        self.assertIn("apps/a/.env", out)
        self.assertIn("business/b/.env", out)
        self.assertNotIn("business/c", out, "an example file is not a deployment")
        self.assertIn("2 file(s)", out)


if __name__ == "__main__":
    unittest.main()
