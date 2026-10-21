#!/usr/bin/env python3
"""The Authentik forward-auth switch in core/traefik/.env.

AUTHENTIK_FORWARD_AUTH_ENABLED decides whether render.sh writes
config/dynamic/authentik.yml, which defines the middleware auth-authentik and
its older name sec-authentik. Same contract as the CrowdSec switch:

- absent or false: no file, no middleware — the blueprint's default
- true: the file, both names, the address from .env or its default
- a value other than true/false, or an address that is not a URL: refused
- a rendered middleware that .env does not declare: refused, both ways

Run:
    python3 scripts/ci/test_traefik_authentik_switch.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")
DEFAULT_ADDRESS = "http://authentik-server:9000/outpost.goauthentik.io/auth/traefik"


class AuthentikSwitch(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parent.parent / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    def render(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        return subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)

    def validate(self):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def authentik_file(self):
        return self.root / "config" / "dynamic" / "authentik.yml"

    def middlewares(self):
        return yaml.safe_load(self.authentik_file().read_text(encoding="utf-8"))["http"]["middlewares"]

    def test_default_renders_no_middleware(self):
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.authentik_file().exists())
        for f in (self.root / "config" / "dynamic").glob("*.yml"):
            self.assertNotIn("auth-authentik:", f.read_text(encoding="utf-8"), f.name)
            self.assertNotIn("sec-authentik:", f.read_text(encoding="utf-8"), f.name)
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_true_renders_both_names_with_the_default_address(self):
        r = self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mw = self.middlewares()
        self.assertEqual(mw["auth-authentik"]["forwardAuth"]["address"], DEFAULT_ADDRESS)
        self.assertIn("X-authentik-username", mw["auth-authentik"]["forwardAuth"]["authResponseHeaders"])
        self.assertNotIn("trustForwardHeader", mw["auth-authentik"]["forwardAuth"])
        self.assertEqual(mw["sec-authentik"]["chain"]["middlewares"], ["auth-authentik"])
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_address_from_env_is_rendered(self):
        env = dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true",
                   AUTHENTIK_FORWARD_AUTH_ADDRESS="https://auth.example.com/outpost.goauthentik.io/auth/traefik")
        self.render(env)
        self.assertEqual(self.middlewares()["auth-authentik"]["forwardAuth"]["address"],
                         "https://auth.example.com/outpost.goauthentik.io/auth/traefik")

    def test_address_that_is_not_a_url_is_refused(self):
        self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true", AUTHENTIK_FORWARD_AUTH_ADDRESS="authentik-server:9000"))
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("AUTHENTIK_FORWARD_AUTH_ADDRESS", v.stdout + v.stderr)

    def test_value_other_than_true_false_is_refused(self):
        r = self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="yes"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("AUTHENTIK_FORWARD_AUTH_ENABLED", r.stdout + r.stderr)

    def test_rendered_middleware_with_switch_absent_is_refused(self):
        """A host that enabled it before the switch existed is stopped, not downgraded."""
        self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true"))
        r = self.render(VALID_ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("AUTHENTIK_FORWARD_AUTH_ENABLED is not set", r.stdout + r.stderr)
        self.assertTrue(self.authentik_file().exists(), "nothing was removed")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)

    def test_explicit_false_removes_the_middleware(self):
        self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true"))
        r = self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="false"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NOTICE", r.stdout)
        self.assertFalse(self.authentik_file().exists())
        self.assertEqual(self.validate().returncode, 0)

    def test_true_then_validate_before_render_is_refused(self):
        self.render(VALID_ENV)
        (self.root / ".env").write_text(
            "".join(f'{k}="{v}"\n' for k, v in dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true").items()),
            encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("run render.sh", v.stdout + v.stderr)

    def test_switches_are_independent(self):
        """Forward-auth on, CrowdSec off, and the other way round — neither needs the other."""
        self.render(dict(VALID_ENV, AUTHENTIK_FORWARD_AUTH_ENABLED="true", CROWDSEC_BOUNCER_ENABLED="false"))
        self.assertTrue(self.authentik_file().exists())
        self.assertFalse((self.root / "config" / "dynamic" / "crowdsec.yml").exists())
        access = (self.root / "config" / "dynamic" / "access.yml").read_text(encoding="utf-8")
        chains = (self.root / "config" / "dynamic" / "security-chains.yml").read_text(encoding="utf-8")
        self.assertNotIn("authentik", access + chains, "no access policy or chain depends on the gate")


if __name__ == "__main__":
    unittest.main()
