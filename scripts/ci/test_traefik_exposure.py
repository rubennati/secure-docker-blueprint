"""The exposure profile, its layers, the host firewall and the marker (DEC-078, step 6).

validate.sh derives direct, proxied or private from the bindings and the trusted
proxy and prints the layers present and absent; render.sh writes the host
firewall for the profile into config/host/ingress.nft; --strict requires the
marker scripts/exposure-test.sh writes for a public binding. The test script
itself is run against a stub curl.

Run:
    python3 scripts/ci/test_traefik_exposure.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK  # noqa: E402

VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com", TRAEFIK_FORWARDED_PROXY="none")
EXPOSURE_TEST = TRAEFIK.parents[1] / "scripts" / "exposure-test.sh"


class Rendered(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            shutil.copy(TRAEFIK / name, self.root / name)
        # validate.sh reaches for the repository's CrowdSec config check when the bouncer is on
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parents[1] / "scripts" / "ci" / "check-crowdsec-config.py", tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def render(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        r = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def validate(self, *args):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh"), *args], capture_output=True, text=True)

    def nft(self):
        return (self.root / "config" / "host" / "ingress.nft").read_text(encoding="utf-8")

    def nft_check(self):
        text = self.nft().replace('include "/etc/nftables.d/cloudflare-ranges.nft"',
                                  f'include "{self.root / "config" / "host" / "cloudflare-ranges.nft"}"')
        path = self.root / "check.nft"
        path.write_text(text, encoding="utf-8")
        r = subprocess.run(["nft", "-c", "-f", str(path)], capture_output=True, text=True)
        if r.returncode != 0 and "not permitted" in r.stderr:
            # nft opens a netlink socket even to check a file, which needs
            # CAP_NET_ADMIN: as root here, through sudo on a CI runner.
            if subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0:
                return subprocess.run(["sudo", "-n", "nft", "-c", "-f", str(path)], capture_output=True, text=True)
            self.skipTest("nft -c needs CAP_NET_ADMIN, which this environment does not grant")
        return r


class Profile(Rendered):
    def test_the_defaults_derive_direct(self):
        out = self.render(VALID_ENV)
        self.assertIn("exposure profile: direct", out)
        v = self.validate()
        self.assertIn("Exposure profile: direct — derived from TRAEFIK_BIND_V4=0.0.0.0, TRAEFIK_BIND_V6=not published, TRAEFIK_FORWARDED_PROXY=none", v.stdout)
        self.assertIn("not here", v.stdout, "the profile is never presented as reachability")

    def test_cloudflare_derives_proxied(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.assertIn("Exposure profile: proxied", self.validate().stdout)

    def test_private_bindings_derive_private(self):
        for bind in ("100.64.0.5", "192.168.10.2", "127.0.0.1", "10.0.0.1", "172.20.0.1"):
            self.render(dict(VALID_ENV, TRAEFIK_BIND_V4=bind))
            self.assertIn("Exposure profile: private", self.validate().stdout, bind)

    def test_a_public_ipv6_binding_under_dual_stack_makes_it_direct(self):
        env = dict(VALID_ENV, TRAEFIK_BIND_V4="100.64.0.5", TRAEFIK_BIND_V6="[::]",
                   COMPOSE_FILE="docker-compose.yml:network-dual-stack.yml:config/published-ports.yml:config/edge-networks.yml",
                   PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16", PUBLIC_NETWORK_SUBNET_V6="fd3a:91c2:7e04::/64")
        out = self.render(env)
        self.assertIn("exposure profile: direct", out)
        self.render(dict(env, TRAEFIK_BIND_V6="[fd7a:115c:a1e0::5]"))
        self.assertIn("Exposure profile: private", self.validate().stdout)


class HostFirewall(Rendered):
    def test_direct_closes_input_keeps_forward_open_and_protects_the_vpn_range(self):
        self.render(VALID_ENV)
        text = self.nft()
        self.assertIn("type filter hook input priority filter - 10; policy drop;", text)
        self.assertIn("type filter hook forward priority filter - 10; policy accept;", text)
        self.assertIn(f'iifname != "tailscale0" ip6 saddr @vpn_v6 drop', text)
        self.assertIn(f"elements = {{ {BASE_ENV['TAILSCALE_CIDR_V4']} }}", text)
        self.assertIn("ip saddr @vpn_v4 accept", text)
        self.assertNotIn("ct status dnat", text, "a direct profile filters nothing on the published ports")
        self.assertNotIn("include", text)

    def test_proxied_admits_cloudflare_the_vpn_and_the_trusted_ranges_on_the_published_ports(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare", TRUSTED_RANGES="192.168.10.0/24 2001:db8:10::/64"))
        text = self.nft()
        self.assertIn('include "/etc/nftables.d/cloudflare-ranges.nft"', text)
        self.assertIn("set trusted_v4 { type ipv4_addr; flags interval; elements = { 192.168.10.0/24 } }", text)
        self.assertIn("set trusted_v6 { type ipv6_addr; flags interval; elements = { 2001:db8:10::/64 } }", text)
        self.assertIn("ct status dnat ct state new tcp dport { 80, 443 } ip saddr != @cloudflare_v4 ip saddr != @vpn_v4 ip saddr != @trusted_v4 drop", text)
        self.assertIn("ip6 saddr != @cloudflare_v6 ip6 saddr != @vpn_v6 ip6 saddr != @trusted_v6 drop", text)

    def test_the_vpn_interface_comes_from_the_env(self):
        self.render(dict(VALID_ENV, VPN_INTERFACE="wg0"))
        self.assertIn('iifname != "wg0" ip6 saddr @vpn_v6 drop', self.nft())

    @unittest.skipUnless(shutil.which("nft"), "nft is needed to check the ruleset")
    def test_every_profile_renders_a_ruleset_nft_accepts(self):
        for env in (VALID_ENV, dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare", TRUSTED_RANGES="192.168.10.0/24"),
                    dict(VALID_ENV, TRAEFIK_BIND_V4="100.64.0.5"), dict(VALID_ENV, TRUSTED_RANGES="")):
            self.render(env)
            r = self.nft_check()
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_manifest_offers_the_ruleset_as_optional(self):
        manifest = (TRAEFIK / "ops" / "host-files.manifest").read_text(encoding="utf-8")
        self.assertRegex(manifest, r"(?m)^config/host/ingress\.nft\s+/etc/nftables\.d/ingress\.nft\s+0644\s+root:root\s+exact\s+optional$")


class LayersAndMarker(Rendered):
    def test_absent_layers_are_named_with_their_risk_and_never_fail(self):
        self.render(VALID_ENV)
        v = self.validate()
        self.assertIn("host firewall      not installed (recommended)", v.stdout)
        self.assertIn("crowdsec           absent (recommended)", v.stdout)
        self.assertIn("forward-auth       absent (optional)", v.stdout)
        self.assertIn("management", v.stdout)
        self.assertNotIn("ERROR", v.stdout + v.stderr)

    def test_present_layers_are_named_as_present(self):
        self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="test-key-not-a-secret",
                         AUTHENTIK_FORWARD_AUTH_ENABLED="true", AUTHENTIK_FORWARD_AUTH_ADDRESS="http://authentik-server:9000"))
        v = self.validate()
        self.assertIn("crowdsec           present", v.stdout)
        self.assertIn("forward-auth       present", v.stdout)

    def test_a_public_binding_without_the_marker_is_open_and_fails_strict(self):
        self.render(VALID_ENV)
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout)
        self.assertIn("PENDING: exposure test", v.stdout)
        self.assertIn("SECURITY NOT CONFIRMED", v.stdout)
        self.assertNotIn("\nOK.\n", "\n" + v.stdout)
        v = self.validate("--strict")
        self.assertEqual(v.returncode, 1)

    def test_a_marker_for_the_profile_closes_the_item(self):
        self.render(VALID_ENV)
        (self.root / "config" / "exposure-verified").write_text(
            "EXPOSURE_MARKER date=2026-11-01T10:00:00Z target=203.0.113.10 profile=direct result=ok\n", encoding="utf-8")
        v = self.validate()
        self.assertIn("exposure test      recorded 2026-11-01T10:00:00Z against 203.0.113.10 (profile direct)", v.stdout)
        self.assertNotIn("PENDING: exposure test", v.stdout)

    def test_a_marker_for_another_profile_is_refused(self):
        self.render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        (self.root / "config" / "exposure-verified").write_text(
            "EXPOSURE_MARKER date=2026-11-01T10:00:00Z target=203.0.113.10 profile=direct result=ok\n", encoding="utf-8")
        v = self.validate()
        self.assertEqual(v.returncode, 1)
        self.assertIn("records profile 'direct', the configuration derives 'proxied'", v.stdout)

    def test_a_private_profile_needs_no_marker(self):
        self.render(dict(VALID_ENV, TRAEFIK_BIND_V4="100.64.0.5"))
        v = self.validate()
        self.assertIn("exposure test      not required", v.stdout)
        self.assertNotIn("PENDING: exposure test", v.stdout)


class ExposureTestScript(unittest.TestCase):
    """scripts/exposure-test.sh against a stub curl: the port behaviour comes from
    STUB_OPEN, a space-separated list of ports that answer; everything else is
    closed. STUB_NO_V6=1 makes every IPv6 probe report no address.

    The stub behaves as curl does with telnet:// against real servers (measured
    on a host running Traefik, 2026-11-01): an open port whose server waits for
    the client — HTTP, SSH after its banner — is held until --max-time, so curl
    exits 28 after one connect (STUB_OPEN_RC); a refused port exits 7 without a
    connect, a filtered one 28 without a connect (STUB_CLOSED_RC). The
    connection count is what -w '%{num_connects}' prints."""

    def setUp(self):
        self.bin = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.bin, ignore_errors=True)
        stub = self.bin / "curl"
        stub.write_text('''#!/usr/bin/env bash
fam=4; url=""; wout=""; next_w=""
for a in "$@"; do
  if [ -n "$next_w" ]; then wout="$a"; next_w=""; continue; fi
  case "$a" in -6) fam=6 ;; -w) next_w=1 ;; telnet://*) url="$a" ;; esac
done
port="${url##*:}"
[ -n "${STUB_LOG:-}" ] && echo "-$fam $url" >> "$STUB_LOG"
if [ "$fam" = 6 ] && [ -n "${STUB_NO_V6:-}" ]; then exit 6; fi
for p in ${STUB_OPEN:-}; do
  if [ "$p" = "$port" ]; then printf '%s' "${wout//%\\{num_connects\\}/1}"; exit "${STUB_OPEN_RC:-28}"; fi
done
printf '%s' "${wout//%\\{num_connects\\}/0}"
exit "${STUB_CLOSED_RC:-7}"
''', encoding="utf-8")
        stub.chmod(0o755)

    def run_test(self, profile, open_ports, no_v6=False, host="203.0.113.10", **stub_env):
        env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", STUB_OPEN=open_ports, EXPOSURE_TIMEOUT="1", **stub_env)
        if no_v6:
            env["STUB_NO_V6"] = "1"
        return subprocess.run(["bash", str(EXPOSURE_TEST), host, profile], capture_output=True, text=True, env=env)

    def test_a_literal_address_probes_its_own_family_only(self):
        # The plan runs the test once per address; the other family has no address.
        log = self.bin / "probes.log"
        r = self.run_test("direct", "80 443", STUB_LOG=str(log))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("tcp/80                 v6   no address of this family", r.stdout)
        self.assertNotIn("-6 ", log.read_text())
        log.unlink()
        r = self.run_test("direct", "80 443", host="2001:db8::10", STUB_LOG=str(log))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("tcp/80                 v4   no address of this family", r.stdout)
        self.assertIn("-6 telnet://[2001:db8::10]:80", log.read_text())
        self.assertNotIn("-4 ", log.read_text())

    def test_a_name_probes_both_families(self):
        r = self.run_test("direct", "80 443", host="host.example.com")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("no address of this family", r.stdout)

    def test_a_silent_open_port_answers(self):
        # Traefik and sshd wait for the client: curl times out after the connect.
        r = self.run_test("direct", "80 443 22", no_v6=True, STUB_OPEN_RC="28")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("answers (expected: a direct profile is published)", r.stdout)
        self.assertIn("SSH is reachable outside the VPN", r.stdout)

    def test_a_port_the_server_closes_answers(self):
        r = self.run_test("direct", "80 443", no_v6=True, STUB_OPEN_RC="0")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_filtered_port_is_closed(self):
        # A timeout without a connect: the port is filtered, not answering.
        r = self.run_test("direct", "80", no_v6=True, STUB_CLOSED_RC="28")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("tcp/443                v4   does not answer", r.stdout)
        r = self.run_test("proxied", "", no_v6=True, STUB_CLOSED_RC="28")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_direct_with_the_two_ports_answering_prints_the_marker(self):
        r = self.run_test("direct", "80 443", no_v6=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout.strip().splitlines()[-1], r"^EXPOSURE_MARKER date=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ target=203\.0\.113\.10 profile=direct result=ok$")
        self.assertIn("no address of this family", r.stdout)

    def test_direct_with_a_port_not_answering_fails_without_a_marker(self):
        r = self.run_test("direct", "80")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tcp/443", r.stdout)
        self.assertNotIn("EXPOSURE_MARKER", r.stdout)

    def test_proxied_and_private_expect_the_ports_closed(self):
        for profile in ("proxied", "private"):
            r = self.run_test(profile, "")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn(f"profile={profile}", r.stdout)
            r = self.run_test(profile, "443")
            self.assertEqual(r.returncode, 1)
            self.assertIn("answers the internet", r.stdout)

    def test_a_port_that_must_never_answer_fails_every_profile(self):
        for profile, ports in (("direct", "80 443 8080"), ("private", "2375")):
            r = self.run_test(profile, ports)
            self.assertEqual(r.returncode, 1, profile)
            self.assertIn("must never be published", r.stdout)

    def test_ssh_is_reported_not_judged(self):
        r = self.run_test("direct", "80 443 22", no_v6=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("SSH is reachable outside the VPN (reported, not judged)", r.stdout)

    def test_usage_errors_exit_2(self):
        r = subprocess.run(["bash", str(EXPOSURE_TEST), "203.0.113.10", "open"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
