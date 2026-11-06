#!/usr/bin/env python3
"""Seafile CE and Pro turn the OnlyOffice integration on only when it is configured.

Always on, Seahub opened every office file in an editor that loads api.js from
ONLYOFFICE_HOST, even where no Document Server answers (step 8 lab host). Each
stack's config/seahub_custom.py is executed here with the environment its
entrypoint or compose file would hand it.

Run:
    python3 scripts/ci/test_seafile_onlyoffice_switch.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STACKS = ("apps/seafile", "apps/seafile-pro")

CASES = [
    ("no secret", "", "https://office.example.com", False),
    ("whitespace", "  \n", "https://office.example.com", False),
    ("placeholder", "__REPLACE_ME__", "https://office.example.com", False),
    ("no host", "s3cret", "https://", False),
    ("configured", "s3cret", "https://office.example.com", True),
]


def enabled(stack, secret, url):
    env = {"ONLYOFFICE_JWT_SECRET": secret, "ONLYOFFICE_URL": url, "SEAFILE_SMTP_HOST": ""}
    scope = {}
    with unittest.mock.patch.dict(os.environ, env):
        exec((REPO / stack / "config" / "seahub_custom.py").read_text(encoding="utf-8"), scope)
    return scope["ENABLE_ONLYOFFICE"]


class OnlyOfficeSwitch(unittest.TestCase):
    def test_on_only_when_configured(self):
        for stack in STACKS:
            for name, secret, url, expected in CASES:
                with self.subTest(stack=stack, case=name):
                    self.assertIs(enabled(stack, secret, url), expected)


if __name__ == "__main__":
    unittest.main()
