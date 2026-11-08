"""Tests for the stack status report.

The report is information, so what matters is that it never claims more than it
knows: a tag it cannot compare is "not determinable", never "current", and a
date-style tag never passes as a newer release. No test touches the network.
"""

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "upstream_status", Path(__file__).with_name("upstream-status.py")
)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class SplitRef(unittest.TestCase):
    def test_official_image_gets_library(self):
        self.assertEqual(status.split_ref("postgres:17.6"), ("docker.io", "library/postgres", "17.6"))

    def test_hub_namespace(self):
        self.assertEqual(status.split_ref("vaultwarden/server:1.37.5"),
                         ("docker.io", "vaultwarden/server", "1.37.5"))

    def test_other_registry(self):
        self.assertEqual(status.split_ref("ghcr.io/immich-app/immich-server:v3.3.6"),
                         ("ghcr.io", "immich-app/immich-server", "v3.3.6"))

    def test_digest_is_dropped(self):
        self.assertEqual(status.split_ref("ghcr.io/a/b:14-x@sha256:abc")[2], "14-x")

    def test_registry_port_is_not_a_tag(self):
        self.assertEqual(status.split_ref("registry:5000/app"), ("registry:5000", "app", ""))


class Shape(unittest.TestCase):
    def test_suffix_must_match(self):
        tags = ["4.1.2-apache", "4.2.0-apache", "4.3.0-fpm", "5.0.0"]
        self.assertEqual(status.newest("4.1.2-apache", tags), "4.2.0-apache")

    def test_prefix_must_match(self):
        self.assertEqual(status.newest("v3.3.6", ["v3.3.6", "v3.4.0", "3.9.9"]), "v3.4.0")

    def test_prerelease_is_not_newer(self):
        self.assertEqual(status.newest("1.37.5", ["1.37.5", "1.38.0-rc1", "1.38.0-beta"]), "1.37.5")

    def test_numbers_compare_as_numbers(self):
        self.assertEqual(status.newest("1.9.0", ["1.9.0", "1.10.0"]), "1.10.0")

    def test_a_date_tag_is_not_newer(self):
        self.assertEqual(status.newest("2.8.4", ["2.8.4", "2021.11.28"]), "2.8.4")
        self.assertEqual(status.newest("261029", ["261029", "20220121"]), "261029")

    def test_a_commit_hash_suffix_matches_any_hash(self):
        tags = ["2024.10.22-7ca5933", "2025.01.10-a1b2c3d"]
        self.assertEqual(status.newest("2024.10.22-7ca5933", tags), "2025.01.10-a1b2c3d")

    def test_a_numeric_revision_counts(self):
        self.assertEqual(status.newest("7.2.2-0038", ["7.2.2-0038", "7.2.2-0045"]), "7.2.2-0045")

    def test_a_word_prefix_with_a_hyphen(self):
        self.assertEqual(status.newest("alpine-7.0.32", ["alpine-7.0.32", "alpine-8.0.0", "ubuntu-8.0.0"]),
                         "alpine-8.0.0")

    def test_a_long_letter_run_does_not_backtrack(self):
        """CodeQL py/redos: a prefix of many letters must fail fast, not exponentially."""
        self.assertIsNone(status.shape("A" * 5000 + "!"))
        self.assertIsNone(status.shape("a-" * 3000 + "x"))

    def test_no_version_is_not_comparable(self):
        self.assertIsNone(status.newest("latest", ["latest", "1.0.0"]))
        self.assertIsNone(status.newest("main", ["main"]))

    def test_digits_in_the_suffix_are_not_comparable(self):
        self.assertIsNone(status.newest("7.1.4-php8.3-apache", ["7.1.5-php8.3-apache"]))
        self.assertIsNone(status.newest("14-vectorchord1.1.1", ["15-vectorchord1.1.1"]))


class Resolve(unittest.TestCase):
    def test_env_and_inline_default_as_the_scan_resolves_them(self):
        env = {"APP_TAG": "1.2.3", "OTHER": "9"}
        self.assertEqual(status.resolve("vendor/app:${APP_TAG}", env), "vendor/app:1.2.3")
        # list-images.sh takes the inline default even when the variable is set.
        self.assertEqual(status.resolve("vendor/app:${OTHER:-1.0}", env), "vendor/app:1.0")

    def test_unresolved_and_local_images_are_skipped(self):
        self.assertIsNone(status.resolve("vendor/app:${MISSING}", {}))
        self.assertIsNone(status.resolve("app-local:dev", {}))

    def test_primary_image_follows_the_pin_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp) / "apps" / "demo"
            stack.mkdir(parents=True)
            (stack / ".env.example").write_text("DB_TAG=17.6\nAPP_TAG=2.0.1\n")
            (stack / "docker-compose.yml").write_text(
                "services:\n"
                "  db:\n    image: postgres:${DB_TAG}\n"
                "  app:\n    image: vendor/app:${APP_TAG}\n")
            (stack / "docker-compose.local.yml").write_text(
                "services:\n  extra:\n    image: vendor/only-local:1.0\n")
            images = status.stack_images(stack)
            self.assertEqual([i for _, i in images], ["postgres:17.6", "vendor/app:2.0.1"])
            self.assertEqual(status.primary_image(stack, images), "vendor/app:2.0.1")


def _report(tmp, name, image, criticals=(), highs=()):
    vulns = [{"Severity": "CRITICAL", "VulnerabilityID": c} for c in criticals]
    vulns += [{"Severity": "HIGH", "VulnerabilityID": h} for h in highs]
    (Path(tmp) / f"{name}.json").write_text(
        json.dumps({"ArtifactName": image, "Results": [{"Vulnerabilities": vulns}]}))


class Findings(unittest.TestCase):
    def test_counts_every_image_of_the_stack_once_per_cve(self):
        with tempfile.TemporaryDirectory() as tmp:
            _report(tmp, "a", "vendor/app:2", criticals=["CVE-1"], highs=["CVE-H1"])
            _report(tmp, "b", "postgres:17", criticals=["CVE-1", "CVE-2"], highs=["CVE-H2"])
            scan = status.scan_findings(Path(tmp))
            f = status.stack_findings(["vendor/app:2", "postgres:17", "redis:8"], scan)
            self.assertEqual(f["critical"], 2)
            self.assertEqual(f["high"], 2)
            self.assertEqual(f["unscanned"], ["redis:8"])
            self.assertEqual(f["images"]["postgres:17"], {"libraries": [2, 1]})

    def test_findings_are_split_by_where_they_sit(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.json").write_text(json.dumps({
                "ArtifactName": "vendor/app:2", "Results": [
                    {"Class": "os-pkgs", "Type": "debian",
                     "Vulnerabilities": [{"Severity": "HIGH", "VulnerabilityID": "C1"}]},
                    {"Class": "lang-pkgs", "Type": "gobinary",
                     "Vulnerabilities": [{"Severity": "CRITICAL", "VulnerabilityID": "C2"}]},
                    {"Class": "lang-pkgs", "Type": "node-pkg",
                     "Vulnerabilities": [{"Severity": "HIGH", "VulnerabilityID": "C3"}]},
                ]}))
            f = status.stack_findings(["vendor/app:2"], status.scan_findings(Path(tmp)))
            self.assertEqual(f["images"]["vendor/app:2"],
                             {"system": [0, 1], "programs": [1, 0], "libraries": [0, 1]})

    def test_no_reports_means_no_counts_not_zero(self):
        self.assertIsNone(status.stack_findings(["vendor/app:2"], status.scan_findings(None)))


class Render(unittest.TestCase):
    NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)

    def _row(self, **kw):
        row = {"stack": "apps/demo", "image": "vendor/app:1.0.0", "pinned": "1.0.0",
               "pinned_date": self.NOW - timedelta(days=30), "newest": "1.1.0",
               "newest_date": self.NOW - timedelta(days=3), "status": "behind",
               "reason": "", "images": ["vendor/app:1.0.0"],
               "findings": {"critical": 1, "high": 4, "unscanned": []}, "assessed": True}
        row.update(kw)
        return row

    def test_a_newer_version_and_an_assessed_count(self):
        md = status.render_markdown([self._row()], self.NOW, True)
        self.assertIn("newer version upstream", md)
        self.assertIn("README.md#open-findings", md)

    def test_an_old_newest_image_is_named(self):
        old = self.NOW - timedelta(days=800)
        row = self._row(status="current", newest="1.0.0", pinned_date=old, newest_date=old)
        self.assertIn("no release in over 12 months", status.render_markdown([row], self.NOW, True))

    def test_a_recent_github_release_is_not_quiet(self):
        old = self.NOW - timedelta(days=800)
        row = self._row(status="current", newest="1.0.0", pinned_date=old, newest_date=old,
                        last_release=self.NOW - timedelta(days=10))
        self.assertFalse(status.quiet(row, self.NOW))

    def test_an_archived_upstream_is_named(self):
        md = status.render_markdown([self._row(archived=True)], self.NOW, True)
        self.assertIn("upstream repository archived", md)

    def test_undetermined_says_why(self):
        row = self._row(status="undetermined", newest=None, newest_date=None,
                        reason="`main` carries no comparable version")
        md = status.render_markdown([row], self.NOW, True)
        self.assertIn("not determinable: `main` carries no comparable version", md)
        self.assertNotIn("newer version upstream", md)

    def test_json_round_trips(self):
        data = json.loads(status.render_json([self._row()], self.NOW))
        self.assertEqual(data["stacks"]["apps/demo"]["newest"], "1.1.0")
        self.assertEqual(data["stacks"]["apps/demo"]["pinned_date"], "2026-10-09")


class Releases(unittest.TestCase):
    def test_version_numbers_ignore_prefix_and_suffix(self):
        self.assertEqual(status.release_version("v2.4.29"), (2, 4, 29))
        self.assertEqual(status.release_version("35.0.2-fpm-alpine"), (35, 0, 2))

    def test_the_release_matching_the_image_tag(self):
        when = datetime(2026, 11, 1, tzinfo=timezone.utc)
        releases = [("v1.38.0", datetime(2026, 11, 7, tzinfo=timezone.utc), False),
                    ("v1.37.5", when, False)]
        self.assertEqual(status.release_date(releases, "1.37.5"), when)
        self.assertIsNone(status.release_date(releases, "1.36.0"))

    def test_the_first_github_repository_of_the_source_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp)
            (stack / "UPSTREAM.md").write_text(
                "# U\n\n## Source\n\n- **Image:** https://hub.docker.com/_/traefik\n"
                "- **GitHub:** https://github.com/traefik/traefik\n"
                "- **Plugin:** https://github.com/other/plugin\n\n## Changes\n"
                "https://github.com/not/this\n")
            self.assertEqual(status.github_repo(stack), "traefik/traefik")

    def test_a_releases_line_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp)
            (stack / "UPSTREAM.md").write_text(
                "# U\n\n## Source\n\n- **Repo:** https://github.com/portainer/agent\n"
                "- **Releases:** https://github.com/portainer/portainer/releases\n\n")
            self.assertEqual(status.github_repo(stack), "portainer/portainer")


if __name__ == "__main__":
    unittest.main()
