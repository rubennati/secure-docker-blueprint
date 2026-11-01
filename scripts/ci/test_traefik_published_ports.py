#!/usr/bin/env python3
"""The published ports of core/traefik — port variables and bind addresses.

- TRAEFIK_HTTP_PORT and TRAEFIK_HTTPS_PORT hold a port number; the default
  .env passes
- address:port from an .env written before the bind variables is refused,
  and the message names the lines that keep the same binding: the IPv4
  address moves to TRAEFIK_BIND_V4, a bracketed IPv6 address to
  TRAEFIK_BIND_V6 with the dual-stack overlay
- two ports naming different IPv4 addresses are pointed out, since one
  TRAEFIK_BIND_V4 holds the address for both
- anything else that is not a port from 1 to 65535 is refused
- TRAEFIK_BIND_V4 accepts an IPv4 address only, TRAEFIK_BIND_V6 a bracketed
  IPv6 address only
- render.sh writes config/published-ports.yml, one block per family; an empty
  variable leaves its family out, TRAEFIK_BIND_V6 has no default, unset
  TRAEFIK_BIND_V4 is 0.0.0.0 (DEC-075.3, step 7)
- render.sh refuses a COMPOSE_FILE without the rendered file, an IPv6 binding
  without network-dual-stack.yml, and the overlay with TRAEFIK_BIND_V6 unset;
  validate.sh refuses the same missing file and a rendered file that names
  other bindings than .env

Run:
    python3 scripts/ci/test_traefik_published_ports.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

REPO = Path(__file__).resolve().parents[2]
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")


class PublishedPorts(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def run_with(self, **overrides):
        env = dict(VALID_ENV, **overrides)
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        render = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def test_port_numbers_pass(self):
        r = self.run_with()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_ipv4_address_in_port_variable_is_refused_with_the_replacement(self):
        r = self.run_with(TRAEFIK_HTTPS_PORT="192.0.2.10:443")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("TRAEFIK_HTTPS_PORT=443", r.stdout)
        self.assertIn("TRAEFIK_BIND_V4=192.0.2.10", r.stdout)

    def test_all_interfaces_form_is_refused_with_the_replacement(self):
        # The form an operator sets to publish IPv4 only on a release that
        # has no bind variable; the replacement keeps that binding.
        r = self.run_with(TRAEFIK_HTTP_PORT="0.0.0.0:80", TRAEFIK_HTTPS_PORT="0.0.0.0:443")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("TRAEFIK_HTTP_PORT=80", r.stdout)
        self.assertIn("TRAEFIK_HTTPS_PORT=443", r.stdout)
        self.assertIn("TRAEFIK_BIND_V4=0.0.0.0", r.stdout)
        self.assertNotIn("different addresses", r.stdout)

    def test_ipv6_address_in_port_variable_points_to_the_overlay(self):
        r = self.run_with(TRAEFIK_HTTPS_PORT="[2001:db8::10]:443")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("TRAEFIK_BIND_V6=[2001:db8::10]", r.stdout)
        self.assertIn("network-dual-stack.yml", r.stdout)

    def test_two_different_ipv4_addresses_are_pointed_out(self):
        r = self.run_with(TRAEFIK_HTTP_PORT="192.0.2.10:80", TRAEFIK_HTTPS_PORT="192.0.2.11:443")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("different addresses", r.stdout)

    def test_values_that_are_no_port_are_refused(self):
        for value in ("443x", "0", "70000", "https"):
            with self.subTest(value=value):
                r = self.run_with(TRAEFIK_HTTPS_PORT=value)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("must be a port number", r.stdout)

    def test_bind_v4_accepts_ipv4_only(self):
        self.assertEqual(self.run_with(TRAEFIK_BIND_V4="192.0.2.10").returncode, 0)
        for value in ("[::]", "::", "localhost"):
            with self.subTest(value=value):
                r = self.run_with(TRAEFIK_BIND_V4=value)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("TRAEFIK_BIND_V4 must be an IPv4 address", r.stdout)

    def test_bind_v6_accepts_a_bracketed_ipv6_address_only(self):
        self.assertEqual(self.run_with(TRAEFIK_BIND_V6="[2001:db8::10]").returncode, 0)
        for value in ("::", "2001:db8::10", "0.0.0.0"):
            with self.subTest(value=value):
                r = self.run_with(TRAEFIK_BIND_V6=value)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("TRAEFIK_BIND_V6 must be a bracketed IPv6 address", r.stdout)


if __name__ == "__main__":
    unittest.main()


class RenderedBindings(unittest.TestCase):
    DUAL = "docker-compose.yml:network-dual-stack.yml:config/published-ports.yml:config/edge-networks.yml"
    V4_ONLY = "docker-compose.yml:config/published-ports.yml:config/edge-networks.yml"
    SUBNETS = dict(PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16", PUBLIC_NETWORK_SUBNET_V6="fd3a:91c2:7e04::/64")

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def write_env(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")

    def render(self, **overrides):
        env = dict(VALID_ENV, **overrides)
        env = {k: v for k, v in env.items() if v is not None}
        self.write_env(env)
        return subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)

    def validate(self):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def ports(self):
        return [l.strip()[3:-1] for l in (self.root / "config" / "published-ports.yml").read_text().splitlines()
                if l.strip().startswith('- "')]

    def test_unset_v4_is_every_ipv4_address_and_ipv6_is_off(self):
        r = self.render()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ports(), ["0.0.0.0:80:80/tcp", "0.0.0.0:443:443/tcp", "0.0.0.0:443:443/udp"])
        self.assertIn("IPv6: not published", r.stdout)

    def test_dual_stack_renders_both_families(self):
        r = self.render(COMPOSE_FILE=self.DUAL, TRAEFIK_BIND_V4="0.0.0.0", TRAEFIK_BIND_V6="[::]", **self.SUBNETS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ports(), ["0.0.0.0:80:80/tcp", "0.0.0.0:443:443/tcp", "0.0.0.0:443:443/udp",
                                        "[::]:80:80/tcp", "[::]:443:443/tcp", "[::]:443:443/udp"])

    def test_ipv6_only_leaves_ipv4_out(self):
        r = self.render(COMPOSE_FILE=self.DUAL, TRAEFIK_BIND_V4="", TRAEFIK_BIND_V6="[2001:db8::10]", **self.SUBNETS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ports(), ["[2001:db8::10]:80:80/tcp", "[2001:db8::10]:443:443/tcp", "[2001:db8::10]:443:443/udp"])
        self.assertIn("IPv4: not published", r.stdout)

    def test_both_empty_publishes_nothing_and_says_so(self):
        r = self.render(TRAEFIK_BIND_V4="", TRAEFIK_BIND_V6="")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ports(), [])
        self.assertIn("nothing is published", (self.root / "config" / "published-ports.yml").read_text())
        self.assertIn("Traefik publishes no port", self.validate().stdout)

    def test_compose_file_without_the_rendered_file_is_refused(self):
        r = self.render(COMPOSE_FILE="docker-compose.yml:config/edge-networks.yml")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not apply config/published-ports.yml", r.stdout)

    def test_ipv6_binding_without_the_overlay_is_refused(self):
        r = self.render(COMPOSE_FILE=self.V4_ONLY, TRAEFIK_BIND_V6="[::]")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not apply\n       network-dual-stack.yml", r.stdout)

    def test_the_overlay_with_bind_v6_unset_is_refused(self):
        r = self.render(COMPOSE_FILE=self.DUAL, **self.SUBNETS)
        self.assertEqual(r.returncode, 1)
        self.assertIn("TRAEFIK_BIND_V6 is not set", r.stdout)

    def test_the_overlay_with_bind_v6_empty_publishes_ipv4_only(self):
        r = self.render(COMPOSE_FILE=self.DUAL, TRAEFIK_BIND_V6="", **self.SUBNETS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(all(p.startswith("0.0.0.0:") for p in self.ports()))

    def test_validate_refuses_a_stale_file_and_a_missing_entry(self):
        self.assertEqual(self.render().returncode, 0)
        self.write_env(dict(VALID_ENV, TRAEFIK_BIND_V4="192.0.2.10"))
        v = self.validate()
        self.assertEqual(v.returncode, 1)
        self.assertIn("config/published-ports.yml binds [0.0.0.0 ] but .env says [192.0.2.10 ]", v.stdout)
        self.write_env(dict(VALID_ENV, COMPOSE_FILE="docker-compose.yml:config/edge-networks.yml"))
        v = self.validate()
        self.assertEqual(v.returncode, 1)
        self.assertIn("do not apply config/published-ports.yml", v.stdout)

    def test_the_example_ships_ipv4_and_no_ipv6_default(self):
        text = (TRAEFIK / ".env.example").read_text(encoding="utf-8")
        self.assertIn("\nTRAEFIK_BIND_V4=0.0.0.0\n", text)
        self.assertIn("\nTRAEFIK_BIND_V6=\n", text)
        self.assertIn("\nCOMPOSE_FILE=docker-compose.yml:config/published-ports.yml:config/edge-networks.yml\n", text)
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            self.assertNotIn("ports:", "\n".join(l for l in (TRAEFIK / name).read_text().splitlines()
                                                 if not l.lstrip().startswith("#")), name)


class SubnetVariables(unittest.TestCase):
    """PUBLIC_NETWORK_SUBNET_V4/_V6, judged only when set: the example IPv6
    prefix is refused with the generating command, a global prefix is refused,
    a generated ULA and a private IPv4 network pass."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def validate_with(self, **overrides):
        env = dict(VALID_ENV, **overrides)
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        render = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def test_the_example_prefix_is_refused_with_the_generating_command(self):
        r = self.validate_with(PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16", PUBLIC_NETWORK_SUBNET_V6="fd00:dead:beef:30::/64")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("example prefix", r.stdout)
        self.assertIn("openssl rand -hex 5", r.stdout)

    def test_a_global_prefix_is_refused(self):
        r = self.validate_with(PUBLIC_NETWORK_SUBNET_V6="2001:db8:1::/64")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unique local IPv6 network", r.stdout)

    def test_a_public_ipv4_network_is_refused(self):
        r = self.validate_with(PUBLIC_NETWORK_SUBNET_V4="203.0.113.0/24")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("private IPv4 network", r.stdout)

    def test_generated_values_pass(self):
        r = self.validate_with(PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16", PUBLIC_NETWORK_SUBNET_V6="fd3a:91c2:7e04::/64")
        self.assertNotIn("PUBLIC_NETWORK_SUBNET", r.stdout + r.stderr)

    def test_unset_variables_are_not_judged(self):
        r = self.validate_with()
        self.assertNotIn("PUBLIC_NETWORK_SUBNET", r.stdout + r.stderr)
