#!/usr/bin/env python3
"""Regression cover for the `unlisted-stack` rule in check-coverage.py.

Every other inventory in this repository is generated: `LIFECYCLE.md`,
`sovereignty.json` and `catalogue.json` all derive from the stacks themselves, so
a new stack reaches them by existing. The category README is the exception —
somebody has to add the row — and `apps/docling-serve` shipped without one while
every generated view already listed it.

The rule is tested against the real README text rather than through `main()`,
which additionally needs a Git tree and a lifecycle run to reach this point.

Run:
    python3 scripts/ci/test_check_coverage.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("check_coverage", HERE / "check-coverage.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


class UnlistedStack(unittest.TestCase):
    """A stack is listed when its category README links its directory."""

    def _tree(self, root: Path, readme: str) -> None:
        (root / "apps").mkdir(parents=True, exist_ok=True)
        (root / "apps" / "widget").mkdir(exist_ok=True)
        (root / "apps" / "README.md").write_text(readme)

    def _run(self, readme: str, dirs=("apps/widget",)) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._tree(root, readme)
            cwd = os.getcwd()
            os.chdir(root)
            try:
                return cc.unlisted_stacks(dirs)
            finally:
                os.chdir(cwd)

    def test_a_stack_its_category_readme_never_links_is_reported(self):
        readme = "# Apps\n\n| App | Stack |\n|---|---|\n| Widget | Single container |\n"
        self.assertEqual(self._run(readme), ["apps/widget"])

    def test_restoring_the_link_clears_it(self):
        readme = "# Apps\n\n| App | Stack |\n|---|---|\n| [Widget](widget/) | Single container |\n"
        self.assertEqual(self._run(readme), [])

    def test_a_prose_mention_without_a_link_is_not_enough(self):
        """The row has to be reachable, not merely present as a word."""
        self.assertEqual(self._run("# Apps\n\nWidget is included.\n"), ["apps/widget"])

    def test_a_similarly_named_stack_does_not_satisfy_it(self):
        readme = "# Apps\n\n| [Widget Pro](widget-pro/) | Two containers |\n"
        self.assertEqual(self._run(readme), ["apps/widget"])

    def test_a_root_without_a_readme_is_not_reported(self):
        """`development/` carries patterns, not catalogue rows."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "development" / "static-site").mkdir(parents=True)
            cwd = os.getcwd()
            os.chdir(root)
            try:
                self.assertEqual(cc.unlisted_stacks(["development/static-site"]), [])
            finally:
                os.chdir(cwd)

    def test_a_host_installed_component_is_judged_the_same_way(self):
        """It has no compose file, but it still needs to be findable."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backup").mkdir(parents=True)
            (root / "backup" / "README.md").write_text("# Backup\n\n| Borgmatic | host |\n")
            cwd = os.getcwd()
            os.chdir(root)
            try:
                self.assertEqual(cc.unlisted_stacks(["backup/borgmatic"]), ["backup/borgmatic"])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
