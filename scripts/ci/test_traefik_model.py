#!/usr/bin/env python3
"""The middleware model (Phase 4.1, transition): dynamic/model.yml and the TLS
profiles render beside the names they replace, and nothing old changes.

- the four positions exist: access-*, limit-*, headers-*, auth-none, with the
  decided values; every headers-* profile starts with hsts-base; the empty
  chains (*-none, access-public, headers-application-owned) are valid YAML
- HSTS_MAX_AGE renders into hsts-base and hsts-include-subdomains, defaults
  to two years, and is refused when it is not a number
- tls-profiles.yml carries tls-compatible/standard/strict and Traefik's
  reserved `default` built from TLS_DEFAULT_OPTION; a name from before the
  model is refused with the migration script named
- compress is defined once, in model.yml, with exact exclusions, and the
  websecure entrypoint carries it
- the names the model retired are gone: no access.yml, security-blocks.yml
  or security-chains.yml is rendered, no rendered file defines them, a file
  left from an earlier render is removed by render.sh and refused by
  validate.sh, and the dashboard router carries the four positions

Run:
    python3 scripts/ci/test_traefik_model.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

REPO = Path(__file__).resolve().parents[2]
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")

ACCESS = {"access-public", "access-lan", "access-vpn", "access-lan-vpn", "access-blocked"}
LIMITS = {"limit-none": None, "limit-standard": (125, 500), "limit-extra-large": (125, 1000),
          "limit-sync": (1000, 1000), "limit-strict": (20, 40)}
PROFILES = {"headers-standard": ["hsts-base", "header-nosniff", "header-frame-deny", "header-referrer", "header-permissions"],
            "headers-application-owned": ["hsts-base"],
            "headers-none": ["hsts-base"]}
BLOCKS = {"frame-self", "hsts-include-subdomains", "csp-self-only", "forwarded-proto-https"}
TLS_NEW = {"tls-compatible", "tls-standard", "tls-strict"}
TLS_OLD = {"tls-basic", "tls-aplus", "tls-modern"}
RETIRED = re.compile(r"^    (acc-[a-z-]+|sec-[a-z0-9-]+|hdr-[a-z-]+|rl-[a-z-]+|permissions-policy|csp-enforce|crowdsec-(basic|appsec)|tls-(basic|aplus|modern)):", re.M)


class Model(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "ci" / "check-crowdsec-config.py", tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def render(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        return subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)

    def validate(self):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def dyn(self, name):
        return yaml.safe_load((self.root / "config" / "dynamic" / name).read_text(encoding="utf-8"))

    def test_the_four_positions_render_with_the_decided_values(self):
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mw = self.dyn("model.yml")["http"]["middlewares"]
        self.assertTrue(ACCESS <= set(mw), ACCESS - set(mw))
        self.assertEqual(mw["access-public"]["chain"]["middlewares"], [])
        self.assertIn("127.0.0.1/32", mw["access-blocked"]["ipAllowList"]["sourceRange"])
        self.assertEqual(mw["access-vpn"]["ipAllowList"]["sourceRange"], [BASE_ENV["TAILSCALE_CIDR_V4"], BASE_ENV["TAILSCALE_CIDR_V6"]])
        for name, values in LIMITS.items():
            self.assertIn(name, mw)
            if values is None:
                self.assertEqual(mw[name]["chain"]["middlewares"], [])
            else:
                self.assertEqual((mw[name]["rateLimit"]["average"], mw[name]["rateLimit"]["burst"]), values, name)
        for name, chain in PROFILES.items():
            self.assertEqual(mw[name]["chain"]["middlewares"], chain, name)
        self.assertTrue(BLOCKS <= set(mw), BLOCKS - set(mw))
        self.assertEqual(mw["auth-none"]["chain"]["middlewares"], [])
        self.assertEqual(mw["frame-self"]["headers"]["customFrameOptionsValue"], "SAMEORIGIN")
        self.assertNotIn("stsIncludeSubdomains", mw["hsts-base"]["headers"], "the base never carries includeSubDomains")
        self.assertTrue(mw["hsts-include-subdomains"]["headers"]["stsIncludeSubdomains"])
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_hsts_max_age_renders_defaults_and_is_checked(self):
        self.render(VALID_ENV)
        mw = self.dyn("model.yml")["http"]["middlewares"]
        self.assertEqual(mw["hsts-base"]["headers"]["stsSeconds"], 63072000)
        self.render(dict(VALID_ENV, HSTS_MAX_AGE="31536000"))
        mw = self.dyn("model.yml")["http"]["middlewares"]
        self.assertEqual(mw["hsts-base"]["headers"]["stsSeconds"], 31536000)
        self.assertEqual(mw["hsts-include-subdomains"]["headers"]["stsSeconds"], 31536000)
        r = self.render(dict(VALID_ENV, HSTS_MAX_AGE="2y"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("HSTS_MAX_AGE", r.stdout + r.stderr)

    def test_validate_refuses_a_profile_without_the_hsts_base(self):
        self.render(VALID_ENV)
        f = self.root / "config" / "dynamic" / "model.yml"
        text = f.read_text(encoding="utf-8")
        text = text.replace("    headers-none:\n      chain:\n        middlewares:\n          - hsts-base\n",
                            "    headers-none:\n      chain:\n        middlewares: []\n", 1)
        f.write_text(text, encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("headers-none does not start with hsts-base", v.stdout + v.stderr)

    def test_tls_profiles_carry_the_models_names_and_a_default_from_the_env(self):
        self.render(VALID_ENV)
        opts = self.dyn("tls-profiles.yml")["tls"]["options"]
        self.assertEqual(set(opts), TLS_NEW | {"default"}, "three profiles and the reserved default, no alias")
        self.assertEqual(opts["tls-strict"]["minVersion"], "VersionTLS13")
        self.assertIn("cipherSuites", opts["tls-standard"])
        for value in sorted(TLS_NEW):
            r = self.render(dict(VALID_ENV, TLS_DEFAULT_OPTION=value))
            self.assertEqual(r.returncode, 0, value + r.stdout + r.stderr)
            opts = self.dyn("tls-profiles.yml")["tls"]["options"]
            self.assertEqual(opts["default"], opts[value], value)
            v = self.validate()
            self.assertEqual(v.returncode, 0, value + v.stdout + v.stderr)
        for value in sorted(TLS_OLD):
            r = self.render(dict(VALID_ENV, TLS_DEFAULT_OPTION=value))
            self.assertNotEqual(r.returncode, 0, value)
            self.assertIn("before the middleware model", r.stdout + r.stderr, value)
            self.assertIn("migrate-traefik-env.sh", r.stdout + r.stderr, value)
        r = self.render(dict(VALID_ENV, TLS_DEFAULT_OPTION="tls-aaa"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TLS_DEFAULT_OPTION", r.stdout + r.stderr)

    def test_the_retired_names_are_gone(self):
        """Nothing of the vocabulary before the model is rendered: not the
        three files, not a definition in any file, not an alias."""
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dynamic = self.root / "config" / "dynamic"
        for retired in ("access.yml", "security-blocks.yml", "security-chains.yml"):
            self.assertFalse((dynamic / retired).exists(), retired)
        for f in sorted(dynamic.glob("*.yml")):
            self.assertIsNone(RETIRED.search(f.read_text(encoding="utf-8")), f.name)
        static = yaml.safe_load((self.root / "config" / "traefik.yml").read_text(encoding="utf-8"))
        ep = static["entryPoints"]["websecure"]
        self.assertEqual(ep["http"]["middlewares"], ["compress@file"], "compression at the entrypoint; the threat position only by switch")
        self.assertNotIn("tls", ep["http"], "no entrypoint TLS option — every router takes the file provider's default")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_the_dashboard_router_carries_the_four_positions(self):
        self.render(VALID_ENV)
        router = self.dyn("routers-system.yml")["http"]["routers"]["traefik-dashboard"]
        self.assertEqual(router["middlewares"], ["access-vpn@file", "limit-strict@file", "headers-standard@file", "auth-none@file"])
        self.assertEqual(router["tls"]["options"], BASE_ENV["TRAEFIK_DASHBOARD_TLS_OPTION"])

    def test_a_file_from_before_the_model_is_removed_by_render_and_refused_by_validate(self):
        self.render(VALID_ENV)
        dynamic = self.root / "config" / "dynamic"
        leftover = dynamic / "security-chains.yml"
        leftover.write_text("http:\n  middlewares:\n    sec-2:\n      chain:\n        middlewares:\n          - compress\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("security-chains.yml is from before the middleware model", v.stdout + v.stderr)
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("security-chains.yml (retired by the middleware model — removed)", r.stdout)
        self.assertFalse(leftover.exists())
        # a retired name in a file that stays — a hand edit — is refused by name
        (dynamic / "redirects.yml").write_text("http:\n  middlewares:\n    acc-public:\n      chain:\n        middlewares: []\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("names the middleware model retired: acc-public", v.stdout + v.stderr)

    def test_compress_is_defined_once_with_exact_exclusions(self):
        self.render(VALID_ENV)
        mw = self.dyn("model.yml")["http"]["middlewares"]
        excluded = mw["compress"]["compress"]["excludedContentTypes"]
        for measured in ("application/octet-stream", "image/png"):
            self.assertIn(measured, excluded, measured)
        self.assertNotIn("text/event-stream", excluded, "SSE stays compressible (decided 2026-10-18)")
        self.assertFalse(any("*" in e for e in excluded), "Traefik matches exclusions exactly — no wildcards")
        self.assertNotIn("includedContentTypes", mw["compress"]["compress"])
        defined_in = [f.name for f in (self.root / "config" / "dynamic").glob("*.yml")
                      if "compress" in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("http", {}).get("middlewares", {})]
        self.assertEqual(defined_in, ["model.yml"])


if __name__ == "__main__":
    unittest.main()
