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
