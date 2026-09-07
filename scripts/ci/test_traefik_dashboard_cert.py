#!/usr/bin/env python3
"""Rendered dashboard certificate configuration, per certificate strategy.

The dashboard follows the strategy chosen in `core/traefik/.env`, the same way
application routers do. These tests read the rendered YAML rather than the
renderer's internals, so the templating mechanism stays free to change.

Run:
    python3 scripts/ci/test_traefik_dashboard_cert.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRAEFIK = REPO / "core" / "traefik"

BASE_ENV = {
    "TZ": "UTC",
    "TRAEFIK_IMAGE": "traefik:v3.6",
    "SOCKET_PROXY_IMAGE": "tecnativa/docker-socket-proxy:0.3.0",
    "PUBLIC_NETWORK": "proxy-public",
    "SOCKET_PROXY_NETWORK": "socket-proxy",
    "TRAEFIK_HTTP_PORT": "80",
    "TRAEFIK_HTTPS_PORT": "443",
    "DOCKER_SOCKET_PROXY_ENDPOINT": "tcp://socket-proxy:2375",
    "TAILSCALE_CIDR_V4": "100.64.0.0/10",
    "TAILSCALE_CIDR_V6": "fd7a:115c:a1e0::/48",
    "ACME_EMAIL": "letsencrypt@example.com",
    "ACME_STORAGE": "/etc/traefik/acme/acme.json",
    "ACME_RESOLVER_DNS": "cloudflare-dns",
    "ACME_RESOLVER_HTTP": "httpResolver",
    "ACME_DNS_RESOLVER_1": "1.1.1.1:53",
    "ACME_DNS_RESOLVER_2": "1.0.0.1:53",
    "CF_DNS_API_TOKEN": "token",
    "TRAEFIK_DASHBOARD_HOST": "traefik.example.com",
    "TLS_DEFAULT_OPTION": "tls-basic",
    "TRAEFIK_DASHBOARD_TLS_OPTION": "tls-modern",
    "TRAEFIK_LOG_LEVEL": "INFO",
    "TRAEFIK_LOG_FORMAT": "json",
    "TRAEFIK_LOG_FILE": "/var/log/traefik/traefik.log",
    "TRAEFIK_ACCESSLOG_FORMAT": "json",
    "TRAEFIK_ACCESSLOG_FILE": "/var/log/traefik/access.log",
    "TRAEFIK_ACCESSLOG_BUFFER": "100",
    "DSP_LOG_LEVEL": "info",
    "DSP_SOCKET_PATH": "/var/run/docker.sock",
    "DSP_BIND_CONFIG": "0.0.0.0:2375",
    "DSP_POST": "0",
    "TRAEFIK_NETWORK": "proxy-public",
}


class DashboardCertificateStrategy(unittest.TestCase):
    """Each case renders into an isolated copy — the live deployment is never touched."""

    def _run(self, overrides):
        env = dict(BASE_ENV)
        env.update(overrides)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(TRAEFIK / "ops", tmp / "ops")
        (tmp / ".env").write_text(
            "".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8"
        )
        render = subprocess.run(
            ["bash", str(tmp / "ops" / "scripts" / "render.sh")],
            capture_output=True, text=True,
        )
        validate = subprocess.run(
            ["bash", str(tmp / "ops" / "scripts" / "validate.sh")],
            capture_output=True, text=True,
        )
        dashboard = tmp / "config" / "dynamic" / "routers-system.yml"
        return {
            "render_rc": render.returncode,
            "validate_rc": validate.returncode,
            "validate_out": validate.stdout + validate.stderr,
            "dashboard": dashboard.read_text(encoding="utf-8") if dashboard.exists() else "",
            "wildcard_rendered": (tmp / "config" / "dynamic" / "acme-wildcard.yml").exists(),
        }

    def test_a_wildcard_covers_dashboard(self):
        """Covering wildcard, no dashboard resolver: TLS block, no certResolver."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "example.com",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "",
        })
        self.assertEqual(r["render_rc"], 0)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self.assertIn("tls:", r["dashboard"])
        self.assertIn("options: tls-modern", r["dashboard"])
        self.assertNotIn("certResolver", r["dashboard"])
        self.assertTrue(r["wildcard_rendered"])

    def test_b_per_domain_keeps_resolver(self):
        """No wildcard: the dashboard carries its own resolver."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "httpResolver",
        })
        self.assertEqual(r["render_rc"], 0)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self.assertIn("certResolver: httpResolver", r["dashboard"])
        self.assertFalse(r["wildcard_rendered"])

    def test_c_no_wildcard_and_no_resolver_fails(self):
        """The combination that would serve TRAEFIK DEFAULT CERT is rejected."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "",
        })
        self.assertNotEqual(r["validate_rc"], 0)
        self.assertIn("TRAEFIK_DASHBOARD_CERT_RESOLVER", r["validate_out"])

    def test_d_wildcard_that_does_not_cover_the_dashboard_fails(self):
        """*.example.com does not match a dashboard two labels deep."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "example.com",
            "TRAEFIK_DASHBOARD_HOST": "traefik.admin.example.com",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "",
        })
        self.assertNotEqual(r["validate_rc"], 0, r["validate_out"])

    def test_d2_wildcard_on_a_different_domain_fails(self):
        """A wildcard for another zone does not cover the dashboard host."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "apps.example.com",
            "TRAEFIK_DASHBOARD_HOST": "traefik.example.com",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "",
        })
        self.assertNotEqual(r["validate_rc"], 0, r["validate_out"])

    def test_e_explicit_resolver_under_a_covering_wildcard_warns(self):
        """Supported, but it publishes the hostname separately — validation says so."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "example.com",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "cloudflare-dns",
        })
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self.assertIn("WARNING", r["validate_out"])
        self.assertIn("Certificate Transparency", r["validate_out"])
        self.assertIn("certResolver: cloudflare-dns", r["dashboard"])

    def test_f_apex_dashboard_is_covered(self):
        """The wildcard certificate's main domain carries the apex itself."""
        r = self._run({
            "ACME_WILDCARD_DOMAIN": "example.com",
            "TRAEFIK_DASHBOARD_HOST": "example.com",
            "TRAEFIK_DASHBOARD_CERT_RESOLVER": "",
        })
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self.assertNotIn("certResolver", r["dashboard"])


class ShippedExampleRequiresAChoice(unittest.TestCase):
    """The shipped .env.example preselects no certificate strategy, on purpose.

    Three strategies are supported and the Blueprint prescribes none, so the
    example cannot demonstrate one without privileging it. Validation stops until
    the operator chooses; this test keeps that a deliberate gate rather than
    something a later change quietly papers over with a default.
    """

    def test_example_stops_with_a_strategy_prompt(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(TRAEFIK / "ops", tmp / "ops")
        shutil.copy(TRAEFIK / ".env.example", tmp / ".env")
        r = subprocess.run(
            ["bash", str(tmp / "ops" / "scripts" / "validate.sh")],
            capture_output=True, text=True,
        )
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, "the example must not validate unchanged")
        self.assertIn("SELECT A CERTIFICATE STRATEGY", out)
        self.assertIn("Wildcard", out)
        self.assertIn("Per-domain", out)


if __name__ == "__main__":
    unittest.main()
