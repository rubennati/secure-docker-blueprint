"""Tests for the catalogue generator's parsing helpers."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "site_catalogue", Path(__file__).with_name("site-catalogue.py")
)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class Fields(unittest.TestCase):
    def test_field_reads_value(self):
        self.assertEqual(sc.field("- **Role:** A thing\n", "Role"), "A thing")

    def test_field_missing_is_empty(self):
        self.assertEqual(sc.field("- **Origin:** x\n", "Role"), "")

    def test_upstream_link_stops_at_licence(self):
        text = "- **Image:** https://a.example/img\n- **License:** MIT (https://b.example)\n"
        self.assertEqual(sc.upstream_link(text), "https://a.example/img")

    def test_upstream_link_none_when_first_party(self):
        self.assertIsNone(sc.upstream_link("- **License:** Apache-2.0\n"))


class Version(unittest.TestCase):
    def test_strips_leading_v_before_digit(self):
        self.assertEqual(sc.version({"pinned": "APP_TAG=v1.2.3"}, ""), "1.2.3")

    def test_keeps_v_in_a_word(self):
        self.assertEqual(sc.version({"pinned": "APP_TAG=version-v26.5"}, ""), "version-v26.5")

    def test_drops_image_name(self):
        self.assertEqual(sc.version({"pinned": "IMG=traefik:v3.7"}, ""), "3.7")

    def test_falls_back_to_upstream_field(self):
        self.assertEqual(sc.version({}, "- **Based on version:** `2.0.1`\n"), "2.0.1")


class Domains(unittest.TestCase):
    def test_fourteen_unique(self):
        self.assertEqual(len(sc.DOMAINS), 14)
        self.assertEqual(len(set(sc.DOMAINS)), 14)


if __name__ == "__main__":
    unittest.main()


class Footprint(unittest.TestCase):
    """What a stack brings, derived from its compose files rather than recorded.

    The one thing this must never do is publish a configured memory limit as a
    requirement: the repository sets that ceiling, upstream does not state it.
    """

    @staticmethod
    def _stack(tmp, compose, overlay=None):
        """(production files, overlay files), the two lists footprint() takes."""
        app = Path(tmp)
        main = app / "docker-compose.yml"
        main.write_text(compose)
        overlays = []
        if overlay:
            gpu = app / "docker-compose.gpu.yml"
            gpu.write_text(overlay)
            overlays.append(gpu)
        return [main], overlays

    def test_counts_services_and_names_the_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n"
                                   "  app:\n    image: app:1\n"
                                   "  db:\n    image: mariadb:11.4\n")
            f = sc.footprint(*files)
            self.assertEqual(f["services"], 2)
            self.assertEqual(f["infrastructure"], ["MariaDB"])
            self.assertEqual(f["summary"], "2 services · MariaDB")

    def test_a_single_service_is_not_pluralised(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n  app:\n    image: app:1\n")
            self.assertEqual(sc.footprint(*files)["summary"], "1 service")

    def test_a_one_shot_container_is_counted_apart(self):
        """Counting an init container as running would overstate the stack."""
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, 'services:\n'
                                   '  init:\n    image: app:1\n    restart: "no"\n'
                                   '  app:\n    image: app:1\n')
            f = sc.footprint(*files)
            self.assertEqual((f["services"], f["init_services"]), (1, 1))
            self.assertIn("1 one-shot", f["summary"])

    def test_two_databases_are_both_named_and_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n"
                                   "  app:\n    image: app:1\n"
                                   "  cache:\n    image: redis:7-alpine\n"
                                   "  db:\n    image: postgres:17\n")
            self.assertEqual(sc.footprint(*files)["summary"], "3 services · PostgreSQL + Redis")

    def test_a_reserved_gpu_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n  app:\n    image: app:1\n"
                                   "    deploy:\n      resources:\n        reservations:\n"
                                   "          devices:\n            - capabilities: [gpu]\n")
            self.assertEqual(sc.footprint(*files)["gpu"], "required")

    def test_a_gpu_declared_only_in_an_overlay_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(
                tmp,
                "services:\n  app:\n    image: app:1\n",
                "services:\n  app:\n"
                "    deploy:\n      resources:\n        reservations:\n"
                "          devices:\n            - capabilities: [gpu]\n",
            )
            self.assertEqual(sc.footprint(*files)["gpu"], "optional")

    def test_no_gpu_anywhere_states_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n  app:\n    image: app:1\n")
            f = sc.footprint(*files)
            self.assertIsNone(f["gpu"])
            self.assertNotIn("GPU", f["summary"])

    def test_a_memory_limit_never_reaches_the_footprint(self):
        """The ceiling the repository sets is not a requirement upstream states."""
        with tempfile.TemporaryDirectory() as tmp:
            files = self._stack(tmp, "services:\n  app:\n    image: app:1\n"
                                   "    deploy:\n      resources:\n        limits:\n"
                                   "          memory: 4G\n          pids: 200\n")
            f = sc.footprint(*files)
            self.assertNotIn("memory", f)
            self.assertNotIn("4G", f["summary"])
            self.assertNotIn("4G", repr(f))

    def test_a_host_installed_stack_has_no_footprint(self):
        self.assertIsNone(sc.footprint([], []))


class DecisionFacts(unittest.TestCase):
    """Facts read from upstream's terms, each rejected unless it says where it came from.

    An unsourced claim about someone else's licence is the thing this exists to
    stop, so provenance is a parse requirement rather than a convention.
    """

    def _facts(self, line):
        problems = []
        return sc.decision_facts(line, "apps/demo", problems), problems

    def test_a_sourced_fact_is_accepted(self):
        out, problems = self._facts(
            "- **Edition gating:** SAML is a paid plugin"
            " — https://plugins.example.com/x · checked 2026-09-21\n")
        self.assertEqual(problems, [])
        self.assertEqual(out["edition_gating"]["source"], "https://plugins.example.com/x")
        self.assertEqual(out["edition_gating"]["checked"], "2026-09-21")

    def test_a_fact_without_provenance_is_rejected(self):
        out, problems = self._facts("- **Edition gating:** SAML is a paid plugin\n")
        self.assertEqual(out, {})
        self.assertIn("checked YYYY-MM-DD", problems[0])

    def test_a_source_without_a_date_is_rejected(self):
        out, problems = self._facts(
            "- **Edition gating:** SAML is a paid plugin — https://x.example.com\n")
        self.assertEqual(out, {})
        self.assertEqual(len(problems), 1)

    def test_an_impossible_date_is_rejected(self):
        out, problems = self._facts(
            "- **Edition gating:** x — https://x.example.com · checked 2026-13-45\n")
        self.assertEqual(out, {})
        self.assertIn("no valid date", problems[0])

    def test_an_em_dash_inside_the_statement_survives(self):
        """The separator is anchored at the end, so prose may use em dashes."""
        out, _ = self._facts(
            "- **Edition gating:** SSO — the SAML kind — is paid"
            " — https://x.example.com · checked 2026-09-21\n")
        self.assertEqual(out["edition_gating"]["statement"], "SSO — the SAML kind — is paid")

    def test_a_commercial_model_outside_the_vocabulary_is_rejected(self):
        out, problems = self._facts(
            "- **Commercial model:** costs money — https://x.example.com · checked 2026-09-21\n")
        self.assertEqual(out, {})
        self.assertIn("is not one of", problems[0])

    def test_a_qualifier_after_the_term_is_allowed(self):
        out, problems = self._facts(
            "- **Commercial model:** paid add-on; the core is free"
            " — https://x.example.com · checked 2026-09-21\n")
        self.assertEqual(problems, [])
        self.assertEqual(out["commercial_model"]["model"], "paid add-on")

    def test_an_absent_field_is_not_an_empty_one(self):
        """Absent means not researched, and must never be published as a finding."""
        out, problems = self._facts("- **License:** MIT\n")
        self.assertEqual(out, {})
        self.assertEqual(problems, [])

    def test_a_checked_stack_can_state_that_nothing_is_gated(self):
        out, problems = self._facts(
            "- **Edition gating:** none — https://x.example.com · checked 2026-09-21\n")
        self.assertEqual(problems, [])
        self.assertEqual(out["edition_gating"]["statement"], "none")


class ResearchState(unittest.TestCase):
    """Three states, told apart without padding every file with placeholders.

    The marker is a process record — it says the questions were asked — so it
    carries no source. A `none` *fact* asserts something about upstream's terms
    and does. Conflating the two is what would turn this into bookkeeping.
    """

    def _state(self, line, has_facts=False):
        problems = []
        return sc.decision_facts_checked(line, "apps/demo", has_facts, problems), problems

    def test_a_missing_marker_is_rejected(self):
        """This is what stops a new stack entering with its state unstated."""
        out, problems = self._state("- **License:** MIT\n")
        self.assertIsNone(out)
        self.assertIn("Decision facts checked", problems[0])

    def test_not_yet_means_nobody_has_looked(self):
        out, problems = self._state("- **Decision facts checked:** not yet\n")
        self.assertIsNone(out)
        self.assertEqual(problems, [])

    def test_a_date_means_the_questions_were_asked(self):
        out, problems = self._state("- **Decision facts checked:** 2026-09-21\n")
        self.assertEqual(out, "2026-09-21")
        self.assertEqual(problems, [])

    def test_a_date_with_no_facts_is_legal(self):
        """Checked and nothing found needs no placeholder fields."""
        out, problems = self._state("- **Decision facts checked:** 2026-09-21\n", has_facts=False)
        self.assertEqual(out, "2026-09-21")
        self.assertEqual(problems, [])

    def test_facts_alongside_not_yet_contradict(self):
        out, problems = self._state("- **Decision facts checked:** not yet\n", has_facts=True)
        self.assertIsNone(out)
        self.assertIn("date it instead", problems[0])

    def test_a_marker_that_is_not_a_date_is_rejected(self):
        out, problems = self._state("- **Decision facts checked:** soon\n")
        self.assertIsNone(out)
        self.assertIn("needs YYYY-MM-DD", problems[0])

    def test_an_impossible_date_is_rejected(self):
        out, problems = self._state("- **Decision facts checked:** 2026-02-31\n")
        self.assertIsNone(out)
        self.assertEqual(len(problems), 1)
