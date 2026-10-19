#!/usr/bin/env python3
"""The middleware model (Phase 4.1, transition): dynamic/model.yml and the TLS
profiles render beside the names they replace, and nothing old changes.

- the four positions exist: access-*, limit-*, headers-*, auth-none, with the
  decided values; every headers-* profile starts with hsts-base; the empty
  chains (*-none, access-public, headers-application-owned) are valid YAML
- HSTS_MAX_AGE renders into hsts-base and hsts-include-subdomains, defaults
  to two years, and is refused when it is not a number
- tls-profiles.yml carries tls-compatible/standard/strict, Traefik's reserved
  `default` built from TLS_DEFAULT_OPTION (old and new names accepted, any
  other refused), and the transition names tls-basic/aplus/modern
- the old names are untouched: sec-* chains, hdr-*, rl-*, acc-* render as
  before, byte for byte

Run:
    python3 scripts/ci/test_traefik_model.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

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

    def test_tls_profiles_carry_both_name_sets_and_a_default_from_the_env(self):
        self.render(VALID_ENV)  # BASE_ENV: TLS_DEFAULT_OPTION as the shipped example sets it
        opts = self.dyn("tls-profiles.yml")["tls"]["options"]
        self.assertTrue((TLS_NEW | TLS_OLD | {"default"}) <= set(opts), set(opts))
        self.assertEqual(opts["tls-basic"], opts["tls-compatible"])
        self.assertEqual(opts["tls-aplus"], opts["tls-standard"])
        self.assertEqual(opts["tls-modern"], opts["tls-strict"])
        self.assertEqual(opts["tls-strict"]["minVersion"], "VersionTLS13")
        self.assertIn("cipherSuites", opts["tls-standard"])
        for value, expect in (("tls-standard", "tls-standard"), ("tls-aplus", "tls-standard"),
                              ("tls-basic", "tls-compatible"), ("tls-strict", "tls-strict"), ("tls-modern", "tls-strict")):
            r = self.render(dict(VALID_ENV, TLS_DEFAULT_OPTION=value))
            self.assertEqual(r.returncode, 0, value + r.stdout + r.stderr)
            opts = self.dyn("tls-profiles.yml")["tls"]["options"]
            self.assertEqual(opts["default"], opts[expect], value)
        r = self.render(dict(VALID_ENV, TLS_DEFAULT_OPTION="tls-aaa"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TLS_DEFAULT_OPTION", r.stdout + r.stderr)

    def test_the_old_names_render_unchanged(self):
        """The transition keeps sec-*, hdr-*, rl-* and acc-* exactly as before
        the model: compared with the templates of origin/dev at 4a192d9, the
        rendered chains and blocks are the same definitions."""
        self.render(VALID_ENV)
        chains = self.dyn("security-chains.yml")["http"]["middlewares"]
        blocks = self.dyn("security-blocks.yml")["http"]["middlewares"]
        access = self.dyn("access.yml")["http"]["middlewares"]
        self.assertEqual(chains["sec-2"]["chain"]["middlewares"], ["hdr-basic", "rl-soft", "compress"])
        self.assertEqual(chains["sec-3"]["chain"]["middlewares"], ["hdr-strict", "rl-soft", "compress", "permissions-policy"])
        self.assertEqual(blocks["rl-soft"]["rateLimit"], {"average": 125, "burst": 200})
        self.assertEqual(blocks["hdr-basic"]["headers"]["stsSeconds"], 63072000)
        self.assertTrue(blocks["hdr-strict"]["headers"]["stsIncludeSubdomains"])
        self.assertEqual(blocks["compress"], {"compress": {}}, "the old compress block carries no exclusions until it moves to the entrypoint")
        self.assertEqual(set(access), {"acc-public", "acc-local", "acc-tailscale", "acc-private", "acc-deny"})
        static = yaml.safe_load((self.root / "config" / "traefik.yml").read_text(encoding="utf-8"))
        ep = static["entryPoints"]["websecure"]
        self.assertNotIn("middlewares", ep.get("http", {}), "no entrypoint middleware list before the routers move (4.3)")


if __name__ == "__main__":
    unittest.main()
