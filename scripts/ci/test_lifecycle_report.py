#!/usr/bin/env python3
"""Regression cover for lifecycle-report.py: the per-stack row and the
generated findings block (DEC-080).

A stack carries no state. Its row shows the pin and its release date, the
newest upstream release, the CRITICAL and HIGH findings at the pin and the
date of the last test, with the version that ran where it differs from the
pin. These tests hold the pieces that decide what the row says:

- `bare_pin_value()`, `normalize_version()`, `pin_matches_verified()` — whether
  the version that ran is the version pinned. A difference is shown beside the
  date, never hidden and never a reason to drop the date.
- `pin_tag()` — the tag upstream-status.json is keyed by; a row written for
  another pin is not shown as the current one.
- `named_gap()`, `findings_block()`, `readme_with_block()` and the cells.

Run:
    python3 scripts/ci/test_lifecycle_report.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "lifecycle-report.py"

spec = importlib.util.spec_from_file_location("lifecycle_report", CHECKER)
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)


class BarePinValue(unittest.TestCase):
    def test_extracts_value_from_key_equals_value(self):
        self.assertEqual(lr.bare_pin_value("`APP_TAG=3.1.3`"), "3.1.3")

    def test_extracts_value_from_image_form(self):
        self.assertEqual(
            lr.bare_pin_value("`TRAEFIK_IMAGE=traefik:v3.7`"), "traefik:v3.7"
        )

    def test_host_installed_is_not_comparable(self):
        self.assertIsNone(lr.bare_pin_value("*host-installed*"))

    def test_no_pin_recorded_is_not_comparable(self):
        self.assertIsNone(lr.bare_pin_value("—"))


class NormalizeVersion(unittest.TestCase):
    def test_strips_leading_v(self):
        self.assertEqual(lr.normalize_version("v2.20.13"), "2.20.13")

    def test_leaves_bare_number_alone(self):
        self.assertEqual(lr.normalize_version("2.20.13"), "2.20.13")

    def test_strips_digest_suffix(self):
        self.assertEqual(
            lr.normalize_version("v6.2.0-6@sha256:538cbb4a2273deadbeef"),
            "6.2.0-6",
        )

    def test_strips_image_name_prefix(self):
        self.assertEqual(lr.normalize_version("traefik:v3.7"), "3.7")

    def test_does_not_strip_v_from_a_word_that_merely_starts_with_it(self):
        # "version-v26.05.4" has no digit right after the leading "v", so it
        # is not the `vX.Y.Z` shape this strips — left alone rather than
        # mis-parsed into "ersion-v26.05.4".
        self.assertEqual(lr.normalize_version("version-v26.05.4"), "version-v26.05.4")


class PinMatchesVerified(unittest.TestCase):
    def test_identical_versions_match(self):
        self.assertTrue(lr.pin_matches_verified("v1.7.8", "v1.7.8"))

    def test_v_prefix_difference_alone_still_matches(self):
        self.assertTrue(lr.pin_matches_verified("26.7.3", "v26.7.3"))

    def test_genuinely_different_versions_do_not_match(self):
        # apps/paperless-ngx, as pinned and verified in the live repository.
        self.assertFalse(lr.pin_matches_verified("3.1.3", "v2.20.13"))

    def test_different_major_versions_do_not_match(self):
        self.assertFalse(lr.pin_matches_verified("2.39.7", "v2.39.1"))

    def test_documented_variant_suffix_on_the_pin_still_matches(self):
        # apps/tymeslot/UPSTREAM.md states the equivalence explicitly:
        # "Pinning: the `-slim` tag, digest-pinned" — a repository-authored
        # fact, not an inferred one.
        self.assertTrue(lr.pin_matches_verified("1.15.1-slim", "v1.15.1"))

    def test_undocumented_suffix_difference_does_not_match(self):
        # No stack documents "-edge" as a packaging variant, so a bare
        # suffix difference outside KNOWN_VARIANT_SUFFIXES is a mismatch,
        # not something this function guesses at.
        self.assertFalse(lr.pin_matches_verified("1.15.1-edge", "v1.15.1"))

    def test_floating_minor_pin_does_not_match_the_exact_patch_verified(self):
        # A pin that floats the patch (`traefik:v3.7`, core/traefik's pin until
        # 2026-11-02) with a stamp that names exactly which patch was tested
        # (`v3.7.13`) against that floating pin at the time. The pin can resolve to a newer patch
        # upstream with no repository change at all, so the row names the
        # version that ran beside the date.
        self.assertFalse(lr.pin_matches_verified("traefik:v3.7", "v3.7.13"))

    def test_multi_component_verification_compares_the_primary_only(self):
        # A stamp naming a sidecar too (`v3.7.13, socket-proxy v0.5.0`) is
        # compared against pinned_version()'s primary pin using only the
        # first component — exact match still required.
        self.assertTrue(
            lr.pin_matches_verified("v3.7.13", "v3.7.13, socket-proxy v0.5.0")
        )
        self.assertFalse(
            lr.pin_matches_verified("v3.9.0", "v3.7.13, socket-proxy v0.5.0")
        )


class PinnedVersionKey(unittest.TestCase):
    """Which variable names the stack's own version."""

    def _pinned(self, env: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp) / "core" / "widget"
            stack.mkdir(parents=True)
            (stack / "docker-compose.yml").write_text("services: {}\n")
            (stack / ".env.example").write_text(env)
            return lr.pinned_version(stack)

    def test_a_vendor_version_variable_outranks_a_later_datastore_tag(self):
        pinned = self._pinned("WIDGET_VERSION=v1.2.3\nCACHE_TAG=9.1-alpine\n")
        self.assertEqual(pinned, "`WIDGET_VERSION=v1.2.3`")

    def test_app_tag_still_wins_over_everything(self):
        pinned = self._pinned("WIDGET_VERSION=v1.2.3\nAPP_TAG=4.5.6\n")
        self.assertEqual(pinned, "`APP_TAG=4.5.6`")


class TestedVersionEndToEnd(unittest.TestCase):
    """last_verified() + pinned_version() + the comparison, against a real
    stack directory."""

    def _write_stack(self, root: Path, app_tag: str, verified_stamp: str) -> Path:
        stack = root / "apps" / "widget"
        stack.mkdir(parents=True)
        (stack / "docker-compose.yml").write_text(
            "services:\n  app:\n    image: example/widget:1.0\n"
        )
        (stack / ".env.example").write_text(f"APP_TAG={app_tag}\n")
        (stack / "UPSTREAM.md").write_text(
            f"# Widget\n\n- **Last verified:** {verified_stamp}\n"
        )
        return stack

    def test_a_moved_pin_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = self._write_stack(Path(tmp), "2.0.0", "2026-01-01 (v1.0.0)")
            verified, current_format, verified_version = lr.last_verified(stack)
            pinned = lr.pinned_version(stack)
            self.assertTrue(current_format)
            self.assertEqual(verified_version, "v1.0.0")
            pin_value = lr.bare_pin_value(pinned)
            self.assertIsNotNone(pin_value)
            self.assertFalse(lr.pin_matches_verified(pin_value, verified_version))

    def test_a_new_run_at_the_pin_matches_again(self):
        """A host run at the current pin records its version; the row then
        names no differing version."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stack = self._write_stack(root, "2.0.0", "2026-01-01 (v1.0.0)")

            _, _, stale_version = lr.last_verified(stack)
            pinned = lr.pinned_version(stack)
            pin_value = lr.bare_pin_value(pinned)
            self.assertFalse(lr.pin_matches_verified(pin_value, stale_version))

            (stack / "UPSTREAM.md").write_text(
                "# Widget\n\n- **Last verified:** 2026-02-01 (2.0.0)\n"
            )
            _, current_format, fixed_version = lr.last_verified(stack)
            self.assertTrue(current_format)
            self.assertTrue(lr.pin_matches_verified(pin_value, fixed_version))



class OpenFindings(unittest.TestCase):
    """A stack that ships recorded exceptions is counted and marked."""

    def test_counts_every_stack_an_exception_names(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "b.json"
            base.write_text(json.dumps({"exceptions": {
                "postgres": {"stacks": ["apps/a", "apps/b"], "cves": ["C1", "C2"]},
                "redis": {"stacks": ["apps/a"], "cves": ["C3"]},
            }}))
            old, lr.TRIVY_BASELINE = lr.TRIVY_BASELINE, base
            try:
                self.assertEqual(lr.open_findings(), {"apps/a": 3, "apps/b": 2})
            finally:
                lr.TRIVY_BASELINE = old

    def test_section_heading_is_recognised(self):
        self.assertTrue(lr.OPEN_FINDINGS.search("x\n## Open findings\n\ny"))
        self.assertFalse(lr.OPEN_FINDINGS.search("## Open findings and more"))


class PinTag(unittest.TestCase):
    def test_tag_of_an_app_tag_pin(self):
        self.assertEqual(lr.pin_tag("`APP_TAG=1.37.5`"), "1.37.5")

    def test_tag_of_an_image_pin_keeps_the_v(self):
        self.assertEqual(lr.pin_tag("`TRAEFIK_IMAGE=traefik:v3.7.17`"), "v3.7.17")

    def test_digest_is_dropped(self):
        self.assertEqual(lr.pin_tag("`APP_TAG=main@sha256:4981…`"), "main")

    def test_host_installed_has_no_tag(self):
        self.assertIsNone(lr.pin_tag("*host-installed*"))


class NamedGap(unittest.TestCase):
    def _gap(self, line: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp)
            (stack / "UPSTREAM.md").write_text(f"# W\n\n- **Last verified:** {line}\n")
            return lr.named_gap(stack)

    def test_not_yet_with_a_reason(self):
        self.assertEqual(self._gap("not yet — needs a GPU host"), "needs a GPU host")

    def test_dash_with_a_reason_in_parentheses(self):
        self.assertEqual(self._gap("— (not yet run on a live server)"),
                         "not yet run on a live server")

    def test_a_date_is_not_a_gap(self):
        self.assertEqual(self._gap("2026-11-02 (1.37.4)"), "")


UP = {
    "checked": "2026-11-08", "pinned": "1.37.5", "pinned_date": "2026-11-01",
    "newest": "1.37.5", "newest_date": "2026-11-01", "status": "current",
    "archived": False, "quiet": False, "last_release": "2026-11-01",
    "findings": {"critical": 1, "high": 28, "unscanned": [], "images": {
        "mariadb:12.3.3": {"system": [0, 1], "programs": [1, 25]},
        "vaultwarden/server:1.37.5": {"system": [0, 3]},
    }},
}


class FindingsBlock(unittest.TestCase):
    def test_counts_per_image_and_area(self):
        block = lr.findings_block("apps/vaultwarden", UP, True, "1.37.5")
        self.assertIn("| `mariadb:12.3.3` | 0 · 1 | — | 1 · 25 |", block)
        self.assertIn("the newest upstream release", block)
        self.assertTrue(block.startswith(lr.FINDINGS_START))
        self.assertTrue(block.endswith(lr.FINDINGS_END))

    def test_a_row_for_another_pin_is_not_shown(self):
        block = lr.findings_block("apps/vaultwarden", UP, False, "1.38.0")
        self.assertIn("Not scanned at the pin `1.38.0` yet.", block)
        self.assertNotIn("mariadb", block)

    def test_the_block_is_replaced_and_the_text_around_it_kept(self):
        readme = "# W\n\n## Open findings\n\nWhy it stays.\n"
        first = lr.readme_with_block(readme, "BLOCK")
        self.assertEqual(first, "# W\n\n## Open findings\n\nBLOCK\n\nWhy it stays.\n")
        block = lr.findings_block("apps/vaultwarden", UP, True, "1.37.5")
        once = lr.readme_with_block(readme, block)
        self.assertEqual(lr.readme_with_block(once, block), once)
        self.assertIn("Why it stays.", once)

    def test_a_section_is_added_before_details(self):
        readme = "# W\n\n## Backup\n\nx\n\n## Details\n\ny\n"
        out = lr.readme_with_block(readme, "BLOCK")
        self.assertIn("## Open findings\n\nBLOCK\n\n## Details", out)


class Cells(unittest.TestCase):
    def row(self, **kw):
        r = {
            "stack": "apps/widget", "category": "apps", "pinned": "`APP_TAG=2.0.0`",
            "tag": "2.0.0", "pinned_date": "2026-10-01", "upstream": "current",
            "newest": "2.0.0", "newest_date": "2026-10-01", "checked": "2026-11-08",
            "archived": False, "quiet": False, "last_release": "2026-10-01",
            "critical": 1, "high": 4, "marked": True,
            "tested": "2026-09-01", "tested_anchored": True, "tested_version": "1.0.0",
            "tested_differs": True, "restored": True, "gap": "",
            "backup": "documented", "restore": "documented", "local": True,
        }
        r.update(kw)
        return r

    def test_a_moved_pin_keeps_the_test_date_and_names_the_version(self):
        self.assertEqual(lr.tested_cell(self.row()),
                         "[2026-09-01](apps/widget/UPSTREAM.md) · with restore · ran `1.0.0`")

    def test_current_pin(self):
        self.assertTrue(lr.newest_cell(self.row()).startswith("= Pin"))

    def test_newer_release_and_quiet_upstream(self):
        cell = lr.newest_cell(self.row(upstream="behind", newest="2.1.0",
                                       newest_date="2026-11-05"))
        self.assertTrue(cell.startswith("`2.1.0` · 2026-11-05"))
        cell = lr.newest_cell(self.row(quiet=True, last_release="2024-10-22"))
        self.assertIn("⚠️ no release since 2024-10-22", cell)

    def test_not_scanned_is_not_zero(self):
        self.assertEqual(lr.findings_cell(self.row(critical=None, high=None)), "—")
        self.assertEqual(lr.findings_cell(self.row()),
                         "[1 · 4](apps/widget/README.md#open-findings)")

    def test_a_named_gap(self):
        self.assertEqual(
            lr.tested_cell(self.row(tested="—", tested_anchored=False, gap="needs a GPU")),
            "— · [gap named](apps/widget/UPSTREAM.md)")

    def test_render_has_no_state(self):
        report = lr.render([self.row()])
        self.assertIn("| Stack | Pin | Newest | CRITICAL · HIGH | Last tested |", report)
        for word in ("scaffolded", "baseline-aligned", "ops-proven"):
            self.assertNotIn(word, report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
