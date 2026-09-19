#!/usr/bin/env python3
"""Regression cover for the pin-drift check in lifecycle-report.py.

`baseline-aligned`/`ops-proven` used to be granted on the strength of *any*
correctly-formatted `Last verified: DATE (vX.Y.Z)` stamp, with nothing
checking whether that named version still matches the tag currently pinned
in `.env.example`. A pin bump therefore left a stale verification claim
standing — confirmed against the live repository before this fix: 17 of the
30 stacks that claimed `baseline-aligned` were verified against a version
their own `.env.example` no longer pins, or (`core/traefik`) pin a version
component that floats independent of any repository change at all.

The comparison prefers exactness on purpose: an earlier draft tolerated any
one-sided version prefix at a boundary, which is what let `traefik:v3.7`
count as a match for the exact `v3.7.13` that was actually tested — silently
re-introducing the same kind of overclaim this check exists to catch, since
that pin can resolve to a newer patch upstream with no commit here at all.
Normalization now stops at formatting this repository's data shows really is
formatting (a `v`, an image-name prefix, a digest suffix) plus the one
packaging variant a stack's own `UPSTREAM.md` documents as equivalent
(`-slim`, per `apps/tymeslot`).

These tests hold the comparison itself in place — `bare_pin_value()`,
`normalize_version()`, `pin_matches_verified()` — plus one end-to-end check
that correcting the stamp on a real stack directory restores the state a
correct verification should produce.

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
        # "Based on version: `1.15.1` (`-slim` tag, digest-pinned)" — a
        # repository-authored fact, not an inferred one.
        self.assertTrue(lr.pin_matches_verified("1.15.1-slim", "v1.15.1"))

    def test_undocumented_suffix_difference_does_not_match(self):
        # No stack documents "-edge" as a packaging variant, so a bare
        # suffix difference outside KNOWN_VARIANT_SUFFIXES is a mismatch,
        # not something this function guesses at.
        self.assertFalse(lr.pin_matches_verified("1.15.1-edge", "v1.15.1"))

    def test_floating_minor_pin_does_not_match_the_exact_patch_verified(self):
        # core/traefik pins float the patch on purpose (`traefik:v3.7`) and
        # the stamp names exactly which patch was tested (`v3.7.13`) against
        # that floating pin at the time. The pin can resolve to a newer patch
        # upstream with no repository change at all, so this must NOT be
        # treated as freshness evidence — it is reported as `pin-drifted`
        # like any other mismatch, with no separate exemption.
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


class DriftEndToEnd(unittest.TestCase):
    """last_verified() + pinned_version() + the comparison, against a real
    stack directory — no subprocess/baseline dependency, since both those
    functions only read files."""

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

    def test_drifted_pin_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = self._write_stack(Path(tmp), "2.0.0", "2026-01-01 (v1.0.0)")
            verified, current_format, verified_version = lr.last_verified(stack)
            pinned = lr.pinned_version(stack)
            self.assertTrue(current_format)
            self.assertEqual(verified_version, "v1.0.0")
            pin_value = lr.bare_pin_value(pinned)
            self.assertIsNotNone(pin_value)
            self.assertFalse(lr.pin_matches_verified(pin_value, verified_version))

    def test_correcting_the_stamp_restores_the_matching_state(self):
        """The exact 'fix' an operator performs: bump the stamp's version to
        the one that was actually just verified. The drift signal clears."""
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
