#!/usr/bin/env python3
"""TRAEFIK_FORWARDED_PROXY — who may set the client address.

- none (and absent): the entrypoints trust no sender (empty trustedIPs), the
  CrowdSec middlewares carry no trusted-proxy list, no firewall file is rendered
- cloudflare: the entrypoints trust the ranges of ops/cloudflare-ips.txt, both
  CrowdSec middlewares carry the same list and keep the plugin's default
  header X-Forwarded-For (never a custom one — Traefik deletes only
  X-Forwarded-* from untrusted senders), and config/host/cloudflare-ranges.nft
  carries the ranges as nftables defines
- any other value is refused by render.sh and validate.sh
- a rendered configuration that trusts any list while .env does not declare
  the switch (absent or empty) is refused, both by render.sh and by
  validate.sh — also after the ranges file gained a new first entry, and in
  the shape every release up to v0.9.4 rendered (comment lines in the list)
- validate.sh refuses a rendered list that differs from the ranges file, a
  middleware with forwardedHeadersCustomName, and a firewall file in none mode;
  it names the undeclared switch before any missing file
- only the trustedIPs key under forwardedHeaders counts, a hand-written flow
  list is read like the block list, and entries are compared by value
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

    def write_env(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")

    def render(self, env):
        self.write_env(env)
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
            self.assertNotIn("forwardedHeadersCustomName", b, f"{mw}: the plugin reads a custom header from any sender")
            self.assertNotIn("clientTrustedIPs", b, mw)
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

    def test_no_mode_names_a_custom_header_for_the_bouncer(self):
        for mode in ("none", "cloudflare"):
            self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY=mode))
            text = (self.root / "config" / "dynamic" / "crowdsec.yml").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^\s*forwardedHeadersCustomName:", mode)
        # and validate.sh refuses one that got there by hand
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        cs = self.root / "config" / "dynamic" / "crowdsec.yml"
        cs.write_text(cs.read_text(encoding="utf-8").replace(
            "          forwardedHeadersTrustedIPs:", "          forwardedHeadersCustomName: CF-Connecting-IP\n          forwardedHeadersTrustedIPs:", 1), encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("forwardedHeadersCustomName", v.stdout + v.stderr)

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

    def test_guard_holds_after_the_ranges_file_gained_a_new_first_entry(self):
        """The guard is keyed on the shape of the rendered list, not on a value:
        a range inserted at the top of the file must not make it blind."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        f = self.root / "ops" / "cloudflare-ips.txt"
        f.write_text("192.0.2.0/24\n" + f.read_text(encoding="utf-8"), encoding="utf-8")
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0, "rendered over a trusting config without a declared mode")
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)
        self.assertEqual(self.static()["entryPoints"]["web"]["forwardedHeaders"]["trustedIPs"], RANGES, "nothing was changed")

    # The forwardedHeaders block of core/traefik/ops/templates/traefik.yml.tmpl
    # at tag v0.9.4, verbatim (identical from v0.8.4 to v0.9.4; the list was
    # hard-coded, so a release rendered it exactly like this). This is the
    # shape the migration guard exists for, and the shape its first version
    # read as "trusts nobody" because the line after the key is a comment.
    RELEASED_BLOCK = """    forwardedHeaders:
      trustedIPs: &cloudflareTrustedIPs
        # Cloudflare IPv4
        - "173.245.48.0/20"
        - "103.21.244.0/22"
        - "103.22.200.0/22"
        - "103.31.4.0/22"
        - "141.101.64.0/18"
        - "108.162.192.0/18"
        - "190.93.240.0/20"
        - "188.114.96.0/20"
        - "197.234.240.0/22"
        - "198.41.128.0/17"
        - "162.158.0.0/15"
        - "104.16.0.0/13"
        - "104.24.0.0/14"
        - "172.64.0.0/13"
        - "131.0.72.0/22"
        # Cloudflare IPv6
        - "2400:cb00::/32"
        - "2606:4700::/32"
        - "2803:f800::/32"
        - "2405:b500::/32"
        - "2405:8100::/32"
        - "2a06:98c0::/29"
        - "2c0f:f248::/32"
"""

    def released_shape(self):
        """Replace the rendered web-entrypoint list in config/traefik.yml with
        the block a v0.8.4–v0.9.4 release rendered, verbatim."""
        f = self.root / "config" / "traefik.yml"
        lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
        start = next(i for i, l in enumerate(lines) if l.startswith("    forwardedHeaders:"))
        end = start + 1
        while end < len(lines) and (lines[end].startswith("      trustedIPs:") or lines[end].startswith("        ")):
            end += 1
        text = "".join(lines[:start]) + self.RELEASED_BLOCK + "".join(lines[end:])
        f.write_text(text, encoding="utf-8")
        self.assertIn("        # Cloudflare IPv4\n", text)
        self.assertEqual(self.static()["entryPoints"]["web"]["forwardedHeaders"]["trustedIPs"][0], "173.245.48.0/20", "the released block parses as the list it was")

    def test_released_block_matches_the_tagged_template_when_git_has_the_tag(self):
        """Keeps the fixture honest: when the checkout carries tag v0.9.4, the
        block above must be what that template holds. A shallow CI checkout
        without tags skips this, the fixture tests above still run."""
        r = subprocess.run(["git", "-C", str(REPO), "show", "v0.9.4:core/traefik/ops/templates/traefik.yml.tmpl"], capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("tag v0.9.4 not in this checkout")
        self.assertIn(self.RELEASED_BLOCK, r.stdout)

    def test_guard_holds_against_a_configuration_rendered_by_a_release(self):
        """The second review found the shape guard reading the release's
        comment line as "trusts nobody". A host from v0.9.x must be refused."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.released_shape()
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0, "rendered over a release's trusting config without a declared mode")
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)
        self.assertIn("# Cloudflare IPv4", (self.root / "config" / "traefik.yml").read_text(encoding="utf-8"), "nothing was changed")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("not set in .env", v.stdout + v.stderr)

    def test_validate_reads_the_whole_list_of_a_release_shape(self):
        """A comment between the two families must not end the list early, or
        the comparison with the ranges file would fail on a correct host."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.released_shape()
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_upper_case_value_is_accepted(self):
        r = self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="CLOUDFLARE"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.static()["entryPoints"]["web"]["forwardedHeaders"]["trustedIPs"], RANGES)
        self.assertEqual(self.validate().returncode, 0)

    def web_block(self):
        """(start, end) line indexes of the web entrypoint's forwardedHeaders block."""
        lines = (self.root / "config" / "traefik.yml").read_text(encoding="utf-8").splitlines(keepends=True)
        start = next(i for i, l in enumerate(lines) if l.startswith("    forwardedHeaders:"))
        end = start + 1
        while end < len(lines) and (lines[end].startswith("      trustedIPs:") or lines[end].startswith("        ")):
            end += 1
        return lines, start, end

    def rewrite_web_block(self, block):
        lines, start, end = self.web_block()
        (self.root / "config" / "traefik.yml").write_text("".join(lines[:start]) + block + "".join(lines[end:]), encoding="utf-8")

    def test_a_flow_list_written_by_hand_is_read_like_the_block_list(self):
        """The third review: `trustedIPs: ["…"]` on the key line was read as
        "trusts nobody" and rendered over silently. Trusting flow list: refused
        without the switch, valid with cloudflare. Empty flow list: none."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        flow = ", ".join(f'"{r}"' for r in RANGES)
        self.rewrite_web_block(f"    forwardedHeaders:\n      trustedIPs: &cloudflareTrustedIPs [{flow}]\n")
        self.assertEqual(self.static()["entryPoints"]["websecure"]["forwardedHeaders"]["trustedIPs"], RANGES, "valid YAML, same list")
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0, "rendered over a hand-written flow list without a declared mode")
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("not set in .env", v.stdout + v.stderr)
        self.write_env(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        # the empty flow list is the none shape
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none"))
        self.rewrite_web_block("    forwardedHeaders:\n      trustedIPs: &cloudflareTrustedIPs []\n")
        self.assertEqual(self.validate().returncode, 0)
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_only_the_key_under_forwarded_headers_counts(self):
        """A proxyProtocol.trustedIPs list written above forwardedHeaders must
        not be the list the guard reads — in either direction."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none"))
        lines, start, _ = self.web_block()
        lines.insert(start, '    proxyProtocol:\n      trustedIPs:\n        - "10.0.0.0/8"\n')
        (self.root / "config" / "traefik.yml").write_text("".join(lines), encoding="utf-8")
        self.assertEqual(self.validate().returncode, 0, "a trusting proxyProtocol list is not the forwarded-headers list")
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        lines, start, _ = self.web_block()
        lines.insert(start, "    proxyProtocol:\n      trustedIPs: []\n")
        (self.root / "config" / "traefik.yml").write_text("".join(lines), encoding="utf-8")
        self.assertEqual(self.validate().returncode, 0, "an empty proxyProtocol list does not hide the trusting forwarded-headers list")
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)

    def test_hand_edited_entries_are_compared_by_value(self):
        """A trailing comment, single quotes and CRLF endings on the rendered
        entries are the operator's editor, not a changed ranges file."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        lines, start, end = self.web_block()
        entries = [i for i in range(start, end) if lines[i].lstrip().startswith('- "')]
        lines[entries[0]] = lines[entries[0]].rstrip("\n") + "  # the edge\n"
        lines[entries[1]] = lines[entries[1]].replace('"', "'")
        for i in range(start, end):
            lines[i] = lines[i].rstrip("\n") + "\r\n"
        (self.root / "config" / "traefik.yml").write_text("".join(lines), encoding="utf-8")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        # and a real difference is still named as the list, not the editor
        f = self.root / "ops" / "cloudflare-ips.txt"
        f.write_text(f.read_text(encoding="utf-8") + "198.51.100.0/24\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("differs from ops/cloudflare-ips.txt", v.stdout + v.stderr)

    def test_validate_names_the_switch_before_a_missing_file(self):
        """A config/ from before v0.9.3 lacks servers-transports.yml; the
        operator must read the migration message first, not a missing file."""
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        (self.root / "config" / "dynamic" / "servers-transports.yml").unlink()
        self.write_env(VALID_ENV)
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        out = v.stdout + v.stderr
        self.assertIn("not set in .env", out)
        self.assertNotIn("servers-transports", out)

    def test_empty_value_counts_as_undeclared(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        r = self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY=""))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TRAEFIK_FORWARDED_PROXY is not", r.stdout + r.stderr)
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("not set", v.stdout + v.stderr)

    def test_validate_notices_a_changed_ranges_file_in_cloudflare_mode(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.assertEqual(self.validate().returncode, 0)
        f = self.root / "ops" / "cloudflare-ips.txt"
        f.write_text(f.read_text(encoding="utf-8") + "198.51.100.0/24\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("differs from ops/cloudflare-ips.txt", v.stdout + v.stderr)
        self.assertIn("run render.sh", v.stdout + v.stderr)

    def test_validate_refuses_a_firewall_file_in_none_mode(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="none"))
        self.nft().parent.mkdir(parents=True, exist_ok=True)
        self.nft().write_text("define cloudflare_v4 = { 192.0.2.0/24 }\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("cloudflare-ranges.nft", v.stdout + v.stderr)

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
