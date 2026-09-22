#!/usr/bin/env python3
"""Regression cover for the opt-in overlay validation in check-overlays.py.

The defect this guards against is not a malformed overlay — it is a *correct*
overlay that quietly weakens a service the base file hardened. A block with no
image adds no service and reads as harmless, yet it can hand that service the
Docker socket, set `privileged: true`, or clear the memory ceiling with
`!reset`. Judging the overlay file on its own sees none of it, which is why
these tests assert against the merged result Compose actually produces.

The merge cases need Docker and are skipped without it; the rule cases do not.

Run:
    python3 scripts/ci/test_check_overlays.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("check_overlays", HERE / "check-overlays.py")
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)

HAVE_DOCKER = co.docker_available()

BASE = """\
services:
  widget-app:
    image: example/widget:1.0
    security_opt:
      - no-new-privileges:true
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256m
          pids: 100
    networks:
      - app-internal
networks:
  app-internal:
    internal: true
"""


def _stack(root: Path, overlay: str, name: str = "feature.yml") -> tuple[Path, Path]:
    """A minimal compliant stack plus one overlay, as real files."""
    app = root / "apps" / "widget"
    app.mkdir(parents=True)
    (app / "docker-compose.yml").write_text(BASE)
    (app / ".env.example").write_text("COMPOSE_PROJECT_NAME=widget\n")
    (app / name).write_text(overlay)
    return app, app / name


class RuntimeRules(unittest.TestCase):
    """The mandatory runtime rules, against an effective service definition."""

    def rules(self, svc: dict, name: str = "widget-app") -> set[str]:
        return {f["rule"] for f in co.runtime_findings(name, svc, "feature.yml")}

    def _compliant(self) -> dict:
        return {"image": "example/widget:1.0", "memswap_limit": "256m",
                "deploy": {"resources": {"limits": {"memory": 268435456, "pids": 100}}}}

    def test_a_compliant_service_reports_nothing(self):
        self.assertEqual(self.rules(self._compliant()), set())

    def test_resources_cleared_is_reported(self):
        svc = self._compliant()
        svc["deploy"] = {}
        self.assertEqual(self.rules(svc), {"no-resources"})

    def test_swap_policy_cleared_is_reported(self):
        svc = self._compliant()
        del svc["memswap_limit"]
        self.assertIn("no-swap-policy", self.rules(svc))

    def test_privileged_is_reported(self):
        svc = self._compliant()
        svc["privileged"] = True
        self.assertIn("privileged", self.rules(svc))

    def test_unpinned_image_is_reported(self):
        svc = self._compliant()
        svc["image"] = "example/widget:latest"
        self.assertIn("latest-tag", self.rules(svc))

    def test_a_datastore_publishing_a_port_is_reported(self):
        svc = self._compliant()
        svc["ports"] = ["5432:5432"]
        self.assertIn("db-exposed", self.rules(svc, name="db"))

    def test_an_unresolved_tag_is_reported(self):
        """A variable that resolved to nothing leaves `image:` with an empty tag."""
        svc = self._compliant()
        svc["image"] = "example/widget:"
        self.assertIn("unresolved-tag", self.rules(svc))

    def test_mem_limit_shorthand_counts_as_a_memory_ceiling(self):
        """`docker compose config` emits `mem_limit`, not only deploy limits."""
        svc = {"image": "example/widget:1.0", "memswap_limit": "256m",
               "mem_limit": 268435456, "pids_limit": 100}
        self.assertEqual(self.rules(svc), set())


class OverlayEnv(unittest.TestCase):
    """An overlay with its own variables names the example beside itself."""

    def test_docker_compose_agent_yml_finds_env_agent_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / ".env.agent.example").write_text("ORION_AGENT_TAG=1.2.0\n")
            found = co.overlay_env(app, app / "docker-compose.agent.yml")
            self.assertEqual(found, app / ".env.agent.example")

    def test_an_overlay_without_its_own_env_example_gets_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            self.assertIsNone(co.overlay_env(app, app / "network-host.yml"))


@unittest.skipUnless(HAVE_DOCKER, "needs Docker to perform the Compose merge")
class EffectiveMerge(unittest.TestCase):
    """A patch-only overlay is judged by what the merged deployment becomes."""

    def _run(self, overlay: str, name: str = "feature.yml") -> tuple[set[str], bool]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, overlay, name)
            cwd = os.getcwd()
            os.chdir(root)
            try:
                co._structure.repository_files.cache_clear()
                found, touched = co.check_variant(Path("apps/widget"),
                                                  Path("apps/widget") / name)
                return {f["rule"] for f in found}, touched
            finally:
                os.chdir(cwd)
                co._structure.repository_files.cache_clear()

    def findings(self, overlay: str, name: str = "feature.yml") -> set[str]:
        return self._run(overlay, name)[0]

    def test_a_legitimate_patch_passes(self):
        rules = self.findings("services:\n  widget-app:\n"
                              "    environment:\n      FEATURE_ENABLED: \"true\"\n")
        self.assertEqual(rules, set())

    def test_a_patch_cannot_silently_clear_the_resource_ceiling(self):
        rules = self.findings("services:\n  widget-app:\n    deploy: !reset null\n")
        self.assertIn("no-resources", rules)

    def test_a_patch_cannot_silently_clear_the_swap_policy(self):
        rules = self.findings("services:\n  widget-app:\n    memswap_limit: !reset null\n")
        self.assertIn("no-swap-policy", rules)

    def test_a_patch_cannot_silently_enable_privileged(self):
        rules = self.findings("services:\n  widget-app:\n    privileged: true\n")
        self.assertIn("privileged", rules)

    def test_a_patch_cannot_silently_mount_the_docker_socket(self):
        rules = self.findings("services:\n  widget-app:\n    volumes:\n"
                              "      - /var/run/docker.sock:/var/run/docker.sock:ro\n")
        self.assertIn("direct socket mount", rules)

    def test_a_patch_cannot_silently_drop_no_new_privileges(self):
        rules = self.findings("services:\n  widget-app:\n    security_opt: !reset null\n")
        self.assertIn("no-new-privileges missing", rules)

    def test_a_patch_targeting_a_service_the_stack_does_not_define_is_rejected(self):
        """Compose refuses the project: the block becomes a service with no image."""
        rules = self.findings("services:\n  app:\n    network_mode: host\n")
        self.assertIn("overlay-invalid", rules)

    def test_an_introduced_service_is_judged_in_full(self):
        rules = self.findings("services:\n  extra:\n    image: example/x:latest\n")
        self.assertLessEqual({"latest-tag", "no-resources"}, rules)

    def test_a_network_only_overlay_is_merge_validated_without_service_checks(self):
        """It changes no service, so it must still resolve — and claim nothing more."""
        rules, touched = self._run("networks:\n  app-internal:\n    internal: true\n",
                                   name="network-alt.yml")
        self.assertEqual(rules, set())
        self.assertFalse(touched)

    def test_a_broken_network_only_overlay_cannot_escape_validation(self):
        """The regression guarded here: an overlay that touches no service used to
        be invisible to discovery entirely, so a merge it breaks went unnoticed."""
        rules, touched = self._run(
            "networks:\n  app-internal:\n    bogus_key: true\n", name="network-alt.yml")
        self.assertIn("overlay-invalid", rules)
        self.assertFalse(touched)

    def test_a_variable_the_example_leaves_commented_is_enabled_for_the_variant(self):
        """Enabling an opt-in feature means uncommenting what its docs name."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app, _ = _stack(root, "networks:\n  app-internal:\n    ipam:\n"
                                  "      config:\n        - subnet: ${ALT_SUBNET:?set it}\n",
                            "network-alt.yml")
            (app / ".env.example").write_text(
                "COMPOSE_PROJECT_NAME=widget\n# ALT_SUBNET=10.99.0.0/16\n")
            cwd = os.getcwd()
            os.chdir(root)
            try:
                co._structure.repository_files.cache_clear()
                found, _ = co.check_variant(Path("apps/widget"),
                                            Path("apps/widget/network-alt.yml"))
            finally:
                os.chdir(cwd)
                co._structure.repository_files.cache_clear()
        self.assertEqual({f["rule"] for f in found}, set())

    def test_a_variable_with_no_example_anywhere_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stack(root, "networks:\n  app-internal:\n    ipam:\n"
                         "      config:\n        - subnet: ${NOWHERE_SUBNET:?set it}\n",
                   "network-alt.yml")
            cwd = os.getcwd()
            os.chdir(root)
            try:
                co._structure.repository_files.cache_clear()
                found, _ = co.check_variant(Path("apps/widget"),
                                            Path("apps/widget/network-alt.yml"))
            finally:
                os.chdir(cwd)
                co._structure.repository_files.cache_clear()
        self.assertIn("overlay-invalid", {f["rule"] for f in found})

    def test_an_untouched_service_is_not_re_reported(self):
        """The canonical run already covers it; repeating it is noise."""
        rules = self.findings("services:\n  extra:\n    image: example/x:1.0\n"
                              "    memswap_limit: 64m\n    security_opt:\n"
                              "      - no-new-privileges:true\n"
                              "    deploy:\n      resources:\n        limits:\n"
                              "          memory: 64m\n          pids: 50\n")
        self.assertEqual(rules, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
