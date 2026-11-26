#!/usr/bin/env python3
"""scripts/stacks.sh — apply, update and status against a scratch origin with
two releases and a scratch partial checkout of it, so no real host is touched.

Run:
    python3 scripts/ci/test_stacks.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts" / "stacks.sh"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def git(cwd, *args):
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Scratch:
    """An origin with releases v1 and v2, and a partial checkout of v1."""

    STACKS = ["core/traefik", "core/crowdsec", "apps/whoami", "apps/vaultwarden",
              "apps/retired", "docs/standards"]

    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        self.origin = self.root / "origin"
        self.host = self.root / "host"
        o = self.origin
        o.mkdir()
        git(o, "init", "-q", "-b", "main")
        write(o / ".gitignore", "/stacks\n/custom/\n**/.env\n**/volumes/\n**/.secrets/\n")
        write(o / "README.md", "root\n")
        write(o / "stacks.example", "core/traefik\n")
        (o / "scripts").mkdir()
        shutil.copy(TOOL, o / "scripts" / "stacks.sh")
        for s in self.STACKS:
            write(o / s / "README.md", f"{s} v1\n")
        git(o, "add", "-A")
        git(o, "commit", "-q", "-m", "v1")
        git(o, "tag", "v1")
        write(o / "core/traefik/README.md", "core/traefik v2\n")
        write(o / "apps/nextcloud/README.md", "apps/nextcloud v2\n")
        git(o, "rm", "-q", "-r", "apps/retired")
        git(o, "commit", "-q", "-am", "v2")
        git(o, "add", "-A")
        git(o, "commit", "-q", "--allow-empty", "-m", "v2 files")
        git(o, "tag", "v2")

        git(self.root, "clone", "-q", "--sparse", "--no-checkout", o.as_uri(), str(self.host))
        git(self.host, "-c", "advice.detachedHead=false", "checkout", "-q", "v1")
        git(self.host, "sparse-checkout", "set", "scripts", "docs/standards")

    def stacks(self, *lines):
        write(self.host / "stacks", "\n".join(lines) + "\n")

    def run(self, *args, stdin=None):
        env = {**os.environ, **GIT_ENV}
        return subprocess.run(["bash", str(self.host / "scripts" / "stacks.sh"), *args],
                              cwd=self.host, env=env, capture_output=True, text=True,
                              stdin=stdin if stdin is not None else subprocess.DEVNULL)

    def own_stack(self, name, readme, tag=None):
        """custom/<name> as a checkout of its own repository, with data of its own."""
        d = self.host / "custom" / name
        d.mkdir(parents=True)
        git(d, "init", "-q", "-b", "main")
        write(d / "README.md", readme)
        write(d / ".gitignore", ".env\nvolumes/\n")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "init")
        if tag:
            git(d, "tag", tag)
        write(d / ".env", "X=1\n")
        write(d / "volumes/data/site", "data\n")
        return d

    def checked_out(self):
        return sorted(git(self.host, "sparse-checkout", "list").split())

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


class StacksTest(unittest.TestCase):
    def setUp(self):
        self.s = Scratch()

    def tearDown(self):
        self.s.cleanup()

    def test_apply_checks_out_the_file_plus_required_paths(self):
        self.s.stacks("# base", "core/traefik", "apps/whoami/   # trailing slash and comment", "")
        r = self.s.run("apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.s.checked_out(),
                         ["apps/whoami", "core/traefik", "docs/standards", "scripts"])
        self.assertTrue((self.s.host / "core/traefik/README.md").is_file())
        self.assertFalse((self.s.host / "core/crowdsec").exists())

    def test_apply_refuses_to_drop_a_stack_with_local_files(self):
        self.s.stacks("core/traefik", "apps/vaultwarden")
        self.assertEqual(self.s.run("apply").returncode, 0)
        write(self.s.host / "apps/vaultwarden/.env", "X=1\n")
        write(self.s.host / "apps/vaultwarden/volumes/data/db", "data\n")
        self.s.stacks("core/traefik")
        r = self.s.run("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED: apps/vaultwarden", r.stdout)
        self.assertIn("apps/vaultwarden/.env", r.stdout)
        self.assertIn("apps/vaultwarden/volumes/data/db", r.stdout)
        self.assertIn("apps/vaultwarden", self.s.checked_out())
        self.assertTrue((self.s.host / "apps/vaultwarden/volumes/data/db").is_file())

    def data_elsewhere(self, name):
        """A stack's files outside the checkout: .env, a secret and its data."""
        d = self.s.root / "data" / name
        write(d / ".env", "X=1\n")
        write(d / ".secrets/token.txt", "secret\n")
        write(d / "volumes/state", "data\n")
        return d

    def assertIntact(self, d):
        for f in (".env", ".secrets/token.txt", "volumes/state"):
            self.assertTrue((d / f).is_file(), f)

    def test_apply_refuses_a_symbolic_link_on_a_path_not_checked_out(self):
        # Git would delete .env, .secrets/ and volumes/ in the link's target:
        # the directory is outside the checkout and holds only ignored files.
        self.s.stacks("core/traefik")
        self.assertEqual(self.s.run("apply").returncode, 0)
        data = self.data_elsewhere("crowdsec")
        (self.s.host / "core/crowdsec").symlink_to(data)
        self.s.stacks("core/traefik", "apps/whoami")
        r = self.s.run("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing applied", r.stderr)
        self.assertRegex(r.stdout, r"core/crowdsec\s+symbolic link to ")
        self.assertIntact(data)
        self.assertNotIn("apps/whoami", self.s.checked_out())

    def test_apply_refuses_files_on_a_path_not_checked_out(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        data = self.data_elsewhere("vaultwarden")
        shutil.copytree(data, self.s.host / "apps/vaultwarden")
        r = self.s.run("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"apps/vaultwarden\s+directory with files")
        self.assertNotRegex(r.stdout, r"\n   apps\s")
        self.assertIntact(self.s.host / "apps/vaultwarden")

    def test_apply_leaves_an_empty_directory_alone(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        (self.s.host / "apps/vaultwarden").mkdir(parents=True)
        r = self.s.run("apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_update_refuses_a_link_on_a_path_the_target_adds(self):
        # apps/nextcloud exists in v2 only; the check reads the target too.
        self.s.stacks("core/traefik")
        self.s.run("apply")
        data = self.data_elsewhere("nextcloud")
        (self.s.host / "apps").mkdir(exist_ok=True)
        (self.s.host / "apps/nextcloud").symlink_to(data)
        r = self.s.run("update", "v2", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing changed", r.stderr)
        self.assertRegex(r.stdout, r"apps/nextcloud\s+symbolic link to ")
        self.assertEqual(git(self.s.host, "describe", "--tags", "--exact-match").strip(), "v1")
        self.assertIntact(data)

    def test_status_names_what_sits_on_a_path_not_checked_out(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        (self.s.host / "core/crowdsec").symlink_to(self.data_elsewhere("crowdsec"))
        r = self.s.run("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Not checked out, yet something is there", r.stdout)
        self.assertRegex(r.stdout, r"core/crowdsec\s+symbolic link to ")

    def test_apply_drops_a_stack_without_local_files(self):
        self.s.stacks("core/traefik", "apps/whoami")
        self.s.run("apply")
        self.s.stacks("core/traefik")
        r = self.s.run("apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("removed: apps/whoami", r.stdout)
        self.assertNotIn("apps/whoami", self.s.checked_out())

    def test_apply_rejects_unknown_and_invalid_paths(self):
        before = self.s.checked_out()
        for bad in ("core/traefk", "../etc", "/core/traefik", "apps/../core"):
            self.s.stacks("core/traefik", bad)
            r = self.s.run("apply")
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn("nothing applied", r.stderr, bad)
            self.assertEqual(self.s.checked_out(), before, bad)

    def test_apply_without_stacks_file_says_how_to_start(self):
        r = self.s.run("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cp stacks.example stacks", r.stderr)

    def test_update_previews_only_the_selected_stacks_and_takes_the_release(self):
        self.s.stacks("core/traefik", "apps/whoami")
        self.s.run("apply")
        r = self.s.run("update", "v2", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("core/traefik/README.md", r.stdout)
        self.assertNotIn("apps/nextcloud", r.stdout)
        self.assertNotIn("apps/retired", r.stdout)
        self.assertEqual(git(self.s.host, "describe", "--tags", "--exact-match").strip(), "v2")
        self.assertIn("core/traefik v2", (self.s.host / "core/traefik/README.md").read_text())

    def test_update_without_a_terminal_needs_yes(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        r = self.s.run("update", "v2")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--yes", r.stderr)
        self.assertEqual(git(self.s.host, "describe", "--tags", "--exact-match").strip(), "v1")

    def test_update_reports_a_stack_missing_in_the_target(self):
        self.s.stacks("core/traefik", "apps/retired")
        self.s.run("apply")
        write(self.s.host / "apps/retired/.env", "X=1\n")
        r = self.s.run("update", "v2", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Not in v2", r.stdout)
        self.assertIn("apps/retired", r.stdout)
        self.assertTrue((self.s.host / "apps/retired/.env").is_file())

    def test_update_refuses_when_file_and_checkout_differ(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        self.s.stacks("core/traefik", "apps/whoami")
        r = self.s.run("update", "v2", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("apply first", r.stderr)

    def test_status_shows_the_difference(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        self.s.stacks("apps/whoami")
        r = self.s.run("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Release: v1", r.stdout)
        self.assertIn("In the file, not checked out", r.stdout)
        self.assertIn("Checked out, not in the file", r.stdout)


    def test_own_stacks_survive_apply_and_update(self):
        self.s.stacks("core/traefik", "apps/whoami")
        self.s.run("apply")
        d = self.s.own_stack("site", "# Site\n\n**Blueprint:** v1\n", tag="1.0.0")
        self.s.stacks("core/traefik")
        self.assertEqual(self.s.run("apply").returncode, 0)
        r = self.s.run("update", "v2", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((d / "volumes/data/site").is_file())
        self.assertTrue((d / ".env").is_file())
        self.assertEqual(git(self.s.host, "status", "--porcelain").strip(), "")

    def test_status_lists_own_stacks_with_their_blueprint_release(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        self.s.own_stack("site", "# Site\n\n**Blueprint:** v1\n", tag="1.0.0")
        self.s.own_stack("api", "# API\n")
        r = self.s.run("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Own stacks (custom/):", r.stdout)
        self.assertRegex(r.stdout, r"custom/site\s+1\.0\.0\s+follows Blueprint v1\n")
        self.assertIn("no Blueprint line in README.md", r.stdout)

    def test_update_names_own_stacks_and_the_release_they_follow(self):
        self.s.stacks("core/traefik")
        self.s.run("apply")
        self.s.own_stack("site", "**Blueprint:** v1\n")
        self.s.own_stack("api", "no line\n")
        r = self.s.run("update", "v2", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("custom/site follows v1 — read the Migration notes in CHANGELOG.md between v1 and v2", r.stdout)
        self.assertIn("custom/api names no Blueprint release", r.stdout)

    def test_apply_refuses_a_custom_line_and_says_why(self):
        before = self.s.checked_out()
        self.s.stacks("core/traefik", "custom/site")
        r = self.s.run("apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("managed by its own repository", r.stderr)
        self.assertEqual(self.s.checked_out(), before)


if __name__ == "__main__":
    unittest.main()
