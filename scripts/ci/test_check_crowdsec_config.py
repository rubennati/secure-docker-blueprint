#!/usr/bin/env python3
"""Cover for the CrowdSec default-off gate and the conditional key requirement.

The gate renders `core/traefik` with the shipped `.env.example`, then with the
switch on, then off again, and parses each result. A commented-out block and an
absent block are the same to the parser, and since the switch the templates
carry the plugin and the middlewares as live YAML — so what is judged is what
`render.sh` produces, not what a template contains.

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
import shutil
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
        """Output goes to operator terminals and CI logs; the key stays out of it.

        The marker below is a fixed, meaningless string, not a credential and not
        shaped like one. What is under test is whether the checker copies a key
        value into its output, and any distinguishable string proves that — so
        there is no reason to write something credential-looking to disk.
        """
        sentinel = "NON-SENSITIVE-TEST-SENTINEL"
        self._write(active("crowdsec-appsec", sentinel))
        _, passing = run(cc.check_rendered, self.config)
        self._write(active("crowdsec-appsec", "").replace(
            'crowdsecLapiKey: ""', f'crowdsecLapiKey: ""  # was {sentinel}'))
        _, failing = run(cc.check_rendered, self.config)
        self.assertNotIn(sentinel, passing)
        self.assertNotIn(sentinel, failing)

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
    """The gate renders `core/traefik` in both switch states and judges the result.

    Each case starts from a copy of the real `ops/` and `.env.example` and breaks
    one thing, so the failure the gate reports is the one the case introduced.
    """

    REPO = HERE.parent.parent

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        src = self.REPO / cc.TRAEFIK
        if not (src / "ops").exists():
            self.skipTest("core/traefik not present")
        shutil.copytree(src / "ops", self.root / cc.TRAEFIK / "ops")
        shutil.copy(src / ".env.example", self.root / cc.TRAEFIK / ".env.example")

    def tearDown(self):
        self._tmp.cleanup()

    def _env_example(self) -> Path:
        return self.root / cc.TRAEFIK / ".env.example"

    def _template(self, rel: str) -> Path:
        return self.root / cc.TRAEFIK / "ops" / "templates" / rel

    def test_shipped_shape_passes(self):
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("default-off", out)

    def test_switch_on_in_env_example_fails(self):
        """Shipping the example with the switch on would enable it for everyone."""
        text = self._env_example().read_text()
        text = text.replace("CROWDSEC_BOUNCER_ENABLED=false", "CROWDSEC_BOUNCER_ENABLED=true")
        text = text.replace("CROWDSEC_BOUNCER_KEY=\n", "CROWDSEC_BOUNCER_KEY=example-key\n")
        self._env_example().write_text(text)
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("ships default-off", out)

    def test_plugin_region_removed_fails(self):
        """A template without the marker region cannot render the plugin when asked."""
        t = self._template("traefik.yml.tmpl")
        lines = t.read_text().splitlines(keepends=True)
        start = next(i for i, l in enumerate(lines) if l.startswith("# >>> crowdsec-bouncer"))
        end = next(i for i, l in enumerate(lines) if l.startswith("# <<< crowdsec-bouncer"))
        t.write_text("".join(lines[:start] + lines[end + 1:]))
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("expected ['bouncer']", out)

    def test_middleware_left_in_integrations_fails(self):
        """The dropped-stash shape: an active crowdsec-basic in integrations.yml.tmpl."""
        t = self._template("dynamic/integrations.yml.tmpl")
        t.write_text(t.read_text() + "\n" + active("crowdsec-basic", "${CROWDSEC_BOUNCER_KEY}"))
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("nothing may be enabled by default", out)

    def test_crowdsec_template_removed_fails(self):
        """Without crowdsec.yml.tmpl the switch renders a plugin with nothing to use it."""
        self._template("dynamic/crowdsec.yml.tmpl").unlink()
        code, out = run(cc.check_templates, self.root)
        self.assertEqual(code, 1)
        self.assertIn("renders middlewares []", out)


class RealRepositoryState(unittest.TestCase):
    def test_committed_blueprint_is_default_off_and_switchable(self):
        """Guards the actual shipped files, not a fixture."""
        root = HERE.parent.parent
        if not (root / cc.TRAEFIK / "ops").exists():
            self.skipTest("templates not present")
        code, out = run(cc.check_templates, root)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
