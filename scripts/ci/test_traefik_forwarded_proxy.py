#!/usr/bin/env python3
"""TRAEFIK_FORWARDED_PROXY — who may set the client address.

- none (and absent): the entrypoints trust no sender (empty trustedIPs), the
  CrowdSec middlewares carry no trusted-proxy list, no firewall file is rendered
- cloudflare: the entrypoints trust the ranges of ops/cloudflare-ips.txt, both
  CrowdSec middlewares carry the same list with CF-Connecting-IP as the header,
  and config/host/cloudflare-ranges.nft carries the ranges as nftables defines
- any other value is refused by render.sh and validate.sh
- a rendered configuration that trusts the ranges while .env does not declare
  the switch is refused, both by render.sh and by validate.sh
- closed access policies carry no ipStrategy in either mode

Run:
    python3 scripts/ci/test_traefik_forwarded_proxy.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

REPO = Path(__file__).resolve().parents[2]
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com",
                 CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k")

spec = importlib.util.spec_from_file_location("cf", REPO / "scripts" / "ci" / "check-cloudflare-ips.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)
RANGES, _ = cf.read_ranges(TRAEFIK / "ops" / "cloudflare-ips.txt")


class ForwardedProxySwitch(unittest.TestCase):
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

    def static(self):
        return yaml.safe_load((self.root / "config" / "traefik.yml").read_text(encoding="utf-8"))

    def crowdsec(self):
        return yaml.safe_load((self.root / "config" / "dynamic" / "crowdsec.yml").read_text(encoding="utf-8"))["http"]["middlewares"]

    def nft(self):
        return self.root / "config" / "host" / "cloudflare-ranges.nft"

    def test_absent_means_none_trusts_nobody(self):
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for ep in ("web", "websecure"):
            self.assertEqual(self.static()["entryPoints"][ep]["forwardedHeaders"]["trustedIPs"], [], ep)
        for mw in ("crowdsec-basic", "crowdsec-appsec"):
            self.assertNotIn("forwardedHeadersTrustedIPs", self.crowdsec()[mw]["plugin"]["bouncer"], mw)
        self.assertFalse(self.nft().exists())
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_cloudflare_trusts_the_file_everywhere(self):
        r = self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for ep in ("web", "websecure"):
            self.assertEqual(self.static()["entryPoints"][ep]["forwardedHeaders"]["trustedIPs"], RANGES, ep)
        for mw in ("crowdsec-basic", "crowdsec-appsec"):
            b = self.crowdsec()[mw]["plugin"]["bouncer"]
            self.assertEqual(b["forwardedHeadersTrustedIPs"], RANGES, mw)
            self.assertEqual(b["forwardedHeadersCustomName"], "CF-Connecting-IP", mw)
        text = self.nft().read_text(encoding="utf-8")
        v4 = [x for x in RANGES if ":" not in x]
        v6 = [x for x in RANGES if ":" in x]
        self.assertIn("define cloudflare_v4 = { " + ", ".join(v4) + " }", text)
        self.assertIn("define cloudflare_v6 = { " + ", ".join(v6) + " }", text)
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_closed_policies_keep_the_connecting_address_in_both_modes(self):
        for mode in ("none", "cloudflare"):
            self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY=mode))
            access = yaml.safe_load((self.root / "config" / "dynamic" / "access.yml").read_text(encoding="utf-8"))
            for name in ("acc-local", "acc-tailscale", "acc-private"):
                self.assertNotIn("ipStrategy", access["http"]["middlewares"][name]["ipAllowList"], f"{mode} {name}")
            blocks = (self.root / "config" / "dynamic" / "security-blocks.yml").read_text(encoding="utf-8")
            self.assertNotIn("sourceCriterion", blocks, mode)

    def test_other_value_is_refused(self):
        r = self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cdn"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TRAEFIK_FORWARDED_PROXY", r.stdout + r.stderr)

    def test_rendered_trust_with_switch_absent_is_refused(self):
        """A host from before the switch trusted the ranges; a render that would
        silently drop that trust is stopped, and so is validation."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)
        self.assertEqual(self.static()["entryPoints"]["web"]["forwardedHeaders"]["trustedIPs"], RANGES, "nothing was changed")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)

    def test_explicit_none_over_a_trusting_config_renders(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        r = self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.static()["entryPoints"]["web"]["forwardedHeaders"]["trustedIPs"], [])
        self.assertFalse(self.nft().exists())

    def test_validate_catches_a_stale_render_in_both_directions(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none"))
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare").items()), encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("run render.sh", v.stdout + v.stderr)
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none").items()), encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("run render.sh", v.stdout + v.stderr)

    def test_switch_off_crowdsec_keeps_the_mode_consistent(self):
        env = dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare", CROWDSEC_BOUNCER_ENABLED="false")
        env.pop("CROWDSEC_BOUNCER_KEY")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.root / "config" / "dynamic" / "crowdsec.yml").exists())
        self.assertEqual(self.validate().returncode, 0)


if __name__ == "__main__":
    unittest.main()
