#!/usr/bin/env python3
"""core/dnsmasq: DNS_LOG_QUERIES decides whether the query log is rendered.

With `log-queries`, dnsmasq writes every name a device looks up, and the
address that asked, to the container log. The template carried the line
unconditionally, so `DNS_LOG_QUERIES=false` changed nothing. These tests render
an isolated copy of the stack and read the rendered dnsmasq.conf.

Run:
    python3 scripts/ci/test_dnsmasq_render.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STACK = REPO / "core" / "dnsmasq"


class QueryLogSwitch(unittest.TestCase):

    def _render(self, value):
        """Render with DNS_LOG_QUERIES set to `value`; None removes the line."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(STACK / "ops", tmp / "ops")
        env = (STACK / ".env.example").read_text(encoding="utf-8")
        env = re.sub(r"(?m)^DNS_LOG_QUERIES=.*\n", "" if value is None else f"DNS_LOG_QUERIES={value}\n", env)
        (tmp / ".env").write_text(env, encoding="utf-8")
        r = subprocess.run(["bash", str(tmp / "ops" / "scripts" / "render.sh")], capture_output=True, text=True)
        conf = tmp / "config" / "dnsmasq.conf"
        return r.returncode, r.stdout + r.stderr, conf.read_text(encoding="utf-8") if conf.exists() else ""

    def _log_lines(self, conf):
        return [line for line in conf.splitlines() if line.strip() == "log-queries"]

    def test_the_example_ships_the_log_off(self):
        self.assertIn("DNS_LOG_QUERIES=false", (STACK / ".env.example").read_text(encoding="utf-8").splitlines())

    def test_false_renders_no_query_log(self):
        rc, out, conf = self._render("false")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self._log_lines(conf), [])
        self.assertIn("log-facility=-", conf)

    def test_true_renders_the_query_log_and_says_so(self):
        rc, out, conf = self._render("true")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self._log_lines(conf), ["log-queries"])
        self.assertIn("NOTE: DNS_LOG_QUERIES=true", out)

    def test_empty_or_missing_is_off(self):
        for value in ("", None):
            with self.subTest(value=value):
                rc, out, conf = self._render(value)
                self.assertEqual(rc, 0, out)
                self.assertEqual(self._log_lines(conf), [])

    def test_another_value_is_refused_before_writing(self):
        rc, out, conf = self._render("yes")
        self.assertNotEqual(rc, 0)
        self.assertIn("DNS_LOG_QUERIES must be true or false (got 'yes')", out)
        self.assertEqual(conf, "")


if __name__ == "__main__":
    unittest.main()
