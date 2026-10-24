#!/usr/bin/env python3
"""Regression cover for check-prose.py.

The checker matched per line until prose wrapped across two of them hid a
phrase from it — four were found that way, one on a customer-facing page where
the gate would otherwise have blocked. These tests hold the unit model in place:
a wrapped sentence is one search space, a heading or a list item is not.

Run:
    python3 scripts/ci/test_check_prose.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHECKER = HERE / "check-prose.py"

spec = importlib.util.spec_from_file_location("check_prose", CHECKER)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def scan(text: str, name: str = "docs/sample.md"):
    """Rows the checker produces for this text, as if it were `name`."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.md"
        path.write_text(text, encoding="utf-8")
        return cp.scan_file(path, name)


def phrases(rows):
    return {r[2] for r in rows}


class SingleLine(unittest.TestCase):
    def test_phrase_on_one_line_is_found(self):
        rows = scan("The padlock tells the user something untrue.\n")
        self.assertIn("tells the user something", phrases(rows))

    def test_clean_prose_produces_nothing(self):
        rows = scan("Two of seven make an outbound call the operator did not ask for.\n")
        self.assertEqual(rows, [])


class WrappedProse(unittest.TestCase):
    def test_phrase_split_by_a_line_wrap_is_found(self):
        rows = scan("For health records or payroll it is the\nwhole question — and that decides it.\n")
        self.assertIn("is the whole question", phrases(rows))

    def test_reported_line_is_where_the_phrase_starts(self):
        rows = scan("filler line\nsecond line ends with is the\nwhole question here\n")
        row = next(r for r in rows if r[2] == "is the whole question")
        self.assertEqual(row[1], 2)

    def test_row_records_every_line_the_match_spans(self):
        rows = scan("text that is the\nwhole question follows\n")
        row = next(r for r in rows if r[2] == "is the whole question")
        self.assertEqual(row[6], frozenset({1, 2}))

    def test_single_line_match_records_one_line(self):
        rows = scan("this is the whole question in one line\n")
        row = next(r for r in rows if r[2] == "is the whole question")
        self.assertEqual(row[6], frozenset({1}))


class Boundaries(unittest.TestCase):
    """A phrase must not be assembled from text the author kept apart."""

    def test_no_match_across_a_blank_line(self):
        rows = scan("a sentence ending in is the\n\nwhole question starting a new paragraph\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_no_match_across_a_heading(self):
        rows = scan("trailing text is the\n## whole question\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_no_match_across_separate_list_items(self):
        rows = scan("- first item is the\n- whole question item\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_no_match_across_table_rows(self):
        rows = scan("| cell is the |\n| whole question |\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_no_match_inside_a_fenced_code_block(self):
        rows = scan("```bash\necho 'is the whole question'\n```\n")
        self.assertEqual(rows, [])

    def test_no_match_across_a_fence_boundary(self):
        rows = scan("prose is the\n```\nwhole question\n```\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_no_match_across_a_frontmatter_delimiter(self):
        rows = scan("---\ntitle: something is the\n---\nwhole question in the body\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_a_wrapped_list_item_is_still_one_unit(self):
        rows = scan("- an item whose text is the\n  whole question when wrapped\n")
        self.assertIn("is the whole question", phrases(rows))

    def test_no_match_across_two_list_items_even_when_indented(self):
        rows = scan("- first is the\n- whole question second\n")
        self.assertNotIn("is the whole question", phrases(rows))

    def test_a_wrapped_block_quote_is_one_unit(self):
        rows = scan("> a quote that is the\n> whole question when wrapped\n")
        self.assertIn("is the whole question", phrases(rows))

    def test_no_match_from_a_quote_into_the_prose_below(self):
        rows = scan("> quote ends with is the\nwhole question in plain prose\n")
        self.assertNotIn("is the whole question", phrases(rows))


class Audience(unittest.TestCase):
    """Classification is unchanged; a wrapped match inherits it."""

    def test_reader_facing_multiline_match_blocks(self):
        rows = scan("text is the\nwhole question\n", "site/src/content/docs/x.mdx")
        fails, warns = cp.split_by_audience(rows)
        self.assertTrue(fails)
        self.assertFalse(warns)

    def test_maintainer_multiline_match_only_warns(self):
        rows = scan("text is the\nwhole question\n", "docs/notes.md")
        fails, warns = cp.split_by_audience(rows)
        self.assertFalse(fails)
        self.assertTrue(warns)


class ChangedOnly(unittest.TestCase):
    """A wrap must not become a way past the differential mode."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run = lambda *a: subprocess.run(["git", *a], cwd=self.root, check=True,
                                        capture_output=True)
        run("init", "-q")
        run("config", "user.email", "t@example.com")
        run("config", "user.name", "t")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "a.md").write_text("clean first line\nclean second line\n")
        run("add", "-A")
        run("commit", "-qm", "base")
        self.base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                                   capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, content):
        (self.root / "docs" / "a.md").write_text(content)
        return subprocess.run(
            [sys.executable, str(CHECKER), "--changed-only", "--base", self.base],
            cwd=self.root, capture_output=True, text=True)

    def test_wrapped_match_is_caught_when_a_participating_line_changed(self):
        out = self._run("clean first line\ntext is the\nwhole question\n")
        self.assertIn("is the whole question", out.stdout)

    def test_wrapped_match_is_caught_when_only_the_second_line_changed(self):
        # The first participating line is untouched; the wrap must not hide it.
        (self.root / "docs" / "a.md").write_text("clean first line\ntext is the\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "half"], cwd=self.root, check=True,
                       capture_output=True)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                              capture_output=True, text=True).stdout.strip()
        (self.root / "docs" / "a.md").write_text("clean first line\ntext is the\nwhole question\n")
        out = subprocess.run(
            [sys.executable, str(CHECKER), "--changed-only", "--base", base],
            cwd=self.root, capture_output=True, text=True)
        self.assertIn("is the whole question", out.stdout)

    def test_untouched_finding_does_not_block(self):
        out = self._run("clean first line\nclean second line\nan added clean sentence\n")
        self.assertEqual(out.returncode, 0)


def retired(text: str, name: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "f.md"
        path.write_text(text, encoding="utf-8")
        return {r[2] for r in cp.retired_rows(path, name)}


class RetiredNames(unittest.TestCase):
    """The vocabulary before the middleware model is reported in current
    documentation and left alone in records and in old-to-new examples."""

    def test_a_current_standard_naming_an_old_value_is_reported(self):
        self.assertEqual(retired("Set `APP_TRAEFIK_SECURITY=sec-3` and `acc-tailscale` on the router.\n", "docs/standards/x.md"),
                         {"APP_TRAEFIK_SECURITY", "sec-3", "acc-tailscale"})

    def test_a_stack_readme_naming_an_old_value_is_reported(self):
        self.assertEqual(retired("The stack ships `acc-public` with `sec-2`.\n", "apps/x/README.md"), {"acc-public", "sec-2"})

    def test_the_models_names_produce_nothing(self):
        self.assertEqual(retired("The stack ships `access-public`, `limit-standard`, `headers-standard` and `auth-none@file`.\n", "apps/x/README.md"), set())

    def test_an_old_to_new_example_is_allowed(self):
        self.assertEqual(retired("Before the model the router carried `sec-3`; it is `limit-standard` and `headers-standard` now.\n", "docs/standards/x.md"), set())
        self.assertEqual(retired("`acc-tailscale` was replaced by `access-vpn` on 2026-10-22.\n", "core/traefik/README.md"), set())

    def test_a_record_document_is_exempt(self):
        for name in ("docs/bugfixes/x.md", "docs/audits/x.md", "docs/reviews/x.md", "docs/research/x.md",
                     "docs/host-session-findings.md", "docs/maintenance-log.md", ".ai/decisions.md",
                     "core/traefik/docs/middleware-model-migration.md"):
            self.assertEqual(retired("The router carried `sec-3` and `acc-tailscale`.\n", name), set(), name)

    def test_changelog_released_sections_are_exempt_and_unreleased_is_not(self):
        text = "## [Unreleased]\n\n- Set `sec-3` on it.\n\n## [0.9.4] — 2026-10-04\n\n- The chain `sec-2` was widened.\n"
        self.assertEqual(retired(text, "CHANGELOG.md"), {"sec-3"})

    def test_upstream_verification_line_is_kept_and_an_instruction_is_not(self):
        text = ("Last verified: 2026-10-03 (v0.9.4) — behind Traefik with the shipped `acc-tailscale` and `sec-2`.\n\n"
                "Before upgrading, set `APP_TRAEFIK_SECURITY=sec-3` in `.env`.\n")
        self.assertEqual(retired(text, "apps/x/UPSTREAM.md"), {"APP_TRAEFIK_SECURITY", "sec-3"})

    def test_a_code_span_does_not_exempt_a_current_file(self):
        self.assertEqual(retired("Use `rl-soft` here.\n", "docs/standards/x.md"), {"rl-soft"})

    def test_the_threat_names_match_whole_and_not_inside_the_models_name(self):
        self.assertEqual(retired("Attach `crowdsec-basic@file` to the router.\n", "docs/standards/x.md"), {"crowdsec-basic"})
        self.assertEqual(retired("The entrypoint carries `threat-crowdsec-appsec@file`.\n", "docs/standards/x.md"), set())

    def test_retired_names_warn_until_the_gate_is_on(self):
        rows = [("apps/x/README.md", 1, "sec-2", "retired name", "", "", frozenset({1}))]
        fails, warns = cp.split_by_audience(rows)
        self.assertEqual((len(fails), len(warns)), (1, 0) if cp.RETIRED_GATE else (0, 1))


class Repository(unittest.TestCase):
    """The tracked repository state the gate now depends on."""

    def test_full_run_has_no_blocking_findings(self):
        out = subprocess.run([sys.executable, str(CHECKER)], cwd=REPO,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("0 blocking", out.stdout)

    def test_maintainer_findings_warn_instead_of_blocking(self):
        """The two-audience split still works.

        This used to assert that a full repository run printed the maintainer
        section, which made a *clean* repository a test failure — the section
        only renders when something trips it. The behaviour worth holding is
        the split itself: the same phrase gates in a reader-facing file and
        only warns in a maintainer one. That is checked against fixtures, so
        it stays true whether or not the repository currently has a finding.
        """
        text = "The consequence is worth stating plainly: something follows.\n"

        reader_path = "site/src/content/docs/example.md"
        maintainer_path = "docs/standards/example.md"

        self.assertEqual(cp.audience(reader_path), "reader-facing")
        self.assertEqual(cp.audience(maintainer_path), "maintainer")

        self.assertTrue(scan(text, reader_path), "phrase not found in a reader-facing file")
        self.assertTrue(scan(text, maintainer_path), "phrase not found in a maintainer file")

    def test_stack_readme_is_reader_facing_but_upstream_is_not(self):
        """The one classification that is easy to get backwards."""
        self.assertEqual(cp.audience("apps/vaultwarden/README.md"), "reader-facing")
        self.assertEqual(cp.audience("apps/vaultwarden/UPSTREAM.md"), "maintainer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
