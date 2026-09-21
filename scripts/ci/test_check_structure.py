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

import contextlib
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


class ResourceLimits(unittest.TestCase):
    """`no-resources` and `no-swap-policy` — both FAIL since 2026-09-16, once
    every production service states memory, pids and a swap policy."""

    def _findings_for(self, root: Path, compose_yaml: str) -> list[dict]:
        app = root / "apps" / "widget"
        app.mkdir(parents=True, exist_ok=True)
        (app / "docker-compose.yml").write_text(compose_yaml)
        cwd = os.getcwd()
        try:
            os.chdir(root)
            _reset_caches()
            findings: list[dict] = []
            cs.check_compose(app, findings)
            return findings
        finally:
            os.chdir(cwd)

    def test_memory_without_memswap_limit_fails(self):
        compose = """\
services:
  app:
    image: example/image:1.0
    deploy:
      resources:
        limits:
          memory: 512m
          pids: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            found = self._findings_for(Path(tmp), compose)
        rules = {f["rule"] for f in found}
        self.assertIn("no-swap-policy", rules)
        swap = next(f for f in found if f["rule"] == "no-swap-policy")
        self.assertEqual(swap["level"], "FAIL")

    def test_matching_memswap_limit_passes(self):
        compose = """\
services:
  app:
    image: example/image:1.0
    memswap_limit: 512m
    deploy:
      resources:
        limits:
          memory: 512m
          pids: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            found = self._findings_for(Path(tmp), compose)
        rules = {f["rule"] for f in found}
        self.assertNotIn("no-swap-policy", rules)
        self.assertNotIn("no-resources", rules)

    def test_env_var_memswap_limit_passes(self):
        """The one non-literal case in the tree: backup/urbackup ties both
        values to the same variable rather than a literal."""
        compose = """\
services:
  app:
    image: example/image:1.0
    memswap_limit: ${APP_MEM_LIMIT}
    deploy:
      resources:
        limits:
          memory: ${APP_MEM_LIMIT}
          pids: 500
"""
        with tempfile.TemporaryDirectory() as tmp:
            found = self._findings_for(Path(tmp), compose)
        rules = {f["rule"] for f in found}
        self.assertNotIn("no-swap-policy", rules)

    def test_missing_pids_still_fails_no_resources(self):
        """Regression guard: no-swap-policy replacing the WARN must not have
        loosened the older, unrelated no-resources FAIL."""
        compose = """\
services:
  app:
    image: example/image:1.0
    memswap_limit: 512m
    deploy:
      resources:
        limits:
          memory: 512m
"""
        with tempfile.TemporaryDirectory() as tmp:
            found = self._findings_for(Path(tmp), compose)
        rules = {f["rule"] for f in found}
        self.assertIn("no-resources", rules)


class ComposeTags(unittest.TestCase):
    """`!reset` / `!override` must parse, not silently disqualify a file.

    `yaml.safe_load` raises on them and `is_compose()` reported that as "not a
    compose file", which hid backup/urbackup/network-host.yml from every checker.
    """

    def test_reset_tag_parses_and_file_counts_as_compose(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "network-host.yml"
            f.write_text("services:\n  app:\n    network_mode: host\n    networks: !reset null\n")
            data = cs.compose_load(f)
            self.assertEqual(data["services"]["app"]["networks"], None)
            self.assertTrue(cs.is_compose(f))

    def test_genuinely_broken_yaml_still_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "broken.yml"
            f.write_text("services:\n  app:\n   - [unclosed\n")
            self.assertFalse(cs.is_compose(f))


class ImagePins(unittest.TestCase):
    """Reproducibility is checked in every committed example file, both styles.

    The rule used to read `.env.example` and match `*_TAG`. That left 84
    committed `*.env*.example` files unchecked, and missed the `*_IMAGE` style
    inside the file it did read — so `APP_IMAGE=x:latest` passed while
    `APP_TAG=latest` failed, for the same defect.
    """

    def test_tag_variable_yields_its_tag(self):
        self.assertEqual(cs.pinned_tag("APP_TAG", "1.2.3"), "1.2.3")

    def test_image_variable_yields_the_tag_half(self):
        self.assertEqual(cs.pinned_tag("APP_IMAGE", "seafileltd/seafile-mc:13.0.20"), "13.0.20")

    def test_registry_port_is_not_mistaken_for_a_tag(self):
        self.assertEqual(cs.pinned_tag("APP_IMAGE", "registry:5000/app:2.1"), "2.1")

    def test_digest_is_stripped_before_the_tag_is_judged(self):
        self.assertEqual(cs.pinned_tag("APP_TAG", "2.5.x@sha256:abc"), "2.5.x")

    def test_a_variable_that_pins_nothing_is_ignored(self):
        self.assertIsNone(cs.pinned_tag("APP_HOST", "example.com"))
        self.assertIsNone(cs.pinned_tag("APP_IMAGE", "nginx"))

    def test_a_registry_port_without_a_tag_is_not_read_as_one(self):
        self.assertIsNone(cs.pinned_tag("APP_IMAGE", "registry:5000/app"))

    def test_unpinned_local_example_fails(self):
        """The case the old rule could not see: a bad tag outside .env.example."""
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / ".env.local.example").write_text("APP_TAG=latest\n")
            findings: list[dict] = []
            cs.check_env_pins(app, findings)
            self.assertEqual([f["rule"] for f in findings], ["latest-tag"])
            self.assertIn(".env.local.example", findings[0]["detail"])

    def test_unpinned_image_variable_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / ".env.example").write_text("APP_IMAGE=nginx:latest\n")
            findings: list[dict] = []
            cs.check_env_pins(app, findings)
            self.assertEqual([f["rule"] for f in findings], ["latest-tag"])

    def test_a_pinned_example_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / ".env.example").write_text("APP_TAG=1.2.3\nAPP_IMAGE=nginx:1.27-alpine\n")
            (app / ".env.local.example").write_text("APP_TAG=1.2.3\n")
            findings: list[dict] = []
            cs.check_env_pins(app, findings)
            self.assertEqual(findings, [])


class LocalPinDrift(unittest.TestCase):
    """A local stack runs production's version of production's image.

    The join is on the image repository, not the variable name or the service
    key — both legitimately differ between the two files — so the exceptions
    fall out of the rule instead of needing a list.
    """

    @staticmethod
    def _stack(tmp, prod_image, local_image, prod_env="", local_env=""):
        app = Path(tmp)
        (app / "docker-compose.yml").write_text(
            f"services:\n  app:\n    image: {prod_image}\n")
        (app / "docker-compose.local.yml").write_text(
            f"services:\n  app:\n    image: {local_image}\n")
        (app / ".env.example").write_text(prod_env)
        (app / ".env.local.example").write_text(local_env)
        return app

    def _findings(self, app):
        out: list[dict] = []
        cs.check_local_pins(app, out)
        return out

    def test_same_image_different_version_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "app:${APP_TAG}", "app:${APP_TAG}",
                              "APP_TAG=2.0.0\n", "APP_TAG=1.0.0\n")
            f = self._findings(app)
            self.assertEqual([x["rule"] for x in f], ["local-pin-drift"])
            self.assertIn("production pins 2.0.0", f[0]["detail"])

    def test_same_image_same_version_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "app:${APP_TAG}", "app:${APP_TAG}",
                              "APP_TAG=2.0.0\n", "APP_TAG=2.0.0\n")
            self.assertEqual(self._findings(app), [])

    def test_a_deliberately_different_image_is_never_compared(self):
        """apps/vllm runs the CPU build locally — no shared repository, no rule."""
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "vllm/vllm-openai:${APP_TAG}",
                              "vllm/vllm-openai-cpu:${APP_TAG}",
                              "APP_TAG=1.0.0\n", "APP_TAG=1.0.0\n")
            self.assertEqual(self._findings(app), [])

    def test_the_two_pinning_styles_compare_equal(self):
        """Seafile writes the whole reference in production, a bare tag locally."""
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "${APP_IMAGE}", "seafileltd/seafile-mc:${APP_TAG}",
                              "APP_IMAGE=seafileltd/seafile-mc:13.0.20\n",
                              "APP_TAG=13.0.20\n")
            self.assertEqual(self._findings(app), [])

    def test_a_differing_digest_on_the_same_tag_fails(self):
        """urbackup pins a moving tag, so the digest is what fixes the image."""
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "u/s:${APP_TAG}", "u/s:${APP_TAG}",
                              "APP_TAG=2.5.x@sha256:aaa\n", "APP_TAG=2.5.x@sha256:bbb\n")
            self.assertEqual([x["rule"] for x in self._findings(app)], ["local-pin-drift"])

    def test_a_service_absent_locally_is_not_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / "docker-compose.yml").write_text(
                "services:\n  app:\n    image: app:1.0.0\n  search:\n    image: es:8.1\n")
            (app / "docker-compose.local.yml").write_text(
                "services:\n  app:\n    image: app:1.0.0\n")
            (app / ".env.example").write_text("")
            (app / ".env.local.example").write_text("")
            self.assertEqual(self._findings(app), [])

    def test_a_stack_without_a_local_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / "docker-compose.yml").write_text("services:\n  app:\n    image: app:1.0.0\n")
            self.assertEqual(self._findings(app), [])

    def test_an_unresolved_variable_is_not_guessed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self._stack(tmp, "app:${APP_TAG}", "app:${MISSING}", "APP_TAG=2.0.0\n", "")
            self.assertEqual(self._findings(app), [])

    def test_registry_port_splits_on_the_tag_not_the_port(self):
        self.assertEqual(cs.split_image_ref("registry:5000/app:2.1"), ("registry:5000/app", "2.1"))
        self.assertEqual(cs.split_image_ref("registry:5000/app"), ("registry:5000/app", ""))

    def test_digest_stays_with_the_pin(self):
        self.assertEqual(cs.split_image_ref("u/s:2.5.x@sha256:abc"), ("u/s", "2.5.x@sha256:abc"))


class OverlayDiscovery(unittest.TestCase):
    """Which files are canonical production, and which are opt-in overlays."""

    @contextlib.contextmanager
    def _in(self, root: Path):
        """Run inside the temporary tree.

        `in_repository()` asks Git about the *current* directory, so a test that
        stays in the real checkout has its temporary files rejected as untracked.
        """
        cwd = os.getcwd()
        os.chdir(root)
        _reset_caches()
        try:
            yield
        finally:
            os.chdir(cwd)
            _reset_caches()

    def _tree(self, root: Path):
        app = _stack(root, "apps/widget", [("widget-app", ["proxy-public"])])
        (app / "docker-compose.local.yml").write_text("services:\n  widget-app:\n    image: x:1\n")
        (app / "feature.yml").write_text("services:\n  extra:\n    image: x:1\n")
        (app / "network-alt.yml").write_text("networks:\n  app-internal:\n    internal: true\n")
        (app / "config.example.yaml").write_text("endpoints:\n  - name: a\n")
        return Path("apps/widget")

    def test_canonical_set_is_unchanged_by_an_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self._tree(Path(tmp))
            with self._in(Path(tmp)):
                self.assertEqual([p.name for p in cs.compose_files(app)], ["docker-compose.yml"])

    def test_overlay_includes_a_network_only_file_and_excludes_non_compose(self):
        """A network-only overlay is a compose file; a stack's config example is not.

        `is_compose()` requires `services:`, which is right for finding a stack and
        wrong for finding overlays — it hid the one overlay that changes the address
        plan of every routed service.
        """
        with tempfile.TemporaryDirectory() as tmp:
            app = self._tree(Path(tmp))
            with self._in(Path(tmp)):
                self.assertEqual([p.name for p in cs.overlay_files(app)],
                                 ["feature.yml", "network-alt.yml"])

    def test_a_network_only_file_is_not_mistaken_for_a_stack(self):
        """Stack discovery must stay narrower than overlay discovery."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lone = root / "apps" / "networks-only"
            lone.mkdir(parents=True)
            (lone / "network-alt.yml").write_text("networks:\n  a:\n    internal: true\n")
            with self._in(root):
                self.assertFalse(cs.is_compose(lone / "network-alt.yml"))
                self.assertTrue(cs.is_compose_fragment(lone / "network-alt.yml"))
                self.assertNotIn(lone, cs.find_apps())

    def test_a_split_stack_has_no_overlays(self):
        """Every file defines the stack, so none of them is opt-in."""
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "apps" / "split"
            app.mkdir(parents=True)
            (app / "a-server.yml").write_text("services:\n  a:\n    image: x:1\n")
            (app / "b-server.yml").write_text("services:\n  b:\n    image: x:1\n")
            with self._in(Path(tmp)):
                rel = Path("apps/split")
                self.assertEqual(len(cs.compose_files(rel)), 2)
                self.assertEqual(cs.overlay_files(rel), [])


class IntroducesService(unittest.TestCase):
    def test_image_or_build_introduces(self):
        self.assertTrue(cs.introduces_service({"image": "x:1"}))
        self.assertTrue(cs.introduces_service({"build": "."}))

    def test_a_bare_patch_does_not(self):
        self.assertFalse(cs.introduces_service({"environment": {"A": "b"}}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
