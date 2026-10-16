#!/usr/bin/env python3
"""core/crowdsec/ops/allowlist.sh — the administrative exemption, against a
fake cscli that records every call and keeps the engine's state in a file.

What the contract says and these cases hold:
- an empty CROWDSEC_ALLOWLIST_ADMIN is a decision, not an error: exit 0, no call
- a value that is not an address or range is an error: exit 1, nothing applied
- apply creates the list once, adds what is missing, never removes
- a whole VPN range is accepted and named as such
- IPv4 and IPv6 entries both reach the engine

Run:
    python3 scripts/ci/test_crowdsec_allowlist.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "core" / "crowdsec" / "ops" / "allowlist.sh"

# A cscli that records its arguments and answers like the engine would:
# `allowlists inspect <name>` fails until `create`, then prints the values as
# JSON; `add` appends; everything else just records.
FAKE_CSCLI = """#!/usr/bin/env bash
set -eu
STATE="${FAKE_STATE}"
printf '%s\\n' "$*" >> "${STATE}.log"
case "$1 $2" in
  "allowlists inspect")
    [ -f "${STATE}" ] || { echo "allowlist '$3' not found" >&2; exit 1; }
    printf '{"name":"%s","items":[' "$3"
    first=1
    while IFS= read -r v; do
      [ -n "$v" ] || continue
      [ $first -eq 1 ] || printf ','
      printf '{"value":"%s"}' "$v"; first=0
    done < "${STATE}"
    printf ']}\\n' ;;
  "allowlists create") : > "${STATE}" ;;
  "allowlists add") printf '%s\\n' "$4" >> "${STATE}" ;;
  "allowlists remove") grep -vxF "$4" "${STATE}" > "${STATE}.tmp" || true; mv "${STATE}.tmp" "${STATE}" ;;
  "allowlists check") echo "$3 is allowlisted by '${STATE##*/}'" ;;
  "allowlists list") echo "admin-devices" ;;
esac
"""


class Scratch:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        self.stack = self.root / "core" / "crowdsec"
        (self.stack / "ops").mkdir(parents=True)
        shutil.copy(SCRIPT, self.stack / "ops" / "allowlist.sh")
        self.cscli = self.root / "cscli"
        self.cscli.write_text(FAKE_CSCLI, encoding="utf-8")
        self.cscli.chmod(0o755)
        self.state = self.root / "engine-state"

    def env(self, value=None, with_env=True):
        if with_env:
            body = "COMPOSE_PROJECT_NAME=crowdsec\nCONTAINER_NAME_APP=crowdsec\n"
            if value is not None:
                body += f'CROWDSEC_ALLOWLIST_ADMIN="{value}"\n'
            (self.stack / ".env").write_text(body, encoding="utf-8")

    def run(self, *args):
        env = dict(os.environ, ALLOWLIST_CSCLI=str(self.cscli), FAKE_STATE=str(self.state))
        r = subprocess.run(["bash", str(self.stack / "ops" / "allowlist.sh"), *args],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr

    def calls(self):
        log = Path(str(self.state) + ".log")
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


class AdministrativeExemption(unittest.TestCase):
    def setUp(self):
        self.s = Scratch()
        self.addCleanup(self.s.cleanup)

    def test_empty_variable_is_a_decision_not_an_error(self):
        self.s.env("")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("no exemption is active, by decision", out)
        self.assertEqual(self.s.calls(), [], "the engine was not touched")

    def test_unset_variable_behaves_like_empty(self):
        self.s.env(None)
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.s.calls(), [])

    def test_missing_env_file_is_an_error(self):
        self.s.env(with_env=False)
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 1)
        self.assertIn(".env not found", out)

    def test_invalid_value_applies_nothing(self):
        self.s.env("100.64.0.7, admin-laptop, fd7a:115c:a1e0::1")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 1)
        self.assertIn("admin-laptop", out)
        self.assertIn("Nothing was applied", out)
        self.assertEqual(self.s.calls(), [])

    def test_apply_creates_once_and_adds_both_families(self):
        self.s.env("100.64.0.7, fd7a:115c:a1e0::1")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 0, out)
        calls = self.s.calls()
        self.assertEqual(sum(1 for c in calls if c.startswith("allowlists create ")), 1)
        adds = [c for c in calls if c.startswith("allowlists add ")]
        self.assertEqual(len(adds), 2)
        self.assertTrue(any("100.64.0.7" in c for c in adds))
        self.assertTrue(any("fd7a:115c:a1e0::1" in c for c in adds))
        self.assertIn("2 added, 0 already present", out)
        self.assertFalse(any(c.startswith("allowlists remove") for c in calls))

    def test_second_apply_adds_nothing_and_removes_nothing(self):
        self.s.env("100.64.0.7, fd7a:115c:a1e0::1")
        self.s.run("apply")
        # the operator drops one device from .env — the engine keeps it
        self.s.env("100.64.0.7")
        before = len(self.s.calls())
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 0, out)
        new = self.s.calls()[before:]
        self.assertFalse(any(c.startswith("allowlists add") or c.startswith("allowlists create")
                             or c.startswith("allowlists remove") for c in new), new)
        self.assertIn("0 added, 1 already present", out)
        self.assertIn("fd7a:115c:a1e0::1", self.s.state.read_text(encoding="utf-8"))

    def test_whole_vpn_range_is_applied_and_named(self):
        self.s.env("100.64.0.0/10")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING", out)
        self.assertIn("whole VPN range", out)
        self.assertTrue(any(c == "allowlists add admin-devices 100.64.0.0/10 -d administrative device (ops/allowlist.sh apply)"
                            for c in self.s.calls()), self.s.calls())

    def test_remove_is_explicit_and_single(self):
        self.s.env("100.64.0.7, 100.64.0.8")
        self.s.run("apply")
        rc, out = self.s.run("remove", "100.64.0.8")
        self.assertEqual(rc, 0, out)
        self.assertIn("allowlists remove admin-devices 100.64.0.8", self.s.calls())
        self.assertEqual(self.s.state.read_text(encoding="utf-8").split(), ["100.64.0.7"])

    def test_check_validates_and_asks_the_engine(self):
        self.s.env("100.64.0.7")
        rc, out = self.s.run("check", "not-an-address")
        self.assertEqual(rc, 1)
        rc, out = self.s.run("check", "100.64.0.7")
        self.assertEqual(rc, 0, out)
        self.assertIn("allowlists check 100.64.0.7", self.s.calls())

    def test_address_validation(self):
        self.s.env("256.1.1.1")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 1)
        self.s.env("203.0.113.0/33")
        rc, out = self.s.run("apply")
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
