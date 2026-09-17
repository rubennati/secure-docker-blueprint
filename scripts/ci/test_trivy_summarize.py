#!/usr/bin/env python3
"""Regression cover for trivy-summarize.py.

Uses small hand-built Trivy report fixtures rather than real scan output —
real reports are hundreds of KB and the aggregation logic only cares about
ArtifactName and each Vulnerability's Severity/VulnerabilityID/PkgName.

Run:
    python3 scripts/ci/test_trivy_summarize.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "trivy-summarize.py"

spec = importlib.util.spec_from_file_location("trivy_summarize", SCRIPT)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)


def _report(image: str, vulns: list[tuple[str, str, str]]) -> dict:
    """vulns: list of (VulnerabilityID, PkgName, Severity)."""
    return {
        "ArtifactName": image,
        "Results": [{
            "Target": image,
            "Vulnerabilities": [
                {"VulnerabilityID": vid, "PkgName": pkg, "Severity": sev}
                for vid, pkg, sev in vulns
            ],
        }],
    }


def _write(root: Path, name: str, report: dict) -> None:
    (root / f"{name}.json").write_text(json.dumps(report))


class LoadReports(unittest.TestCase):
    def test_counts_only_critical_and_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "a", _report("img:a", [
                ("CVE-1", "pkg1", "CRITICAL"),
                ("CVE-2", "pkg2", "MEDIUM"),   # not counted
                ("CVE-3", "pkg3", "LOW"),      # not counted
            ]))
            reports = ts.load_reports(root)
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["critical"], 1)
            self.assertEqual(reports[0]["high"], 0)

    def test_reads_artifact_name_not_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "some_mangled_filename__1", _report("ghcr.io/x/y:1.0", []))
            reports = ts.load_reports(root)
            self.assertEqual(reports[0]["image"], "ghcr.io/x/y:1.0")

    def test_skips_invalid_json_with_warning_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.json").write_text("{not json")
            reports = ts.load_reports(root)
            self.assertEqual(reports, [])


class LoadFailures(unittest.TestCase):
    def test_missing_file_is_empty_not_an_error(self):
        self.assertEqual(ts.load_failures(Path("/nonexistent/failures.tsv")), [])

    def test_parses_image_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "failures.tsv"
            f.write_text("docker.n8n.io/n8nio/n8n:2.38.7\tTOOMANYREQUESTS\n")
            failures = ts.load_failures(f)
            self.assertEqual(failures, [("docker.n8n.io/n8nio/n8n:2.38.7", "TOOMANYREQUESTS")])

    def test_missing_reason_gets_placeholder_not_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "failures.tsv"
            f.write_text("some/image:tag\n")
            failures = ts.load_failures(f)
            self.assertEqual(failures[0][0], "some/image:tag")
            self.assertTrue(failures[0][1])  # placeholder, not empty


class Render(unittest.TestCase):
    def test_unscanned_image_is_named_not_folded_into_clean(self):
        reports = [{"image": "img:a", "critical": 0, "high": 0, "cves": set()}]
        failures = [("img:b", "some registry error")]
        out = ts.render(reports, failures, images_total=2, top=5)
        self.assertIn("img:b", out)
        self.assertIn("some registry error", out)
        self.assertIn("Images not scanned | 1", out)

    def test_mismatch_between_discovery_and_accounting_is_flagged(self):
        reports = [{"image": "img:a", "critical": 0, "high": 0, "cves": set()}]
        out = ts.render(reports, failures=[], images_total=5, top=5)
        self.assertIn("accounted for in neither list", out)

    def test_no_mismatch_when_counts_agree(self):
        reports = [{"image": "img:a", "critical": 0, "high": 0, "cves": set()}]
        out = ts.render(reports, failures=[], images_total=1, top=5)
        self.assertNotIn("accounted for in neither list", out)

    def test_repeated_cve_across_images_is_surfaced(self):
        reports = [
            {"image": "img:a", "critical": 1, "high": 0, "cves": {("CVE-9", "libx")}},
            {"image": "img:b", "critical": 1, "high": 0, "cves": {("CVE-9", "libx")}},
            {"image": "img:c", "critical": 0, "high": 1, "cves": {("CVE-1", "liby")}},
        ]
        out = ts.render(reports, failures=[], images_total=3, top=5)
        self.assertIn("CVE-9", out)
        self.assertIn("repeated across the most images", out)
        # CVE-1 appears in only one image and must not be listed as repeated.
        self.assertNotIn("CVE-1", out)

    def test_top_offenders_ranked_by_critical_then_high(self):
        reports = [
            {"image": "low", "critical": 1, "high": 99, "cves": set()},
            {"image": "high", "critical": 5, "high": 1, "cves": set()},
        ]
        out = ts.render(reports, failures=[], images_total=2, top=5)
        self.assertLess(out.index("`high`"), out.index("`low`"))

    def test_zero_critical_images_get_no_top_offenders_section(self):
        reports = [{"image": "img:a", "critical": 0, "high": 3, "cves": set()}]
        out = ts.render(reports, failures=[], images_total=1, top=5)
        self.assertNotIn("Top", out)

    def test_exit_code_independence_is_stated(self):
        out = ts.render([], failures=[], images_total=0, top=5)
        self.assertIn("does not depend on any count above", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
