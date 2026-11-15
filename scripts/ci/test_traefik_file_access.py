#!/usr/bin/env python3
"""validate.sh judges config/ and volumes/ as Traefik — root without capabilities — uses them.

Without CAP_DAC_OVERRIDE the kernel gives Traefik the owner bits of a file that
belongs to uid 0, the group bits of one whose group is gid 0, the bits for
everyone else otherwise (ops/scripts/file-access.sh). A test runs as another
user, so TRAEFIK_RUN_AS names that user where a case needs Traefik to own a file;
left out, it is 0:0 as in the deployment, and the test user's files are judged
through "other".

- an unreadable file in config/dynamic, or the directory itself, is refused: the
  file provider then loads nothing and the routers answer 404
- volumes/letsencrypt and volumes/logs have to be writable, acme.json readable
  and writable with mode 600, the log files writable; plugins-storage with the
  CrowdSec switch on
- .env, .secrets/ and the files in it readable by every account are warnings

Run:
    python3 scripts/ci/test_traefik_file_access.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
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

VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")
ME = f"{os.getuid()}:{os.getgid()}"
NOBODY = "65000:65000"   # neither the test user nor its group


@unittest.skipIf(os.geteuid() == 0, "root ignores file modes")
class Deployment(unittest.TestCase):

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parent.parent / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")
        self.render()

    def render(self, **overrides):
        env = self.root / ".env"
        env.write_text("".join(f'{k}="{v}"\n' for k, v in dict(VALID_ENV, **overrides).items()), encoding="utf-8")
        env.chmod(0o600)
        r = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")],
                           capture_output=True, text=True, env=no_daemon.env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def validate(self, run_as=None):
        env = no_daemon.env()
        if run_as:
            env["TRAEFIK_RUN_AS"] = run_as
        r = subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr

    def path(self, rel, mode, directory=False, text="{}"):
        p = self.root / rel
        if directory:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        p.chmod(mode)
        self.addCleanup(lambda: p.exists() and p.chmod(0o700 if directory else 0o600))
        return p

    def assertRefused(self, run_as, says):
        rc, out = self.validate(run_as)
        self.assertNotEqual(rc, 0, out)
        self.assertIn(says, out)
        self.assertIn("Refusing to continue: Traefik cannot use", out)

    def assertAccepted(self, run_as=None):
        rc, out = self.validate(run_as)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Traefik cannot", out)
        return out


class RenderedConfiguration(Deployment):

    def test_a_fresh_render_passes(self):
        out = self.assertAccepted()
        self.assertNotIn("WARNING: .env", out)

    def test_a_dynamic_file_of_mode_600_is_refused_unless_traefik_owns_it(self):
        (self.root / "config/dynamic/model.yml").chmod(0o600)
        self.addCleanup((self.root / "config/dynamic/model.yml").chmod, 0o644)
        self.assertRefused(None, "Traefik cannot read config/dynamic/model.yml (owner")
        self.assertRefused(None, "load none of config/dynamic, and every router naming an @file middleware")
        self.assertAccepted(ME)

    def test_group_zero_reads_through_the_group_bits(self):
        (self.root / "config/dynamic/model.yml").chmod(0o640)
        self.addCleanup((self.root / "config/dynamic/model.yml").chmod, 0o644)
        self.assertAccepted(f"65000:{os.getgid()}")
        self.assertRefused(NOBODY, "Traefik cannot read config/dynamic/model.yml")

    def test_a_closed_dynamic_directory_is_refused(self):
        (self.root / "config/dynamic").chmod(0o700)
        self.addCleanup((self.root / "config/dynamic").chmod, 0o755)
        self.assertRefused(NOBODY, "Traefik cannot list config/dynamic")

    def test_an_unreadable_static_file_is_refused(self):
        (self.root / "config/traefik.yml").chmod(0o600)
        self.addCleanup((self.root / "config/traefik.yml").chmod, 0o644)
        self.assertRefused(NOBODY, "Traefik cannot read config/traefik.yml")


class Volumes(Deployment):

    def test_a_log_directory_made_by_a_normal_user_is_refused(self):
        self.path("volumes/logs", 0o755, directory=True)
        self.assertRefused(NOBODY, "Traefik cannot write volumes/logs")
        self.assertAccepted(ME)

    def test_a_log_file_traefik_cannot_write_is_refused(self):
        self.path("volumes/logs", 0o755, directory=True)
        self.path("volumes/logs/access.log", 0o644, text="")
        self.assertAccepted(ME)
        self.path("volumes/logs/access.log", 0o444, text="")
        self.assertRefused(ME, "Traefik cannot write volumes/logs/access.log")

    def test_the_certificate_store_directory_has_to_be_writable(self):
        self.path("volumes/letsencrypt", 0o755, directory=True)
        self.assertRefused(NOBODY, "Traefik cannot write volumes/letsencrypt")
        self.assertAccepted(ME)

    def test_acme_json_has_to_be_traefiks_with_mode_600(self):
        self.path("volumes/letsencrypt", 0o700, directory=True)
        self.path("volumes/letsencrypt/acme.json", 0o600)
        self.assertAccepted(ME)
        self.assertRefused(f"65000:{os.getgid()}", "Traefik cannot read and write volumes/letsencrypt/acme.json")
        self.path("volumes/letsencrypt/acme.json", 0o644)
        self.assertRefused(ME, "volumes/letsencrypt/acme.json has mode 644: Traefik refuses a certificate store")

    def test_plugin_storage_counts_only_with_the_bouncer(self):
        self.path("volumes/plugins-storage", 0o755, directory=True)
        self.assertAccepted(NOBODY)
        bouncer_key.write(self.root)
        self.render(CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_PLUGIN_VERSION="v1.7.1")
        self.assertRefused(NOBODY, "Traefik cannot write volumes/plugins-storage")


class Secrets(Deployment):

    def test_an_env_every_account_reads_is_a_warning(self):
        (self.root / ".env").chmod(0o644)
        out = self.assertAccepted()
        self.assertIn("WARNING: .env is readable by every account on this host (mode 644) — chmod 600 .env", out)

    def test_an_open_secrets_directory_and_file_are_warnings(self):
        self.path(".secrets", 0o755, directory=True)
        self.path(".secrets/token.txt", 0o644, text="placeholder")
        out = self.assertAccepted()
        self.assertIn("WARNING: .secrets is open to every account on this host (mode 755)", out)
        self.assertIn("WARNING: .secrets/token.txt is readable by every account on this host (mode 644)", out)
        (self.root / ".secrets").chmod(0o700)
        (self.root / ".secrets/token.txt").chmod(0o600)
        out = self.assertAccepted()
        self.assertNotIn("WARNING: .secrets", out)


if __name__ == "__main__":
    unittest.main()
