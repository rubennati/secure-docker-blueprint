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
