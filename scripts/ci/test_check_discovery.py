#!/usr/bin/env python3
"""Regression cover for repository-scoped discovery in check-structure.py.

The checkers used to walk the filesystem, which made three different things
indistinguishable: blueprint content, generated runtime directories, and local
working material a developer had deliberately excluded. A gate that fails on the
second or third is reporting on the machine, not on the repository.

Discovery now asks Git what the repository contains — tracked files plus new
files that are not ignored. That keeps the useful local behaviour (a stack
written but not yet `git add`ed is still checked) while leaving out material
Git was told to ignore.

Run:
    python3 scripts/ci/test_check_discovery.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "check-structure.py"

spec = importlib.util.spec_from_file_location("check_structure_discovery", CHECKER)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


COMPOSE = """\
services:
  demo-app:
    image: example/image:1.0
    networks:
      - app-internal
networks:
  app-internal:
    internal: true
"""


def _git(root: Path, *args):
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


class RepositoryScopedDiscovery(unittest.TestCase):
    """Each test builds a real Git repository — the behaviour under test is
    Git's own notion of what the repository contains, so a stub would prove
    nothing."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "test@example.com")
        _git(self.root, "config", "user.name", "Test")
        self._cwd = os.getcwd()
        os.chdir(self.root)
        cs.repository_files.cache_clear()

    def tearDown(self):
        os.chdir(self._cwd)
        cs.repository_files.cache_clear()
        self._tmp.cleanup()

    def _stack(self, path: str) -> Path:
        app = self.root / path
        app.mkdir(parents=True, exist_ok=True)
        (app / "docker-compose.yml").write_text(COMPOSE)
        return app / "docker-compose.yml"

    def test_tracked_compose_file_is_checked(self):
        f = self._stack("apps/tracked")
        _git(self.root, "add", "apps/tracked/docker-compose.yml")
        _git(self.root, "commit", "-qm", "add stack")
        cs.repository_files.cache_clear()
        self.assertTrue(cs.in_repository(Path("apps/tracked/docker-compose.yml")))
        self.assertIn(Path("apps/tracked"), cs.find_apps())

    def test_new_untracked_but_not_ignored_file_is_checked(self):
        """The point of keeping untracked files in scope: a stack written but
        not yet added is exactly when the gate is most useful."""
        self._stack("apps/fresh")
        cs.repository_files.cache_clear()
        self.assertTrue(cs.in_repository(Path("apps/fresh/docker-compose.yml")))
        self.assertIn(Path("apps/fresh"), cs.find_apps())

    def test_gitignored_file_is_excluded(self):
        self._stack("apps/generated")
        (self.root / ".gitignore").write_text("apps/generated/\n")
        cs.repository_files.cache_clear()
        self.assertFalse(cs.in_repository(Path("apps/generated/docker-compose.yml")))
        self.assertNotIn(Path("apps/generated"), cs.find_apps())

    def test_git_info_exclude_material_is_excluded(self):
        """Local working material — the case that made a gate permanently red."""
        self._stack("core/workbench")
        exclude = self.root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text("core/workbench/\n")
        cs.repository_files.cache_clear()
        self.assertFalse(cs.in_repository(Path("core/workbench/docker-compose.yml")))
        self.assertNotIn(Path("core/workbench"), cs.find_apps())

    def test_falls_back_to_filesystem_when_git_is_unavailable(self):
        """A source tarball has no Git. The checker must still run — it simply
        cannot tell repository content from local material."""
        self._stack("apps/tarball")
        cs.repository_files.cache_clear()
        original = cs.repository_files
        try:
            cs.repository_files = lambda: None
            self.assertTrue(cs.in_repository(Path("anything/at/all.yml")))
        finally:
            cs.repository_files = original
            cs.repository_files.cache_clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)
