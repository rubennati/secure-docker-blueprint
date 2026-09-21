"""Tests for the CRITICAL gate over Trivy's per-image reports.

The gate exists because the scan blocked nothing. Its whole value is that a
finding nobody has accounted for cannot pass, so the cases below are mostly
about what must *fail*: an unrecorded CVE, and a report that could not be read.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "trivy_gate", Path(__file__).with_name("trivy-gate.py")
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def _report(tmp, name, image, criticals=(), highs=()):
    vulns = [{"Severity": "CRITICAL", "VulnerabilityID": c} for c in criticals]
    vulns += [{"Severity": "HIGH", "VulnerabilityID": h} for h in highs]
    (Path(tmp) / f"{name}.json").write_text(
        json.dumps({"ArtifactName": image, "Results": [{"Vulnerabilities": vulns}]})
    )


class Repository(unittest.TestCase):
    """The key is the repository, so a pin bump surfaces what is new."""

    def test_tag_is_stripped(self):
        self.assertEqual(gate.repository("postgres:17.1"), "postgres")

    def test_digest_is_stripped(self):
        self.assertEqual(gate.repository("u/s:2.5.x@sha256:abc"), "u/s")

    def test_registry_port_is_not_a_tag(self):
        self.assertEqual(gate.repository("registry:5000/app:2.1"), "registry:5000/app")
        self.assertEqual(gate.repository("registry:5000/app"), "registry:5000/app")


class Findings(unittest.TestCase):
    def test_only_critical_is_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _report(tmp, "a", "postgres:17", criticals=["CVE-1"], highs=["CVE-H"])
            found, broken = gate.findings(Path(tmp))
            self.assertEqual(found, {"postgres": {"CVE-1"}})
            self.assertEqual(broken, [])

    def test_two_tags_of_one_repository_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            _report(tmp, "a", "postgres:17.1", criticals=["CVE-1"])
            _report(tmp, "b", "postgres:17.2", criticals=["CVE-2"])
            found, _ = gate.findings(Path(tmp))
            self.assertEqual(found, {"postgres": {"CVE-1", "CVE-2"}})

    def test_an_unreadable_report_is_named_not_skipped(self):
        """"Could not be read" must never reach the gate as "found nothing"."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.json").write_text("{not json")
            found, broken = gate.findings(Path(tmp))
            self.assertEqual(found, {})
            self.assertEqual(broken, ["broken.json"])

    def test_a_report_without_an_image_name_is_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.json").write_text(json.dumps({"Results": []}))
            _, broken = gate.findings(Path(tmp))
            self.assertEqual(broken, ["x.json"])


class Baseline(unittest.TestCase):
    def test_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "b.json"
            p.write_text(gate.render_baseline(
                {"postgres": {"CVE-2", "CVE-1"}}, "2026-09-21", {"reg/x": "needs auth"}))
            accepted, unscanned = gate.load_baseline(p)
            self.assertEqual(accepted, {"postgres": {"CVE-1", "CVE-2"}})
            self.assertEqual(unscanned, {"reg/x": "needs auth"})

    def test_cves_are_sorted_so_a_rewrite_does_not_churn_the_diff(self):
        out = gate.render_baseline({"postgres": {"CVE-9", "CVE-1"}}, "2026-09-21")
        self.assertLess(out.index("CVE-1"), out.index("CVE-9"))

    def test_an_image_with_no_criticals_is_not_recorded(self):
        out = json.loads(gate.render_baseline({"postgres": set()}, "2026-09-21"))
        self.assertEqual(out["accepted"], {})

    def test_a_missing_baseline_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gate.load_baseline(Path(tmp) / "absent.json"), ({}, {}))


class Reach(unittest.TestCase):
    """Coverage can only shrink deliberately.

    An unscanned image contributes no findings, so it can never fail the CVE
    half of the gate. Left at a summary line it would quietly reduce what the
    gate covers — so an unscanned image that nobody acknowledged fails instead.
    """

    def _run(self, tmp, unscanned_reason=None, failures="", images_total=None):
        import subprocess
        res = Path(tmp) / "res"; res.mkdir(exist_ok=True)
        _report(res, "a", "postgres:17", criticals=["CVE-1"])
        base = Path(tmp) / "b.json"
        base.write_text(gate.render_baseline(
            {"postgres": {"CVE-1"}}, "2026-09-21",
            {"registry.example.com/app": unscanned_reason} if unscanned_reason else {}))
        fails = Path(tmp) / "f.tsv"
        fails.write_text(failures)
        cmd = ["python3", str(Path(__file__).with_name("trivy-gate.py")),
               "--results-dir", str(res), "--baseline", str(base),
               "--failures-file", str(fails)]
        if images_total is not None:
            cmd += ["--images-total", str(images_total)]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_an_unacknowledged_unscanned_image_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(tmp, failures="registry.example.com/app:1\tunauthorized\n")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("not acknowledged", r.stdout)

    def test_an_acknowledged_one_passes_and_is_still_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(tmp, unscanned_reason="registry requires authentication",
                          failures="registry.example.com/app:1\tunauthorized\n")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("registry.example.com/app:1", r.stdout)
            self.assertIn("acknowledged", r.stdout)

    def test_an_image_in_neither_list_fails(self):
        """Discovery, reports and failures must add up, or coverage is unknown."""
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(tmp, images_total=5)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("neither", r.stdout)

    def test_the_arithmetic_is_skipped_when_no_total_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(tmp)
            self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
