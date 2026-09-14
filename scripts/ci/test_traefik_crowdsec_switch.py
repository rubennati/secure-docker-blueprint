#!/usr/bin/env python3
"""The CrowdSec reverse-proxy remediation switch in core/traefik.

One variable in .env, CROWDSEC_BOUNCER_ENABLED, decides whether render.sh emits
the bouncer plugin block into config/traefik.yml and the middleware file
config/dynamic/crowdsec.yml. The templates are never edited to enable anything.

Each case renders into an isolated copy of core/traefik/ops — the live
deployment is never touched. The cases pin down the contract:

- default (switch absent) renders neither half and validates;
- true renders both halves, the plugin at the version .env names, the
  middlewares keyed, and validates;
- true without a key is refused by validate.sh with the variable named;
- a value other than true/false is refused by render.sh;
- a rendered configuration that carries the integration while .env does not
  declare the switch is refused by render.sh — the state a host is in after
  enabling by hand and pulling the version with the switch;
- an explicit false over that state removes both halves.

Run:
    python3 -m unittest scripts/ci/test_traefik_crowdsec_switch.py
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

# BASE_ENV picks no certificate strategy on purpose (that is its own test); the
# switch cases want validate.sh to reach the CrowdSec checks, so they cover the
# dashboard with a wildcard.
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")


def write_env(root: Path, env: dict) -> None:
    (root / ".env").write_text(
        "".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8"
    )


def run(root: Path, script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(root / "ops" / "scripts" / script)],
        capture_output=True, text=True,
    )


class CrowdSecSwitch(unittest.TestCase):
    def setUp(self):
        # Real layout: <tmp>/core/traefik/ops next to <tmp>/scripts/ci, because
        # validate.sh reaches the key checker through ../../scripts/ci/.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parent.parent / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")

    # -- helpers -------------------------------------------------------------
    def static(self) -> str:
        return (self.root / "config" / "traefik.yml").read_text(encoding="utf-8")

    def crowdsec_file(self) -> Path:
        return self.root / "config" / "dynamic" / "crowdsec.yml"

    def integrations(self) -> str:
        return (self.root / "config" / "dynamic" / "integrations.yml").read_text(encoding="utf-8")

    def render(self, env: dict) -> subprocess.CompletedProcess:
        write_env(self.root, env)
        return run(self.root, "render.sh")

    def validate(self) -> subprocess.CompletedProcess:
        return run(self.root, "validate.sh")

    # -- cases ---------------------------------------------------------------
    def test_default_renders_no_plugin_and_no_middleware(self):
        """Switch absent from .env: the shipped blueprint stays default-off."""
        r = self.render(VALID_ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("experimental:", self.static())
        self.assertNotIn("# >>> crowdsec-bouncer", self.static(), "markers must go with the block")
        self.assertFalse(self.crowdsec_file().exists())
        self.assertNotRegex(self.integrations(), r"(?m)^\s*crowdsec-basic:")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_true_renders_plugin_and_keyed_middlewares(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true",
                   CROWDSEC_BOUNCER_KEY="test-key-not-a-secret",
                   CROWDSEC_BOUNCER_PLUGIN_VERSION="v1.7.1")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        static = self.static()
        self.assertRegex(static, r"(?m)^experimental:\n  plugins:\n    bouncer:", "plugin block rendered")
        self.assertIn('version: "v1.7.1"', static)
        self.assertTrue(self.crowdsec_file().exists())
        mw = self.crowdsec_file().read_text(encoding="utf-8")
        self.assertRegex(mw, r"(?m)^    crowdsec-basic:", "crowdsec-basic defined")
        self.assertRegex(mw, r"(?m)^    crowdsec-appsec:", "crowdsec-appsec defined")
        self.assertEqual(mw.count('crowdsecLapiKey: "test-key-not-a-secret"'), 2)
        self.assertNotRegex(self.integrations(), r"(?m)^\s*crowdsec-basic:", "the middlewares live in crowdsec.yml only")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        self.assertIn("with a key present", v.stdout)

    def test_plugin_version_defaults_when_unset(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(self.static(), r'version: "v\d+\.\d+\.\d+"')

    def test_true_without_key_is_refused(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="")
        self.render(env)
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("CROWDSEC_BOUNCER_KEY", v.stdout + v.stderr)

    def test_value_other_than_true_false_is_refused(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="yes")
        r = self.render(env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("must be true or false", r.stdout + r.stderr)
        self.assertFalse((self.root / "config" / "traefik.yml").exists(), "refused before writing")

    def test_rendered_integration_with_switch_absent_is_refused(self):
        """The drift case: config/ enabled, .env silent. render.sh must not overwrite."""
        env_on = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k")
        self.assertEqual(self.render(env_on).returncode, 0)
        before = self.static()
        r = self.render(VALID_ENV)          # switch absent again
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CROWDSEC_BOUNCER_ENABLED is not set", r.stdout + r.stderr)
        self.assertEqual(self.static(), before, "nothing written")
        self.assertTrue(self.crowdsec_file().exists(), "nothing removed")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("not set in .env", v.stdout + v.stderr)

    def test_explicit_false_removes_the_integration(self):
        env_on = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k")
        self.assertEqual(self.render(env_on).returncode, 0)
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="false"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NOTICE", r.stdout, "the removal is announced, with the router consequence")
        self.assertNotIn("experimental:", self.static())
        self.assertFalse(self.crowdsec_file().exists())
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_true_then_validate_before_render_is_refused(self):
        """Switch flipped on in .env, render.sh not run yet: validate says so."""
        self.assertEqual(self.render(VALID_ENV).returncode, 0)
        write_env(self.root, dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k"))
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("run render.sh", v.stdout + v.stderr)


if __name__ == "__main__":
    unittest.main()
