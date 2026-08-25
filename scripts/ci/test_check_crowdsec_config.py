#!/usr/bin/env python3
"""Cover for the CrowdSec default-off gate and the conditional key requirement.

Two behaviours are worth a test each because both used to be decided by reading
comments, and a comment is not configuration. The parser treats a commented-out
block and an absent block identically — which is the question actually being
asked in both cases.

The key requirement is conditional on purpose: the shipped blueprint has no
CrowdSec middleware and must validate without a bouncer key, while an operator
who enables one must not get a silently empty key from `envsubst`.

Run:
    python3 scripts/ci/test_check_crowdsec_config.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import io
import contextlib
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "check_crowdsec_config", HERE / "check-crowdsec-config.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


# The shipped shape: everything commented out, so the document is empty.
COMMENTED = """\
# http:
#   middlewares:
#     crowdsec-basic:
#       plugin:
#         bouncer:
#           enabled: true
#           crowdsecLapiKey: "${CROWDSEC_BOUNCER_KEY}"
"""


def active(name: str, key: str) -> str:
    return f"""\
http:
  middlewares:
    {name}:
      plugin:
        bouncer:
          enabled: true
          crowdsecMode: stream
          crowdsecLapiHost: crowdsec:8080
          crowdsecLapiKey: "{key}"
"""


def run(fn, *args) -> tuple:
    """Return (exit code, captured output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, buf.getvalue()


class ConditionalKeyRequirement(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = Path(self._tmp.name) / "config"
        (self.config / "dynamic").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, content: str):
        (self.config / "dynamic" / "integrations.yml").write_text(content)

    def test_default_commented_templates_without_key_pass(self):
        """The shipped default must validate on a host that has no bouncer key."""
        self._write(COMMENTED)
        code, out = run(cc.check_rendered, self.config)
        self.assertEqual(code, 0)
        self.assertNotIn("ERROR", out)

    def test_active_basic_with_empty_key_fails(self):
        self._write(active("crowdsec-basic", ""))
        code, out = run(cc.check_rendered, self.config)
        self.assertEqual(code, 1)
        self.assertIn("crowdsec-basic", out)
        self.assertIn("CROWDSEC_BOUNCER_KEY", out)

    def test_active_appsec_with_empty_key_fails(self):
        """AppSec is a separate middleware and must be caught independently."""
        self._write(active("crowdsec-appsec", ""))
        code, out = run(cc.check_rendered, self.config)
        self.assertEqual(code, 1)
        self.assertIn("crowdsec-appsec", out)

    def test_active_middleware_with_key_passes(self):
        self._write(active("crowdsec-basic", "s3cret-bouncer-key"))
        code, out = run(cc.check_rendered, self.config)
        self.assertEqual(code, 0)

    def test_key_value_is_never_printed(self):
        """Output goes to operator terminals and CI logs; the key stays out of it."""
        secret = "REAL-KEY-DO-NOT-LEAK"
        self._write(active("crowdsec-appsec", secret))
        _, passing = run(cc.check_rendered, self.config)
        self._write(active("crowdsec-appsec", "").replace(
            'crowdsecLapiKey: ""', f'crowdsecLapiKey: ""  # was {secret}'))
        _, failing = run(cc.check_rendered, self.config)
        self.assertNotIn(secret, passing)
        self.assertNotIn(secret, failing)

    def test_whitespace_only_key_counts_as_empty(self):
        self._write(active("crowdsec-basic", "   "))
        self.assertEqual(run(cc.check_rendered, self.config)[0], 1)

    def test_missing_rendered_config_is_not_a_failure(self):
        """validate.sh runs before a first render too."""
        empty = Path(self._tmp.name) / "never-rendered"
        self.assertEqual(run(cc.check_rendered, empty)[0], 0)

    def test_non_crowdsec_middleware_needs_no_key(self):
        self._write("http:\n  middlewares:\n    compress:\n      compress: {}\n")
        self.assertEqual(run(cc.check_rendered, self.config)[0], 0)


class DefaultOffGate(unittest.TestCase):
    """The property the dropped CrowdSec stash would have violated."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / cc.STATIC_TEMPLATE).parent.mkdir(parents=True)
        (self.root / cc.DYNAMIC_TEMPLATE).parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _templates(self, static: str, dynamic: str):
        (self.root / cc.STATIC_TEMPLATE).write_text(static)
        (self.root / cc.DYNAMIC_TEMPLATE).write_text(dynamic)

    def test_commented_templates_pass(self):
        self._templates("providersThrottleDuration: 30s\n"
                        "# experimental:\n#   plugins:\n#     bouncer:\n", COMMENTED)
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 0)
        self.assertIn("default-off", out)

    def test_uncommented_plugin_declaration_fails(self):
        self._templates(
            "experimental:\n  plugins:\n    bouncer:\n"
            '      moduleName: "github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin"\n'
            '      version: "v1.7.1"\n', COMMENTED)
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("bouncer", out)

    def test_uncommented_middleware_fails(self):
        self._templates("providersThrottleDuration: 30s\n",
                        active("crowdsec-basic", "${CROWDSEC_BOUNCER_KEY}"))
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("crowdsec-basic", out)

    def test_the_dropped_stash_shape_fails_both_rules(self):
        """Exactly the enablement that was carried as an uncommitted stash."""
        self._templates(
            "experimental:\n  plugins:\n    bouncer:\n"
            '      moduleName: "github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin"\n'
            '      version: "v1.4.5"\n',
            active("crowdsec-basic", "${CROWDSEC_BOUNCER_KEY}")
            + "    crowdsec-appsec:\n      plugin:\n        bouncer:\n"
              "          crowdsecAppsecEnabled: true\n")
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("crowdsec-basic", out)
        self.assertIn("crowdsec-appsec", out)


class RealRepositoryState(unittest.TestCase):
    def test_committed_templates_are_default_off(self):
        """Guards the actual shipped files, not a fixture."""
        root = HERE.parent.parent
        if not (root / cc.STATIC_TEMPLATE).exists():
            self.skipTest("templates not present")
        self.assertEqual(run(cc.check_templates, root)[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
