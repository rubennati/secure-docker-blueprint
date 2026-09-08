#!/usr/bin/env python3
"""Regression cover for the shared-network identity rules in check-structure.py.

Compose publishes a service key as a discoverable name on every network the
service joins. Docker states that a network-wide name shared by more than one
container resolves to an unspecified one of them, so two independently
deployable stacks must not publish the same key into a shared external network.

These tests hold three things in place:
  * the rule fires on the first generic key, not only once two stacks collide;
  * an inherently application-specific key needs no role suffix;
  * a stack whose directory and COMPOSE_PROJECT_NAME disagree is reported
    rather than silently resolved one way.

Run:
    python3 scripts/ci/test_check_structure.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "check-structure.py"

spec = importlib.util.spec_from_file_location("check_structure", CHECKER)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


COMPOSE = """\
services:
{services}
networks:
  proxy-public:
    external: true
  app-internal:
    internal: true
"""

SERVICE = """\
  {key}:
    image: example/image:1.0
    networks:
{networks}
"""


def _reset_caches():
    """The checker caches Git state and the canonical network for the real
    repository; a test running in a temporary tree must not inherit either."""
    cs.repository_files.cache_clear()
    cs.canonical_shared_network.cache_clear()


def _stack(root: Path, path: str, services, project=None, extra_env=""):
    """Write a minimal but structurally real stack under `root`."""
    app = root / path
    app.mkdir(parents=True, exist_ok=True)
    blocks = ""
    for key, nets in services:
        netlines = "".join(f"      - {n}\n" for n in nets)
        blocks += SERVICE.format(key=key, networks=netlines)
    (app / "docker-compose.yml").write_text(COMPOSE.format(services=blocks))
    if project is not None or extra_env:
        env = f"COMPOSE_PROJECT_NAME={project}\n" if project else ""
        (app / ".env.example").write_text(env + extra_env)
    return app


class SharedNetworkDiscovery(unittest.TestCase):
    def test_external_network_is_discovered_not_hardcoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("alpha-app", ["proxy-public"])], project="alpha")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                _reset_caches()
                # One stack alone is not shared, so give it a second attacher.
                _stack(root, "apps/beta", [("beta-app", ["proxy-public"])], project="beta")
                self.assertIn("proxy-public", cs.shared_external_networks())
                # internal: true is not shared and must not be picked up
                self.assertNotIn("app-internal", cs.shared_external_networks())
            finally:
                os.chdir(cwd)


class StackIdentity(unittest.TestCase):
    def test_project_name_is_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _stack(Path(tmp), "apps/paperless-ngx",
                         [("paperless-app", ["proxy-public"])], project="paperless")
            identity, disagreement = cs.stack_identity(app)
            self.assertEqual(identity, "paperless")
            self.assertIsNotNone(disagreement)
            self.assertIn("paperless-ngx", disagreement)

    def test_directory_is_fallback_when_no_env_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _stack(Path(tmp), "apps/beta", [("beta-app", ["proxy-public"])])
            identity, disagreement = cs.stack_identity(app)
            self.assertEqual(identity, "beta")
            self.assertIsNone(disagreement)

    def test_agreement_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _stack(Path(tmp), "apps/caldiy",
                         [("caldiy-app", ["proxy-public"])], project="caldiy")
            identity, disagreement = cs.stack_identity(app)
            self.assertEqual(identity, "caldiy")
            self.assertIsNone(disagreement)


class IdentityConformance(unittest.TestCase):
    def test_prefixed_key_conforms(self):
        self.assertTrue(cs.identity_conforms("caldiy-app", "caldiy"))
        self.assertTrue(cs.identity_conforms("nextcloud-nginx", "nextcloud"))

    def test_bare_identity_conforms_without_role_suffix(self):
        # `seafile` is already application-specific; a `-server` suffix would be
        # redundant, and the rule is semantic rather than a formatting mandate.
        self.assertTrue(cs.identity_conforms("seafile", "seafile"))

    def test_generic_keys_do_not_conform(self):
        for key in ("app", "nginx", "api", "web", "server", "ui", "proxy", "hub"):
            self.assertFalse(cs.identity_conforms(key, "caldiy"), key)

    def test_foreign_prefix_does_not_conform(self):
        self.assertFalse(cs.identity_conforms("ghost-app", "caldiy"))


class SharedNetworkRules(unittest.TestCase):
    def _run(self, root):
        cwd = os.getcwd()
        try:
            os.chdir(root)
            _reset_caches()
            by_app: dict = {}
            cs.check_shared_network_identity(by_app)
            return {str(a): f for a, f in by_app.items() if f}
        finally:
            os.chdir(cwd)

    def _rules(self, findings):
        return {f["rule"] for f in findings}

    def test_generic_key_fails_even_when_unique(self):
        """The invariant is proactive — one stack is enough to fail."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("app", ["proxy-public"])], project="alpha")
            _stack(root, "apps/peer", [("peer-app", ["proxy-public"])], project="peer")
            out = self._run(root)
            self.assertIn("shared-net-identity", self._rules(out["apps/alpha"]))
            self.assertNotIn("shared-net-duplicate", self._rules(out["apps/alpha"]))

    def test_conforming_key_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("alpha-app", ["proxy-public"])], project="alpha")
            _stack(root, "apps/peer", [("peer-app", ["proxy-public"])], project="peer")
            out = self._run(root)
            self.assertEqual(out.get("apps/alpha", []), [])

    def test_private_services_keep_short_keys(self):
        """`db` and `redis` are untouched while they stay off the shared network."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [
                ("alpha-app", ["proxy-public", "app-internal"]),
                ("db", ["app-internal"]),
                ("redis", ["app-internal"]),
            ], project="alpha")
            _stack(root, "apps/peer", [("peer-app", ["proxy-public"])], project="peer")
            out = self._run(root)
            self.assertEqual(out.get("apps/alpha", []), [])

    def test_duplicate_key_fails_both_stacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("app", ["proxy-public"])], project="alpha")
            _stack(root, "apps/beta", [("app", ["proxy-public"])], project="beta")
            out = self._run(root)
            for stack in ("apps/alpha", "apps/beta"):
                self.assertIn("shared-net-duplicate", self._rules(out[stack]), stack)

    def test_identity_disagreement_is_warned_not_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/lycheeorg", [("app", ["proxy-public"])], project="lychee")
            _stack(root, "apps/peer", [("peer-app", ["proxy-public"])], project="peer")
            out = self._run(root)
            rules = self._rules(out["apps/lycheeorg"])
            self.assertIn("identity-source", rules)
            levels = {f["rule"]: f["level"] for f in out["apps/lycheeorg"]}
            self.assertEqual(levels["identity-source"], "WARN")

    def test_disagreement_warning_is_emitted_once_per_stack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/lycheeorg", [
                ("lychee-app", ["proxy-public"]),
                ("lychee-nginx", ["proxy-public"]),
            ], project="lychee")
            _stack(root, "apps/peer", [("peer-app", ["proxy-public"])], project="peer")
            out = self._run(root)
            warns = [f for f in out["apps/lycheeorg"] if f["rule"] == "identity-source"]
            self.assertEqual(len(warns), 1)


# A network declared under a different Compose key but resolving, through the
# stack's own .env.example, to the same Docker network.
VAR_COMPOSE = """\
services:
  {key}:
    image: example/image:1.0
    networks:
      - proxy
networks:
  proxy:
    external: true
    name: ${{TRAEFIK_NETWORK}}
"""


def _var_stack(root: Path, path: str, key: str, project: str, network: str):
    app = root / path
    app.mkdir(parents=True, exist_ok=True)
    (app / "docker-compose.yml").write_text(VAR_COMPOSE.format(key=key))
    (app / ".env.example").write_text(
        f"COMPOSE_PROJECT_NAME={project}\nTRAEFIK_NETWORK={network}\n")
    return app


class EffectiveNetworkResolution(unittest.TestCase):
    """`external: true` does not mean shared, and the Compose key is not the
    network's identity. Both distinctions are load-bearing."""

    def _shared(self, root):
        cwd = os.getcwd()
        try:
            os.chdir(root)
            _reset_caches()
            return cs.shared_external_networks()
        finally:
            os.chdir(cwd)

    def _findings(self, root):
        cwd = os.getcwd()
        try:
            os.chdir(root)
            _reset_caches()
            by_app: dict = {}
            cs.check_shared_network_identity(by_app)
            return {str(a): {f["rule"] for f in fs} for a, fs in by_app.items() if fs}
        finally:
            os.chdir(cwd)

    def test_shared_external_network_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("app", ["proxy-public"])], project="alpha")
            _stack(root, "apps/beta", [("beta-app", ["proxy-public"])], project="beta")
            self.assertIn("proxy-public", self._shared(root))
            self.assertIn("shared-net-identity", self._findings(root)["apps/alpha"])

    def test_private_network_is_not_checked(self):
        """A stack-private network never enters the rule, whatever the key."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("app", ["app-internal"])], project="alpha")
            _stack(root, "apps/beta", [("app", ["app-internal"])], project="beta")
            self.assertNotIn("app-internal", self._shared(root))
            self.assertEqual(self._findings(root), {})

    def test_external_but_single_stack_is_not_shared(self):
        """One stack attaching to an external network does not make it a shared
        namespace — there is nothing to be ambiguous with."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _var_stack(root, "apps/alpha", "app", "alpha", "some-other-net")
            self.assertNotIn("some-other-net", self._shared(root))
            self.assertEqual(self._findings(root), {})

    def test_second_stack_makes_network_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _var_stack(root, "apps/alpha", "app", "alpha", "some-other-net")
            _var_stack(root, "apps/beta", "beta-app", "beta", "some-other-net")
            self.assertIn("some-other-net", self._shared(root))
            self.assertIn("shared-net-identity", self._findings(root)["apps/alpha"])

    def test_differing_key_resolves_to_same_network(self):
        """The regression that the Compose-key approach missed: `proxy` with
        `name: ${TRAEFIK_NETWORK}` is the same namespace as `proxy-public`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("alpha-app", ["proxy-public"])], project="alpha")
            _var_stack(root, "business/gamma", "web", "gamma", "proxy-public")
            self.assertIn("proxy-public", self._shared(root))
            found = self._findings(root)
            self.assertIn("shared-net-identity", found["business/gamma"])
            self.assertNotIn("apps/alpha", found)

    def test_duplicate_detection_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "apps/alpha", [("app", ["proxy-public"])], project="alpha")
            _var_stack(root, "business/gamma", "app", "gamma", "proxy-public")
            found = self._findings(root)
            for stack in ("apps/alpha", "business/gamma"):
                self.assertIn("shared-net-duplicate", found[stack], stack)


if __name__ == "__main__":
    unittest.main(verbosity=2)
