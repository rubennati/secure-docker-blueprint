#!/usr/bin/env python3
"""The middleware model on every router (Phase 4.2): the rules in
check-structure.py that describe the four positions.

- router-positions: a router missing a position, carrying one twice, out of
  order, with an empty variable, or still naming what the model replaces
- block-order: a response-header block after the headers profile, a request
  block before the auth position
- burst-exposure: limit-extra-large (or a sec-*-xl chain) only behind a
  closed access policy — judged per router, on the router's own variable
- tls-conflict: two routers of one stack naming different tls.options for
  one host name
- a stack's own gate (<stack>-auth@docker) is the auth position when the
  stack's *_TRAEFIK_AUTH variable carries it

Run:
    python3 scripts/ci/test_traefik_router_model.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_structure", HERE / "check-structure.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

MODEL_ENV = """COMPOSE_PROJECT_NAME=demo
APP_TRAEFIK_HOST=demo.example.com
APP_TRAEFIK_ACCESS=access-public
APP_TRAEFIK_LIMIT=limit-standard
APP_TRAEFIK_HEADERS=headers-standard
APP_TRAEFIK_AUTH=auth-none@file
"""

OLD_ENV = """COMPOSE_PROJECT_NAME=demo
APP_TRAEFIK_HOST=demo.example.com
APP_TRAEFIK_TLS_OPTION=tls-aplus
APP_TRAEFIK_ACCESS=acc-public
APP_TRAEFIK_SECURITY=sec-2
APP_TRAEFIK_THREAT=
"""

MODEL_LABEL = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"


def compose(routers):
    """A compose file with one service and the given routers:
    [(name, rule, middlewares, tls_options or None)]."""
    labels = ['      - "traefik.enable=true"']
    for name, rule, mw, tls in routers:
        labels.append(f'      - "traefik.http.routers.{name}.rule={rule}"')
        labels.append(f'      - "traefik.http.routers.{name}.tls=true"')
        if tls is not None:
            labels.append(f'      - "traefik.http.routers.{name}.tls.options={tls}"')
        if mw is not None:
            labels.append(f'      - "traefik.http.routers.{name}.middlewares={mw}"')
    return "services:\n  demo-app:\n    image: example/app:1.0\n    labels:\n" + "\n".join(labels) + "\n"


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        os.chdir(self.root)
        cs.repository_files.cache_clear()
        cs.canonical_shared_network.cache_clear()

    def tearDown(self):
        os.chdir(self.cwd)
        cs.repository_files.cache_clear()
        cs.canonical_shared_network.cache_clear()
        self.tmp.cleanup()

    def findings(self, env, routers):
        app = self.root / "apps" / "demo"
        app.mkdir(parents=True, exist_ok=True)
        (app / ".env.example").write_text(env, encoding="utf-8")
        (app / "docker-compose.yml").write_text(compose(routers), encoding="utf-8")
        out = []
        cs.check_routers(Path("apps/demo"), out)
        return out

    def rule(self, findings, name):
        return [f for f in findings if f["rule"] == name]


class RouterPositions(Scratch):
    def test_the_model_shape_passes(self):
        f = self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)])
        self.assertEqual(f, [], f)

    def test_the_old_shape_is_reported_with_its_names_at_the_transition_level(self):
        f = self.rule(self.findings(OLD_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)",
                                                "${APP_TRAEFIK_THREAT}${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file",
                                                "${APP_TRAEFIK_TLS_OPTION}@file")]), "router-positions")
        self.assertEqual(len(f), 1, f)
        self.assertEqual(f[0]["level"], cs.MODEL_LEVEL)
        self.assertEqual(f[0]["service"], "demo")
        self.assertIn("missing limit, auth", f[0]["detail"])
        self.assertIn("names the model replaces: acc-public, sec-2", f[0]["detail"])

    def test_a_router_without_the_headers_position_is_reported(self):
        label = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}"
        f = self.rule(self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("missing headers", f[0]["detail"])

    def test_a_router_without_any_middlewares_misses_all_four(self):
        f = self.rule(self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", None, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("missing access, limit, headers, auth", f[0]["detail"])

    def test_positions_out_of_order_and_twice_are_named(self):
        label = "${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_HEADERS}@file,headers-none@file,${APP_TRAEFIK_AUTH}"
        f = self.rule(self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("twice: headers", f[0]["detail"])
        self.assertIn("out of order: limit → access → headers → headers → auth", f[0]["detail"])

    def test_an_empty_variable_is_named_as_what_disables_the_router(self):
        env = MODEL_ENV.replace("APP_TRAEFIK_LIMIT=limit-standard", "APP_TRAEFIK_LIMIT=")
        f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("missing limit", f[0]["detail"])
        self.assertIn("empty variable APP_TRAEFIK_LIMIT disables the router", f[0]["detail"])

    def test_a_variable_the_file_does_not_set_counts_as_empty(self):
        env = MODEL_ENV.replace("APP_TRAEFIK_AUTH=auth-none@file\n", "")
        f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("empty variable APP_TRAEFIK_AUTH", f[0]["detail"])

    def test_a_stacks_own_gate_fills_the_auth_position_through_its_variable(self):
        env = MODEL_ENV.replace("APP_TRAEFIK_AUTH=auth-none@file", "APP_TRAEFIK_AUTH=demo-auth@docker")
        f = self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)])
        self.assertEqual(f, [], f)

    def test_a_secondary_router_with_its_own_access_variable_is_judged_on_it(self):
        env = MODEL_ENV + "API_TRAEFIK_ACCESS=\n"
        label = "${API_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
        f = self.rule(self.findings(MODEL_ENV + "API_TRAEFIK_ACCESS=access-vpn\n",
                                    [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None),
                                     ("demo-api", "Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/api`)", label, None)]),
                      "router-positions")
        self.assertEqual(f, [])
        f = self.rule(self.findings(env, [("demo-api", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "router-positions")
        self.assertEqual(len(f), 1)
        self.assertIn("empty variable API_TRAEFIK_ACCESS", f[0]["detail"])


class BlockOrder(Scratch):
    def test_a_response_block_after_the_profile_is_reported(self):
        label = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,hsts-include-subdomains@file,${APP_TRAEFIK_AUTH}"
        f = self.rule(self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "block-order")
        self.assertEqual(len(f), 1, f)
        self.assertEqual(f[0]["level"], "WARN")
        self.assertIn("hsts-include-subdomains stands after the headers profile", f[0]["detail"])

    def test_a_response_block_before_the_profile_passes(self):
        label = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,frame-self@file,header-permissions@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH},forwarded-proto-https@file"
        f = self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)])
        self.assertEqual(f, [], f)

    def test_a_request_block_before_the_auth_position_is_reported(self):
        label = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,forwarded-proto-https@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
        f = self.rule(self.findings(MODEL_ENV, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "block-order")
        self.assertEqual(len(f), 1, f)
        self.assertIn("forwarded-proto-https stands before the auth position", f[0]["detail"])


class BurstExposure(Scratch):
    def test_the_wide_bucket_behind_a_public_policy_fails(self):
        env = MODEL_ENV.replace("limit-standard", "limit-extra-large")
        f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)]), "burst-exposure")
        self.assertEqual(len(f), 1, f)
        self.assertEqual(f[0]["level"], "FAIL")
        self.assertIn("limit-extra-large", f[0]["detail"])
        self.assertIn("found 'access-public'", f[0]["detail"])

    def test_the_wide_bucket_behind_each_closed_policy_passes(self):
        for access in ("access-lan", "access-vpn", "access-lan-vpn", "access-blocked"):
            env = MODEL_ENV.replace("limit-standard", "limit-extra-large").replace("access-public", access)
            f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, None)]), "burst-exposure")
            self.assertEqual(f, [], access)

    def test_the_old_xl_chain_is_judged_the_same_way(self):
        label = "${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
        env = OLD_ENV.replace("sec-2", "sec-2-spa-xl")
        f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "burst-exposure")
        self.assertEqual(len(f), 1, f)
        self.assertIn("sec-2-spa-xl", f[0]["detail"])
        for access in ("acc-private", "acc-tailscale", "acc-deny"):
            f = self.rule(self.findings(env.replace("acc-public", access),
                                        [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "burst-exposure")
            self.assertEqual(f, [], access)

    def test_the_wide_bucket_without_any_access_position_fails(self):
        label = "${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
        env = MODEL_ENV.replace("limit-standard", "limit-extra-large")
        f = self.rule(self.findings(env, [("demo", "Host(`${APP_TRAEFIK_HOST}`)", label, None)]), "burst-exposure")
        self.assertEqual(len(f), 1, f)
        self.assertIn("found 'none'", f[0]["detail"])


class TlsConflict(Scratch):
    def test_two_routers_on_one_host_with_different_options_are_reported(self):
        f = self.rule(self.findings(MODEL_ENV, [
            ("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, "tls-strict@file"),
            ("demo-api", "Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/api`)", MODEL_LABEL, None),
        ]), "tls-conflict")
        self.assertEqual(len(f), 1, f)
        self.assertEqual(f[0]["level"], cs.MODEL_LEVEL)
        self.assertIn("demo.example.com is served with different tls.options", f[0]["detail"])
        self.assertIn("default: demo-api", f[0]["detail"])
        self.assertIn("tls-strict@file: demo", f[0]["detail"])

    def test_the_same_option_on_both_passes(self):
        env = MODEL_ENV + "APP_TRAEFIK_TLS_OPTION=tls-strict\n"
        f = self.rule(self.findings(env, [
            ("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, "${APP_TRAEFIK_TLS_OPTION}@file"),
            ("demo-api", "Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/api`)", MODEL_LABEL, "${APP_TRAEFIK_TLS_OPTION}@file"),
        ]), "tls-conflict")
        self.assertEqual(f, [])

    def test_different_hosts_may_name_different_options(self):
        env = MODEL_ENV + "UI_TRAEFIK_HOST=ui.example.com\n"
        f = self.rule(self.findings(env, [
            ("demo", "Host(`${APP_TRAEFIK_HOST}`)", MODEL_LABEL, "tls-strict@file"),
            ("demo-ui", "Host(`${UI_TRAEFIK_HOST}`)", MODEL_LABEL, None),
        ]), "tls-conflict")
        self.assertEqual(f, [])


class Repository(unittest.TestCase):
    """What the rules say about the tree as it is: every router carries the
    four positions (Phase 4.3), no block is out of place, no stack serves a
    host name with two TLS options, and nothing exposes the wide bucket."""

    def test_the_tree_carries_the_model_on_every_router(self):
        cwd = os.getcwd()
        os.chdir(cs.Path(__file__).resolve().parents[2])
        try:
            cs.repository_files.cache_clear()
            cs.canonical_shared_network.cache_clear()
            levels = {}
            for app in cs.find_apps():
                out = []
                cs.check_routers(app, out)
                for f in out:
                    levels.setdefault(f["rule"], set()).add(f["level"])
        finally:
            os.chdir(cwd)
        self.assertEqual(levels, {}, levels)


if __name__ == "__main__":
    unittest.main()
