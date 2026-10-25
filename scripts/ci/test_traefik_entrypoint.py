#!/usr/bin/env python3
"""Rendered entrypoint configuration: timeouts, trusted proxy ranges, and the
variables validate.sh refuses to go without.

Every case renders into an isolated copy of core/traefik/ops, so the live
deployment is never touched, and reads the rendered YAML rather than the
renderer's internals.

Run:
    python3 scripts/ci/test_traefik_entrypoint.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

REPO = Path(__file__).resolve().parents[2]
VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")

spec = importlib.util.spec_from_file_location(
    "check_cloudflare_ips", REPO / "scripts" / "ci" / "check-cloudflare-ips.py"
)
cf_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf_check)


def render(env, mutate=None):
    """Render and validate in a scratch copy; mutate(tmp) runs before the render."""
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(TRAEFIK / "ops", tmp / "ops")
    (tmp / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
    if mutate:
        mutate(tmp)
    r = subprocess.run(["bash", str(tmp / "ops/scripts/render.sh")], capture_output=True, text=True)
    v = subprocess.run(["bash", str(tmp / "ops/scripts/validate.sh")], capture_output=True, text=True)
    static = tmp / "config" / "traefik.yml"
    return {
        "tmp": tmp,
        "render_rc": r.returncode,
        "render_out": r.stdout + r.stderr,
        "validate_rc": v.returncode,
        "validate_out": v.stdout + v.stderr,
        "static": yaml.safe_load(static.read_text(encoding="utf-8")) if static.exists() else None,
    }


class EntrypointTimeouts(unittest.TestCase):
    """The three timeouts come from .env and default to Traefik's own values."""

    def setUp(self):
        self.addCleanup(lambda: None)

    def _cleanup(self, r):
        shutil.rmtree(r["tmp"], ignore_errors=True)

    def test_defaults_are_traefiks_own_on_both_entrypoints(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["render_rc"], 0, r["render_out"])
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        for ep in ("web", "websecure"):
            timeouts = r["static"]["entryPoints"][ep]["transport"]["respondingTimeouts"]
            self.assertEqual(timeouts, {"readTimeout": "60s", "writeTimeout": "0s", "idleTimeout": "180s"}, ep)

    def test_values_from_env_are_rendered(self):
        env = dict(VALID_ENV, TRAEFIK_READ_TIMEOUT="2m", TRAEFIK_WRITE_TIMEOUT="30m", TRAEFIK_IDLE_TIMEOUT="90s")
        r = render(env)
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        timeouts = r["static"]["entryPoints"]["websecure"]["transport"]["respondingTimeouts"]
        self.assertEqual(timeouts, {"readTimeout": "2m", "writeTimeout": "30m", "idleTimeout": "90s"})

    def test_a_value_that_is_not_a_duration_is_refused(self):
        r = render(dict(VALID_ENV, TRAEFIK_WRITE_TIMEOUT="ten minutes"))
        self.addCleanup(self._cleanup, r)
        self.assertNotEqual(r["validate_rc"], 0)
        self.assertIn("TRAEFIK_WRITE_TIMEOUT", r["validate_out"])

    def test_a_bare_number_of_seconds_is_accepted(self):
        r = render(dict(VALID_ENV, TRAEFIK_READ_TIMEOUT="120"))
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self.assertEqual(r["static"]["entryPoints"]["web"]["transport"]["respondingTimeouts"]["readTimeout"], 120)


class TrustedProxyRanges(unittest.TestCase):
    """forwardedHeaders.trustedIPs is rendered from ops/cloudflare-ips.txt."""

    def _cleanup(self, r):
        shutil.rmtree(r["tmp"], ignore_errors=True)

    def test_rendered_list_equals_the_file_on_both_entrypoints(self):
        """With TRAEFIK_FORWARDED_PROXY=cloudflare; the none mode (the default)
        renders an empty list — test_traefik_forwarded_proxy.py covers both."""
        r = render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["render_rc"], 0, r["render_out"])
        entries, problems = cf_check.read_ranges(TRAEFIK / "ops" / "cloudflare-ips.txt")
        self.assertEqual(problems, [])
        for ep in ("web", "websecure"):
            rendered = r["static"]["entryPoints"][ep]["forwardedHeaders"]["trustedIPs"]
            self.assertEqual(rendered, entries, ep)
        self.assertTrue(any(":" in e for e in entries), "IPv6 ranges present")
        self.assertTrue(any("." in e for e in entries), "IPv4 ranges present")

    def test_a_line_that_is_not_a_range_stops_render_and_validate(self):
        def poison(tmp):
            (tmp / "ops" / "cloudflare-ips.txt").write_text("203.0.113.0/24\nnot-a-range\n", encoding="utf-8")
        r = render(VALID_ENV, poison)
        self.addCleanup(self._cleanup, r)
        self.assertNotEqual(r["render_rc"], 0)
        self.assertIn("not-a-range", r["render_out"])
        self.assertNotEqual(r["validate_rc"], 0)

    def test_an_empty_list_is_refused(self):
        def empty(tmp):
            (tmp / "ops" / "cloudflare-ips.txt").write_text("# nothing\n", encoding="utf-8")
        r = render(VALID_ENV, empty)
        self.addCleanup(self._cleanup, r)
        self.assertNotEqual(r["render_rc"], 0)
        self.assertIn("no range", r["render_out"])

    def test_offline_checker_accepts_the_shipped_file(self):
        self.assertEqual(cf_check.main(["--file", str(TRAEFIK / "ops" / "cloudflare-ips.txt")]), 0)

    def test_offline_checker_reports_duplicates_and_a_missing_family(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        f = tmp / "list.txt"
        f.write_text("203.0.113.0/24\n203.0.113.0/24\n", encoding="utf-8")
        entries, problems = cf_check.read_ranges(f)
        self.assertEqual(entries, ["203.0.113.0/24", "203.0.113.0/24"])
        self.assertTrue(any("twice" in p for p in problems), problems)
        self.assertTrue(any("IPv6" in p for p in problems), problems)
        self.assertEqual(cf_check.main(["--file", str(f)]), 1)


class RequiredVariables(unittest.TestCase):
    """What validate.sh refuses to go without, and what it checks the shape of."""

    def _cleanup(self, r):
        shutil.rmtree(r["tmp"], ignore_errors=True)

    def test_crowdsec_network_name_is_required(self):
        env = dict(VALID_ENV)
        env.pop("CROWDSEC_SECURITY_NETWORK")
        r = render(env)
        self.addCleanup(self._cleanup, r)
        self.assertNotEqual(r["validate_rc"], 0)
        self.assertIn("MISSING: CROWDSEC_SECURITY_NETWORK", r["validate_out"])

    def test_container_names_are_required(self):
        env = dict(VALID_ENV)
        env.pop("TRAEFIK_CONTAINER_NAME")
        r = render(env)
        self.addCleanup(self._cleanup, r)
        self.assertIn("MISSING: TRAEFIK_CONTAINER_NAME", r["validate_out"])

    def test_memory_ceiling_shape_is_checked_when_set(self):
        r = render(dict(VALID_ENV, TRAEFIK_MEMORY="lots"))
        self.addCleanup(self._cleanup, r)
        self.assertNotEqual(r["validate_rc"], 0)
        self.assertIn("TRAEFIK_MEMORY", r["validate_out"])
        r2 = render(dict(VALID_ENV, TRAEFIK_MEMORY="512m"))
        self.addCleanup(self._cleanup, r2)
        self.assertEqual(r2["validate_rc"], 0, r2["validate_out"])

    def test_every_rendered_file_is_checked_for(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        (r["tmp"] / "config" / "dynamic" / "servers-transports.yml").unlink()
        v = subprocess.run(["bash", str(r["tmp"] / "ops/scripts/validate.sh")], capture_output=True, text=True)
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("servers-transports.yml", v.stdout + v.stderr)

    def test_wildcard_router_must_exist_when_the_domain_is_set(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        (r["tmp"] / "config" / "dynamic" / "acme-wildcard.yml").unlink()
        v = subprocess.run(["bash", str(r["tmp"] / "ops/scripts/validate.sh")], capture_output=True, text=True)
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("acme-wildcard.yml", v.stdout + v.stderr)


class UnresolvedVariables(unittest.TestCase):
    """validate.sh refuses a `${…}` left in a file render.sh wrote, and only there:
    the host files scripts/host-files.sh renders into config/host/ carry shell
    variables on purpose."""

    PATTERN = "${LEFTOVER_VARIABLE}"

    def _cleanup(self, r):
        shutil.rmtree(r["tmp"], ignore_errors=True)

    def _validate(self, r):
        v = subprocess.run(["bash", str(r["tmp"] / "ops/scripts/validate.sh")], capture_output=True, text=True)
        return v.returncode, v.stdout + v.stderr

    def _render_host_files(self, tmp):
        # What `scripts/host-files.sh render core/traefik` writes: the manifest's
        # sources under their installed names, the watchdog script and env among them.
        host = tmp / "config" / "host"
        host.mkdir(parents=True, exist_ok=True)
        scripts = tmp / "ops" / "scripts"
        for src, name in (("traefik-watchdog.sh", "traefik-watchdog.sh"),
                          ("traefik-watchdog.env.example", "traefik-watchdog.env"),
                          ("traefik-watchdog.service.example", "traefik-watchdog.service"),
                          ("traefik-watchdog.timer.example", "traefik-watchdog.timer")):
            shutil.copy(scripts / src, host / name)
        self.assertIn("${", (host / "traefik-watchdog.sh").read_text(encoding="utf-8"))

    def test_rendered_host_files_beside_the_configuration_pass(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        self._render_host_files(r["tmp"])
        rc, out = self._validate(r)
        self.assertEqual(rc, 0, out)

    def test_a_file_under_config_host_that_render_did_not_write_is_not_searched(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        (r["tmp"] / "config" / "host").mkdir(parents=True, exist_ok=True)
        (r["tmp"] / "config" / "host" / "notes.sh").write_text(f'echo "{self.PATTERN}"\n', encoding="utf-8")
        rc, out = self._validate(r)
        self.assertEqual(rc, 0, out)

    def test_a_leftover_in_a_dynamic_file_is_refused_and_named(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        target = r["tmp"] / "config" / "dynamic" / "model.yml"
        target.write_text(target.read_text(encoding="utf-8") + f"# {self.PATTERN}\n", encoding="utf-8")
        rc, out = self._validate(r)
        self.assertNotEqual(rc, 0)
        self.assertIn("Unresolved variables", out)
        self.assertIn("model.yml", out)
        self.assertIn("LEFTOVER_VARIABLE", out)

    def test_a_leftover_in_the_static_file_is_refused(self):
        r = render(VALID_ENV)
        self.addCleanup(self._cleanup, r)
        target = r["tmp"] / "config" / "traefik.yml"
        target.write_text(target.read_text(encoding="utf-8") + f"# {self.PATTERN}\n", encoding="utf-8")
        rc, out = self._validate(r)
        self.assertNotEqual(rc, 0)
        self.assertIn("traefik.yml", out)

    def test_a_leftover_in_the_rendered_firewall_file_is_refused(self):
        r = render(dict(VALID_ENV, TRAEFIK_FORWARDED_PROXY="cloudflare"))
        self.addCleanup(self._cleanup, r)
        self.assertEqual(r["validate_rc"], 0, r["validate_out"])
        target = r["tmp"] / "config" / "host" / "cloudflare-ranges.nft"
        self.assertTrue(target.exists())
        target.write_text(target.read_text(encoding="utf-8") + f"# {self.PATTERN}\n", encoding="utf-8")
        rc, out = self._validate(r)
        self.assertNotEqual(rc, 0)
        self.assertIn("cloudflare-ranges.nft", out)


if __name__ == "__main__":
    unittest.main()
