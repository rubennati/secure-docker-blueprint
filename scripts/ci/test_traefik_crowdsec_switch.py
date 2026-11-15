#!/usr/bin/env python3
"""The CrowdSec reverse-proxy remediation switch in core/traefik.

One variable in .env, CROWDSEC_BOUNCER_ENABLED, decides whether render.sh emits
the bouncer plugin block into config/traefik.yml and the middleware file
config/dynamic/crowdsec.yml. The templates are never edited to enable anything.

Each case renders into an isolated copy of core/traefik/ops — the live
deployment is never touched. The cases pin down the contract:

- default (switch absent) renders neither half and validates;
- true renders both halves, the plugin at the version .env names, the
  middlewares keyed by the file crowdsec-bouncer.yml mounts and holding no
  key, threat-crowdsec@file first on the websecure entrypoint, and validates;
  CROWDSEC_APPSEC_ENABLED=true puts the AppSec variant there instead, and is
  refused without the bouncer switch;
- false and absent leave compress@file alone on the entrypoint;
- true without a key file, with an empty one or with one that root without
  capabilities cannot read is refused by render.sh before it writes, and by
  validate.sh; a key file every account can read is named;
- true with a COMPOSE_FILE that does not apply crowdsec-bouncer.yml is refused,
  and so is the overlay without its key file;
- a value other than true/false is refused by render.sh;
- a rendered configuration that carries the integration while .env does not
  declare the switch is refused by render.sh — the state a host is in after
  enabling by hand and pulling the version with the switch;
- an explicit false over that state removes both halves.

Run:
    python3 -m unittest scripts/ci/test_traefik_crowdsec_switch.py
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK
import bouncer_key
import no_daemon

# BASE_ENV picks no certificate strategy on purpose (that is its own test); the
# switch cases want validate.sh to reach the CrowdSec checks, so they cover the
# dashboard with a wildcard.
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")


def yaml_static(text: str) -> dict:
    import yaml
    return yaml.safe_load(text)


def write_env(root: Path, env: dict) -> None:
    (root / ".env").write_text(
        "".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8"
    )


def run(root: Path, script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(root / "ops" / "scripts" / script)],
        capture_output=True, text=True, env=no_daemon.env(),
    )


class CrowdSecSwitch(unittest.TestCase):
    def setUp(self):
        # Real layout: <tmp>/core/traefik/ops next to <tmp>/scripts/ci, because
        # validate.sh reaches the key checker through ../../scripts/ci/.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        self.key = bouncer_key.write(self.root)
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

    def entrypoint_middlewares(self) -> list:
        import yaml
        static = yaml.safe_load(self.static())
        return static["entryPoints"]["websecure"].get("http", {}).get("middlewares", [])

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
        self.assertNotRegex(self.integrations(), r"(?m)^\s*threat-crowdsec:")
        self.assertEqual(self.entrypoint_middlewares(), ["compress@file"], "compression alone at the entrypoint")
        self.assertNotIn("options", yaml_static(self.static())["entryPoints"]["websecure"].get("http", {}).get("tls", {}),
                         "no entrypoint TLS option — the routers take the file provider's default")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_true_renders_plugin_and_keyed_middlewares(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_PLUGIN_VERSION="v1.7.1")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        static = self.static()
        self.assertRegex(static, r"(?m)^experimental:\n  plugins:\n    bouncer:", "plugin block rendered")
        self.assertIn('version: "v1.7.1"', static)
        self.assertTrue(self.crowdsec_file().exists())
        mw = self.crowdsec_file().read_text(encoding="utf-8")
        self.assertRegex(mw, r"(?m)^    threat-crowdsec:", "threat-crowdsec defined")
        self.assertRegex(mw, r"(?m)^    threat-crowdsec-appsec:", "threat-crowdsec-appsec defined")
        self.assertEqual(mw.count("crowdsecLapiKeyFile: /run/secrets/crowdsec_bouncer_key"), 2)
        self.assertNotIn("crowdsecLapiKey:", mw, "the rendered file carries no key")
        self.assertNotIn(bouncer_key.PLACEHOLDER, mw)
        self.assertNotRegex(self.integrations(), r"(?m)^\s*threat-crowdsec:", "the middlewares live in crowdsec.yml only")
        self.assertEqual(self.entrypoint_middlewares(), ["threat-crowdsec@file", "compress@file"],
                         "the threat position in front of every router, then compression")
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        self.assertIn("keyed by a file", v.stdout)

    def test_appsec_switch_selects_the_inspecting_variant_at_the_entrypoint(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_APPSEC_ENABLED="true")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.entrypoint_middlewares(), ["threat-crowdsec-appsec@file", "compress@file"])
        v = self.validate()
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_appsec_without_the_bouncer_is_refused(self):
        r = self.render(dict(VALID_ENV, CROWDSEC_APPSEC_ENABLED="true"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("needs CROWDSEC_BOUNCER_ENABLED=true", r.stdout + r.stderr)
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_APPSEC_ENABLED="maybe"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CROWDSEC_APPSEC_ENABLED must be true or false", r.stdout + r.stderr)

    def test_validate_refuses_an_entrypoint_list_that_disagrees_with_the_switches(self):
        """The static half rendered under one switch state, .env now says another —
        the state between an edit of .env and the next render."""
        self.assertEqual(self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true")).returncode, 0)
        write_env(self.root, dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_APPSEC_ENABLED="true"))
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("entrypoint middlewares", v.stdout + v.stderr)
        self.assertIn("threat-crowdsec-appsec@file", v.stdout + v.stderr)

    def test_validate_refuses_a_static_configuration_without_the_list(self):
        """A traefik.yml rendered before the middleware model — the state of a
        host after the update and before its render."""
        self.assertEqual(self.render(VALID_ENV).returncode, 0)
        static_path = self.root / "config" / "traefik.yml"
        text = static_path.read_text(encoding="utf-8")
        text = text.replace("      middlewares:\n        - compress@file\n", "      tls:\n        options: tls-basic\n")
        static_path.write_text(text, encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("(none)", v.stdout + v.stderr)
        self.assertIn("run render.sh", (v.stdout + v.stderr).lower().replace("run render.sh,", "run render.sh"))

    def test_validate_refuses_a_name_defined_in_two_dynamic_files(self):
        self.assertEqual(self.render(VALID_ENV).returncode, 0)
        (self.root / "config" / "dynamic" / "leftover.yml").write_text(
            "http:\n  middlewares:\n    compress:\n      compress: {}\n", encoding="utf-8")
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("more than one file", v.stdout + v.stderr)
        self.assertIn("compress", v.stdout + v.stderr)

    def test_plugin_version_defaults_when_unset(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true")
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(self.static(), r'version: "v\d+\.\d+\.\d+"')

    def test_true_without_key_file_is_refused_before_anything_is_written(self):
        self.key.unlink()
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(".secrets/crowdsec_bouncer_key.txt does not exist", r.stdout)
        self.assertIn("cscli bouncers add traefik-bouncer -o raw > .secrets/crowdsec_bouncer_key.txt", r.stdout)
        self.assertNotIn("no longer read", r.stdout)
        self.assertFalse((self.root / "config" / "traefik.yml").exists(), "refused before writing")

    def test_a_key_left_in_env_is_named_as_no_longer_read(self):
        self.key.unlink()
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="old-key-in-env"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CROWDSEC_BOUNCER_KEY in .env is no longer read", r.stdout)
        self.assertNotIn("old-key-in-env", r.stdout + r.stderr)

    def test_an_empty_key_file_is_refused(self):
        self.key.write_text("", encoding="utf-8")
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is empty", r.stdout)

    def test_validate_refuses_a_key_file_removed_after_the_render(self):
        self.assertEqual(self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true")).returncode, 0)
        self.key.unlink()
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn(".secrets/crowdsec_bouncer_key.txt does not exist", v.stdout)

    @unittest.skipIf(os.geteuid() == 0, "root owns the file it writes; the case needs another owner")
    def test_a_key_file_root_cannot_read_is_refused(self):
        """Mode 600 or 640 on a file of the operator's: Traefik, root without
        CAP_DAC_OVERRIDE and outside the file's group, cannot read it."""
        for mode in (0o600, 0o640):
            with self.subTest(mode=oct(mode)):
                if os.getegid() == 0 and mode == 0o640:
                    continue  # group 0 reads it: the case needs another group
                self.key.chmod(mode)
                r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true"))
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("Traefik cannot read .secrets/crowdsec_bouncer_key.txt", r.stdout)
                self.assertIn('sudo chown "$USER":0 .secrets/crowdsec_bouncer_key.txt && chmod 640', r.stdout)
                self.assertFalse(self.crowdsec_file().exists(), "refused before writing")

    def test_a_key_file_every_account_reads_is_named(self):
        self.key.chmod(0o644)
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARNING: .secrets/crowdsec_bouncer_key.txt is readable by every account on this host (mode 644)", r.stdout)

    def test_the_switch_needs_the_overlay_in_compose_file(self):
        v4 = "docker-compose.yml:config/published-ports.yml:config/edge-networks.yml"
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", COMPOSE_FILE=v4))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not apply crowdsec-bouncer.yml", r.stdout)
        self.assertIn(f"COMPOSE_FILE={v4}:crowdsec-bouncer.yml", r.stdout)
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", COMPOSE_FILE=f"{v4}:crowdsec-bouncer.yml"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_overlay_without_its_key_file_is_refused(self):
        """Compose refuses a service whose secret has no file: with the bouncer
        off, the overlay has to leave COMPOSE_FILE."""
        self.key.unlink()
        v4 = "docker-compose.yml:config/published-ports.yml:config/edge-networks.yml"
        r = self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="false", COMPOSE_FILE=f"{v4}:crowdsec-bouncer.yml"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("remove crowdsec-bouncer.yml from COMPOSE_FILE", r.stdout)

    def test_value_other_than_true_false_is_refused(self):
        env = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="yes")
        r = self.render(env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("must be true or false", r.stdout + r.stderr)
        self.assertFalse((self.root / "config" / "traefik.yml").exists(), "refused before writing")

    def test_rendered_integration_with_switch_absent_is_refused(self):
        """The drift case: config/ enabled, .env silent. render.sh must not overwrite."""
        env_on = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true")
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
        env_on = dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true")
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
        write_env(self.root, dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true"))
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("run render.sh", v.stdout + v.stderr)


if __name__ == "__main__":
    unittest.main()
