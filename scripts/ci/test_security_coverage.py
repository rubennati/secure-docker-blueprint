"""Tests for the security-coverage generator's predicates and rendering."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "security_coverage", Path(__file__).with_name("security-coverage.py")
)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class NoNewPrivileges(unittest.TestCase):
    def test_reads_the_flag(self):
        self.assertTrue(sc._has_nnp({"security_opt": ["no-new-privileges:true"]}))

    def test_absent_security_opt_is_false(self):
        self.assertFalse(sc._has_nnp({}))

    def test_other_options_do_not_count(self):
        self.assertFalse(sc._has_nnp({"security_opt": ["seccomp:unconfined"]}))


class CapDrop(unittest.TestCase):
    def test_all_counts(self):
        self.assertTrue(sc._drops_all({"cap_drop": ["ALL"]}))

    def test_case_insensitive(self):
        self.assertTrue(sc._drops_all({"cap_drop": ["all"]}))

    def test_a_named_capability_is_not_all(self):
        self.assertFalse(sc._drops_all({"cap_drop": ["NET_RAW"]}))

    def test_absent_is_false(self):
        self.assertFalse(sc._drops_all({}))


class ResourceLimits(unittest.TestCase):
    def test_needs_both_memory_and_pids(self):
        both = {"deploy": {"resources": {"limits": {"memory": "1G", "pids": 100}}}}
        self.assertTrue(sc._has_limits(both))

    def test_memory_alone_is_not_enough(self):
        only_mem = {"deploy": {"resources": {"limits": {"memory": "1G"}}}}
        self.assertFalse(sc._has_limits(only_mem))

    def test_absent_deploy_is_false(self):
        self.assertFalse(sc._has_limits({}))


class Exceptions(unittest.TestCase):
    def test_counts_services_not_files(self):
        table = {"a/b": {"one": {}, "two": {}}, "c/d": {"three": {}}}
        self.assertEqual(sc._exception_count(table), 3)

    def test_empty_table_is_zero(self):
        self.assertEqual(sc._exception_count({}), 0)


class Render(unittest.TestCase):
    """The rendered document must carry the marker and state both scopes.

    A generated file without its marker reads as hand-written and invites the
    edit this generator exists to prevent.
    """

    facts = {
        "scope": {
            "deployable": {"stacks": 3, "files": 4, "services": 9},
            "universe": {"stacks": 4, "files": 5, "services": 11},
        },
        "excepted": ["apps/_reference"],
        "total": 9,
        "files": 4,
        "hard": {"no-new-privileges": 8, "privileged": 0},
        "waived": {"no-new-privileges": 1, "socket": 2, "host-mode": 0},
        "structure": {"internal-network": 2, "sentinels": 7},
        "soft": {"read_only": 3, "cap_drop_all": 5, "user": 1, "limits": 9, "secrets": 4},
    }

    def test_carries_the_generated_marker(self):
        self.assertIn(sc.MARKER, sc.render(self.facts))

    def test_states_both_scopes(self):
        out = sc.render(self.facts)
        self.assertIn("| **Deployable** | 3 | **4** | **9** |", out)
        self.assertIn("| Checker universe | 4 | 5 | 11 |", out)

    def test_every_service_figure_uses_the_deployable_denominator(self):
        out = sc.render(self.facts)
        self.assertIn("8 / 9 services", out)
        self.assertIn("3 / 9 services", out)
        self.assertNotIn("/ 11 services", out)

    def test_names_the_excepted_directories(self):
        self.assertIn("`apps/_reference`", sc.render(self.facts))

    def test_is_deterministic(self):
        self.assertEqual(sc.render(self.facts), sc.render(self.facts))


if __name__ == "__main__":
    unittest.main()
