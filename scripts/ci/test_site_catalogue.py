"""Tests for the catalogue generator's parsing helpers."""

import importlib.util
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
