#!/usr/bin/env python3
"""Tests for check-baseline.py — the capability and device rules.

The rest of the checker predates these tests. They cover the two rules that had
no coverage at all until 2026-09-24: a container could take SYS_RAWIO and a raw
block device and pass every gate silently.
"""

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_baseline", Path(__file__).parent / "check-baseline.py"
)
baseline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(baseline)

# Any stack path with no entry in the exception tables.
UNLISTED = Path("apps/whoami/docker-compose.yml")


def findings(service: dict, path: Path = UNLISTED, name: str = "probe") -> list[dict]:
    """Run the checker against one synthetic service."""
    svc = {"security_opt": ["no-new-privileges:true"], **service}
    return baseline.check_compose(path, doc={"services": {name: svc}})


def levels(service: dict, **kw) -> dict[str, list[str]]:
    """Map level → list of rule strings, for the levels that matter."""
    out: dict[str, list[str]] = {}
    for f in findings(service, **kw):
        if f["level"] in ("FAIL", "WARN", "SKIP"):
            out.setdefault(f["level"], []).append(f["rule"])
    return out


class CapAddAll(unittest.TestCase):
    """cap_add: ALL is forbidden outright — it undoes cap_drop: ALL."""

    def test_fails(self):
        self.assertIn("cap_add: ALL", levels({"cap_add": ["ALL"]}).get("FAIL", []))

    def test_case_insensitive(self):
        self.assertIn("cap_add: ALL", levels({"cap_add": ["all"]}).get("FAIL", []))

    def test_has_no_exception_path(self):
        """Even a stack that is listed for another capability cannot take ALL."""
        got = levels(
            {"cap_add": ["ALL"]},
            path=Path("monitoring/scrutiny/collector.yml"),
            name="scrutiny-collector",
        )
        self.assertIn("cap_add: ALL", got.get("FAIL", []))


class CapBaseline(unittest.TestCase):
    """The six routine capabilities pass; anything else has to be written down."""

    def test_baseline_set_is_silent(self):
        got = levels({"cap_add": sorted(baseline.CAP_BASELINE)})
        self.assertEqual(got.get("WARN", []), [])
        self.assertEqual(got.get("FAIL", []), [])

    def test_unlisted_capability_warns(self):
        got = levels({"cap_add": ["SYS_ADMIN"]})
        self.assertEqual(got.get("WARN", []), ["cap_add: SYS_ADMIN"])

    def test_several_unlisted_capabilities_warn_once(self):
        got = levels({"cap_add": ["NET_ADMIN", "SYS_PTRACE"]})
        self.assertEqual(got.get("WARN", []), ["cap_add: NET_ADMIN, SYS_PTRACE"])

    def test_baseline_capability_does_not_mask_an_unlisted_one(self):
        got = levels({"cap_add": ["CHOWN", "SYS_RAWIO"]})
        self.assertEqual(got.get("WARN", []), ["cap_add: SYS_RAWIO"])

    def test_documented_exception_skips(self):
        got = levels(
            {"cap_add": ["SYS_RAWIO"]},
            path=Path("monitoring/scrutiny/collector.yml"),
            name="scrutiny-collector",
        )
        self.assertEqual(got.get("WARN", []), [])
        self.assertEqual(len(got.get("SKIP", [])), 1)


class Devices(unittest.TestCase):
    """A host device in a container is a decision, not a detail."""

    def test_undocumented_device_warns(self):
        got = levels({"devices": ["/dev/sda:/dev/sda"]})
        self.assertEqual(got.get("WARN", []), ["devices: /dev/sda:/dev/sda"])

    def test_read_only_mapping_still_warns_when_undocumented(self):
        """Read-only narrows the risk; it does not remove the need to say why."""
        got = levels({"devices": ["/dev/kmsg:/dev/kmsg:r"]})
        self.assertEqual(got.get("WARN", []), ["devices: /dev/kmsg:/dev/kmsg:r"])

    def test_no_devices_is_silent(self):
        self.assertEqual(levels({}).get("WARN", []), [])

    def test_documented_exception_skips(self):
        got = levels(
            {"devices": ["/dev/kmsg:/dev/kmsg:r"]},
            path=Path("monitoring/grafana-prometheus/cadvisor.yml"),
            name="cadvisor",
        )
        self.assertEqual(got.get("WARN", []), [])
        self.assertEqual(len(got.get("SKIP", [])), 1)


class ExceptionTables(unittest.TestCase):
    """Every entry carries the three fields, so no finding is suppressed silently."""

    def test_all_entries_are_complete(self):
        for table_name in ("CAP_ADD_EXCEPTIONS", "DEVICE_EXCEPTIONS"):
            table = getattr(baseline, table_name)
            for stack, services in table.items():
                for service, exc in services.items():
                    for field in ("reason", "alternatives", "risk"):
                        with self.subTest(table=table_name, stack=stack, service=service, field=field):
                            self.assertTrue(
                                exc.get(field, "").strip(),
                                f"{table_name}[{stack}][{service}] has an empty {field}",
                            )


if __name__ == "__main__":
    unittest.main()
