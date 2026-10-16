#!/usr/bin/env python3
"""scripts/host-files.sh — render, check, diff and install-commands against a
scratch stack and a scratch "host" (HOST_FILES_PREFIX), so nothing under /etc
is read or written.

Run:
    python3 scripts/ci/test_host_files.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import grp
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts" / "host-files.sh"
ME = f"{pwd.getpwuid(os.getuid()).pw_name}:{grp.getgrgid(os.getgid()).gr_name}"


class Scratch:
    """A stack with a manifest inside a scratch checkout, and a scratch host."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        self.checkout = self.root / "checkout"
        self.host = self.root / "host"
        (self.checkout / "scripts").mkdir(parents=True)
        shutil.copy(TOOL, self.checkout / "scripts" / "host-files.sh")
        self.stack = self.checkout / "core" / "demo"
        (self.stack / "ops").mkdir(parents=True)
        (self.stack / "config").mkdir()
        (self.stack / "config" / "stanza").write_text(
            "/path/to/secure-docker-blueprint/core/demo/volumes/logs/x.log {\n    daily\n}\n", encoding="utf-8"
        )
        (self.stack / "ops" / "unit.service").write_text("[Service]\nExecStart=/usr/local/bin/x\n", encoding="utf-8")
        (self.stack / "ops" / "demo.env.example").write_text(
            "# demo\nCONTAINER_NAME=\nPING_URL=\nCONFIRM_AFTER=3\n# STATE_FILE=/var/lib/demo/state\n", encoding="utf-8"
        )
        self.host.mkdir()
        for d in ("etc/logrotate.d", "etc/systemd/system", "etc", "root"):
            (self.host / d).mkdir(parents=True, exist_ok=True)

    def manifest(self, text):
        (self.stack / "ops" / "host-files.manifest").write_text(text, encoding="utf-8")

    def run(self, *args):
        env = dict(os.environ, HOST_FILES_PREFIX=str(self.host))
        r = subprocess.run(["bash", str(self.checkout / "scripts" / "host-files.sh"), *args],
                           capture_output=True, text=True, env=env, cwd=str(self.checkout))
        return r.returncode, r.stdout + r.stderr

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


STANDARD = f"""# demo
config/stanza          /etc/logrotate.d/demo                    0644  {ME}  exact     required
ops/unit.service       /etc/systemd/system/demo.service         0644  {ME}  exact     optional
ops/demo.env.example   /etc/demo.env                            0600  {ME}  derived   required
-                      /root/.demo-secret                       0600  {ME}  presence  required
"""


class HostFiles(unittest.TestCase):
    def setUp(self):
        self.s = Scratch()
        self.addCleanup(self.s.cleanup)
        self.s.manifest(STANDARD)

    def install(self, target, content=None, mode=0o644):
        p = self.s.host / target.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            content = (self.s.stack / "config" / "host" / Path(target).name).read_text(encoding="utf-8")
        p.write_text(content, encoding="utf-8")
        p.chmod(mode)
        return p

    # ----- render -------------------------------------------------------
    def test_render_substitutes_the_checkout_path_and_writes_only_config_host(self):
        rc, out = self.s.run("render", "core/demo")
        self.assertEqual(rc, 0, out)
        rendered = (self.s.stack / "config" / "host" / "demo").read_text(encoding="utf-8")
        self.assertIn(f"{self.s.checkout}/core/demo/volumes/logs/x.log", rendered)
        self.assertNotIn("/path/to/secure-docker-blueprint", rendered)
        self.assertFalse(any(p.is_file() for p in self.s.host.rglob("*")), "render wrote nothing on the host")
        self.assertEqual(sorted(p.name for p in (self.s.stack / "config" / "host").iterdir()),
                         ["demo", "demo.env", "demo.service"])

    # ----- check: the states --------------------------------------------
    def test_check_before_render_reports_not_rendered(self):
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 1)
        self.assertIn("not rendered", out)

    def test_missing_required_and_not_installed_optional(self):
        self.s.run("render", "core/demo")
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 1)
        self.assertIn("missing        demo: config/stanza -> /etc/logrotate.d/demo", out)
        self.assertIn("not installed  demo: ops/unit.service -> /etc/systemd/system/demo.service", out)
        self.assertIn("missing        demo: - -> /root/.demo-secret", out)

    def test_everything_in_place_is_identical_adapted_present_and_exit_zero(self):
        self.s.run("render", "core/demo")
        self.install("/etc/logrotate.d/demo")
        self.install("/etc/demo.env", "CONTAINER_NAME=traefik-core\nPING_URL=https://hc.example.com/ping/1\nCONFIRM_AFTER=5\n", 0o600)
        self.install("/root/.demo-secret", "s3cret\n", 0o600)
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 0, out)
        self.assertIn("identical      demo: config/stanza", out)
        self.assertIn("adapted        demo: ops/demo.env.example -> /etc/demo.env  (locally adapted)", out)
        self.assertIn("identical      demo: - -> /root/.demo-secret  (present)", out)
        self.assertIn("not installed  demo: ops/unit.service", out)
        self.assertNotIn("s3cret", out)

    def test_exact_content_difference_is_reported_with_both_paths(self):
        self.s.run("render", "core/demo")
        self.install("/etc/logrotate.d/demo", "/old/path/x.log {\n    daily\n    postrotate\n    docker kill -s USR1 x\n    endscript\n}\n")
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 1)
        self.assertIn("differs        demo: config/stanza -> /etc/logrotate.d/demo  (content differs", out)

    def test_mode_or_owner_difference_is_reported_even_when_content_matches(self):
        self.s.run("render", "core/demo")
        self.install("/etc/logrotate.d/demo", mode=0o600)
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 1)
        self.assertIn("differs        demo: config/stanza -> /etc/logrotate.d/demo  (mode 600, manifest 0644)", out)

    def test_derived_missing_required_setting_differs(self):
        self.s.run("render", "core/demo")
        self.install("/etc/demo.env", "CONTAINER_NAME=x\nCONFIRM_AFTER=3\n", 0o600)
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 1)
        self.assertIn("differs        demo: ops/demo.env.example -> /etc/demo.env  (missing setting(s): PING_URL)", out)

    def test_derived_unknown_setting_is_adapted_not_an_error(self):
        self.s.run("render", "core/demo")
        self.install("/etc/logrotate.d/demo")
        self.install("/root/.demo-secret", "x\n", 0o600)
        self.install("/etc/demo.env", "CONTAINER_NAME=x\nPING_URL=y\nCONFIRM_AFTER=3\nSTATE_FILE=/tmp/s\nEXTRA=1\n", 0o600)
        rc, out = self.s.run("check", "core/demo")
        self.assertEqual(rc, 0, out)
        self.assertIn("adapted        demo: ops/demo.env.example -> /etc/demo.env  (locally adapted; not in the example: EXTRA)", out)

    def test_presence_never_reads_the_secret(self):
        """A secret with no read permission is still 'present' — only stat is used."""
        self.s.run("render", "core/demo")
        p = self.install("/root/.demo-secret", "x\n", 0o000)
        rc, out = self.s.run("check", "core/demo")
        p.chmod(0o600)
        self.assertIn("differs        demo: - -> /root/.demo-secret  (mode 0, manifest 0600)", out)
        self.assertNotIn("unreadable", out.split("/root/.demo-secret")[1].split("\n")[0])

    @unittest.skipIf(os.getuid() == 0, "root can read everything")
    def test_unreadable_installed_file_is_reported(self):
        self.s.run("render", "core/demo")
        p = self.install("/etc/logrotate.d/demo", mode=0o000)
        rc, out = self.s.run("check", "core/demo")
        p.chmod(0o644)
        self.assertEqual(rc, 1)
        self.assertIn("unreadable     demo: config/stanza -> /etc/logrotate.d/demo", out)

    # ----- diff and install-commands ------------------------------------
    def test_diff_shows_exact_and_withholds_secrets(self):
        self.s.run("render", "core/demo")
        self.install("/etc/logrotate.d/demo", "/old {\n}\n")
        rc, out = self.s.run("diff", "core/demo", "/etc/logrotate.d/demo")
        self.assertIn("-/old {", out)
        self.assertIn("+" + str(self.s.checkout), out)
        self.install("/etc/demo.env", "CONTAINER_NAME=x\nPING_URL=https://hc.example.com/ping/s3cret\nCONFIRM_AFTER=3\n", 0o600)
        rc, out = self.s.run("diff", "core/demo", "/etc/demo.env")
        self.assertNotIn("s3cret", out)
        self.assertIn("settings are compared, not shown", out)
        rc, out = self.s.run("diff", "core/demo", "/etc/demo.env", "--show")
        self.assertIn("s3cret", out)
        rc, out = self.s.run("diff", "core/demo", "/root/.demo-secret")
        self.assertIn("never shown", out)

    def test_install_commands_print_and_never_run(self):
        self.s.run("render", "core/demo")
        rc, out = self.s.run("install-commands", "core/demo")
        self.assertEqual(rc, 0, out)
        self.assertIn(f"sudo install -m 0644 -o {ME.split(':')[0]} -g {ME.split(':')[1]} {self.s.stack}/config/host/demo /etc/logrotate.d/demo", out)
        self.assertIn("[ -e /etc/demo.env ] || sudo install -m 0600", out)
        self.assertIn("sudo systemctl daemon-reload", out)
        self.assertIn("sudo logrotate -d /etc/logrotate.d/demo", out)
        self.assertIn("# /root/.demo-secret: a secret the operator creates", out)
        self.assertFalse((self.s.host / "etc" / "logrotate.d" / "demo").exists())

    # ----- manifest validation ------------------------------------------
    def test_a_bad_manifest_line_is_refused_with_its_number(self):
        self.s.manifest("config/stanza /etc/logrotate.d/demo 0644 root:root exact\n")
        rc, out = self.s.run("render", "core/demo")
        self.assertNotEqual(rc, 0)
        self.assertIn("line 1", out)
        self.assertIn("6 fields", out)
        self.s.manifest("config/none /etc/x 0644 root:root exact required\n")
        rc, out = self.s.run("render", "core/demo")
        self.assertIn("does not exist", out)
        self.s.manifest("config/stanza /etc/x 0644 root:root sometimes required\n")
        rc, out = self.s.run("render", "core/demo")
        self.assertIn("compare must be", out)


class ShippedManifests(unittest.TestCase):
    """The three manifests in the tree parse and render."""

    def test_render_every_shipped_manifest_into_a_scratch_copy(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for stack in ("core/traefik", "core/host-watchdog", "backup/borgmatic"):
            dst = tmp / stack
            shutil.copytree(REPO / stack, dst, ignore=shutil.ignore_patterns("volumes", "config/host", ".env"))
        (tmp / "scripts").mkdir()
        shutil.copy(TOOL, tmp / "scripts" / "host-files.sh")
        r = subprocess.run(["bash", str(tmp / "scripts" / "host-files.sh"), "render"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for expected in ("core/traefik/config/host/traefik", "core/traefik/config/host/traefik-watchdog.service",
                         "core/host-watchdog/config/host/docker-daemon-watchdog.sh",
                         "backup/borgmatic/config/host/config.yaml", "backup/borgmatic/config/host/borgmatic.service"):
            self.assertTrue((tmp / expected).is_file(), expected)
        stanza = (tmp / "core/traefik/config/host/traefik").read_text(encoding="utf-8")
        self.assertIn(f"{tmp}/core/traefik/volumes/logs/access.log", stanza)
        self.assertNotIn("/path/to/secure-docker-blueprint", stanza)


if __name__ == "__main__":
    unittest.main()
