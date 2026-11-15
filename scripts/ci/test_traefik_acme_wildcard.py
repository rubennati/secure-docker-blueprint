#!/usr/bin/env python3
"""Several wildcard domains: one ACME router each, checked against what is stored.

ACME_WILDCARD_DOMAIN is a quoted, space-separated list. render.sh writes one
router per domain into config/dynamic/acme-wildcard.yml — the first keeps the
name acme-wildcard, so a single domain renders as before — and refuses an entry
that would request nothing. validate.sh refuses a rendered file that does not
match the list, and compares acme.json with it through check-acme-certs.py: a
wildcard the list no longer names and a single-host certificate under a listed
wildcard are warnings, a listed domain without a certificate a note.

Run:
    python3 scripts/ci/test_traefik_acme_wildcard.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

CHECK = TRAEFIK / "ops" / "scripts" / "check-acme-certs.py"


class Deployment:
    """An isolated copy of core/traefik/ops with its own .env."""

    def __init__(self, case, **overrides):
        self.root = Path(tempfile.mkdtemp())
        case.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        self.write_env(**overrides)

    def write_env(self, **overrides):
        env = dict(BASE_ENV, TRAEFIK_DASHBOARD_CERT_RESOLVER="", TRAEFIK_DASHBOARD_TLS_OPTION="default")
        env.update(overrides)
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")

    def _script(self, name):
        r = subprocess.run(["bash", str(self.root / "ops" / "scripts" / name)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def render(self):
        return self._script("render.sh")

    def validate(self):
        return self._script("validate.sh")

    def wildcard(self):
        path = self.root / "config" / "dynamic" / "acme-wildcard.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None

    def store(self, data):
        path = self.root / "volumes" / "letsencrypt" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path


def acme(*domains):
    """An acme.json with one certificate per (main, sans) pair; keys are placeholders."""
    return {"cloudflare-dns": {"Account": {"Email": "letsencrypt@example.com"}, "Certificates": [
        {"domain": {"main": main, "sans": list(sans)}, "certificate": "placeholder", "key": "placeholder",
         "Store": "default"} for main, sans in domains]}}


class RenderedRouters(unittest.TestCase):

    def test_two_domains_render_two_routers(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com example.net")
        rc, out = d.render()
        self.assertEqual(rc, 0, out)
        self.assertIn("2 wildcard domain(s): example.com example.net", out)
        routers = d.wildcard()["http"]["routers"]
        self.assertEqual(sorted(routers), ["acme-wildcard", "acme-wildcard-2"])
        for name, zone in (("acme-wildcard", "example.com"), ("acme-wildcard-2", "example.net")):
            with self.subTest(router=name):
                r = routers[name]
                self.assertEqual(r["rule"], f"Host(`acme-bootstrap.{zone}`)")
                self.assertEqual(r["tls"]["certResolver"], "cloudflare-dns")
                self.assertEqual(r["tls"]["domains"], [{"main": zone, "sans": [f"*.{zone}"]}])
        rc, out = d.validate()
        self.assertEqual(rc, 0, out)

    def test_one_domain_keeps_the_router_name(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com")
        self.assertEqual(d.render()[0], 0)
        self.assertEqual(list(d.wildcard()["http"]["routers"]), ["acme-wildcard"])

    def test_an_empty_list_renders_no_file(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="", TRAEFIK_DASHBOARD_CERT_RESOLVER="httpResolver")
        rc, out = d.render()
        self.assertEqual(rc, 0, out)
        self.assertIsNone(d.wildcard())
        self.assertIn("skipped", out)

    def test_entries_that_would_request_nothing_are_refused(self):
        for value, says in (("*.example.com", "write the domain without '*.': example.com"),
                            ("Example.com", "is not a domain name"),
                            ("localhost", "is not a domain name"),
                            ("example.com example.com", "is listed twice")):
            with self.subTest(value=value):
                d = Deployment(self, ACME_WILDCARD_DOMAIN=value)
                rc, out = d.render()
                self.assertNotEqual(rc, 0)
                self.assertIn(says, out)


class DashboardUnderTheList(unittest.TestCase):

    def test_a_dashboard_under_the_second_domain_is_covered(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com example.net",
                       TRAEFIK_DASHBOARD_HOST="traefik.example.net")
        self.assertEqual(d.render()[0], 0)
        rc, out = d.validate()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("SELECT A CERTIFICATE STRATEGY", out)

    def test_a_dashboard_under_no_listed_domain_still_needs_a_strategy(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.net example.org",
                       TRAEFIK_DASHBOARD_HOST="traefik.example.com")
        d.render()
        rc, out = d.validate()
        self.assertNotEqual(rc, 0)
        self.assertIn("SELECT A CERTIFICATE STRATEGY", out)

    def test_the_421_warning_names_the_covering_domain(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com example.net",
                       TRAEFIK_DASHBOARD_HOST="traefik.example.net", TRAEFIK_DASHBOARD_TLS_OPTION="tls-strict")
        d.render()
        rc, out = d.validate()
        self.assertEqual(rc, 0, out)
        self.assertIn("TRAEFIK_DASHBOARD_TLS_OPTION=tls-strict under *.example.net", out)


class RenderedFileMatchesTheList(unittest.TestCase):
    """A domain added or dropped after the last render is refused until render.sh runs."""

    def test_a_domain_added_after_the_render_is_refused(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com")
        d.render()
        d.write_env(ACME_WILDCARD_DOMAIN="example.com example.net")
        rc, out = d.validate()
        self.assertNotEqual(rc, 0)
        self.assertIn("names example.net, but config/dynamic/acme-wildcard.yml requests no wildcard for it", out)

    def test_a_domain_dropped_after_the_render_is_refused(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com example.net")
        d.render()
        d.write_env(ACME_WILDCARD_DOMAIN="example.com")
        rc, out = d.validate()
        self.assertNotEqual(rc, 0)
        self.assertIn("requests *.example.net, which ACME_WILDCARD_DOMAIN does not name", out)


class StoredCertificates(unittest.TestCase):

    def _check(self, data, *zones):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "acme.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        r = subprocess.run(["python3", str(CHECK), str(path), *zones], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_the_listed_wildcards_alone_say_nothing(self):
        rc, out = self._check(acme(("example.com", ["*.example.com"]), ("example.net", ["*.example.net"])),
                              "example.com", "example.net")
        self.assertEqual((rc, out), (0, ""))

    def test_a_wildcard_the_list_dropped_is_named(self):
        rc, out = self._check(acme(("example.com", ["*.example.com"]), ("example.net", ["*.example.net"])),
                              "example.com")
        self.assertEqual(rc, 0)
        self.assertIn("wildcard certificate for *.example.net, which ACME_WILDCARD_DOMAIN does not name", out)
        self.assertNotIn("*.example.com,", out)

    def test_a_single_host_under_a_listed_wildcard_is_named(self):
        rc, out = self._check(acme(("example.com", ["*.example.com"]), ("app.example.com", []),
                                   ("deep.app.example.com", []), ("other.org", [])), "example.com")
        self.assertEqual(rc, 0)
        self.assertIn("certificate for app.example.com, which *.example.com covers", out)
        self.assertNotIn("deep.app.example.com", out)   # two labels deep: the wildcard does not cover it
        self.assertNotIn("other.org", out)              # another domain: a per-domain certificate

    def test_a_listed_domain_without_a_certificate_is_a_note(self):
        rc, out = self._check(acme(("example.com", ["*.example.com"])), "example.com", "example.net")
        self.assertEqual(rc, 0)
        self.assertIn("NOTE: acme.json holds no certificate for *.example.net yet", out)

    def test_no_key_material_is_printed(self):
        data = acme(("example.com", ["*.example.com"]), ("app.example.com", []))
        data["cloudflare-dns"]["Certificates"][1]["key"] = "SECRET-KEY-MATERIAL"
        rc, out = self._check(data, "example.com")
        self.assertNotIn("SECRET-KEY-MATERIAL", out)

    def test_an_unreadable_or_broken_file_is_not_verified(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        broken = tmp / "acme.json"
        broken.write_text("{", encoding="utf-8")
        for path in (broken, tmp / "missing.json"):
            with self.subTest(path=path.name):
                r = subprocess.run(["python3", str(CHECK), str(path), "example.com"], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2)
                self.assertIn("NOT VERIFIED", r.stdout)

    def test_validate_reports_the_stored_state(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com")
        d.render()
        d.store(acme(("example.com", ["*.example.com"]), ("example.net", ["*.example.net"])))
        rc, out = d.validate()
        self.assertEqual(rc, 0, out)
        self.assertIn("wildcard certificate for *.example.net", out)

    @unittest.skipIf(os.geteuid() == 0, "root reads a file of mode 000")
    def test_validate_says_when_it_cannot_read_the_store(self):
        d = Deployment(self, ACME_WILDCARD_DOMAIN="example.com")
        d.render()
        path = d.store(acme(("example.com", ["*.example.com"])))
        path.chmod(0)
        self.addCleanup(path.chmod, 0o600)
        rc, out = d.validate()
        self.assertEqual(rc, 0, out)
        self.assertIn("NOT VERIFIED: volumes/letsencrypt/acme.json is not readable for this user", out)


if __name__ == "__main__":
    unittest.main()
