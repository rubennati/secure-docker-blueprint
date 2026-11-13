"""apps/seafile and apps/seafile-pro: the opt-in OnlyOffice overlay opens exactly
the two paths the Document Server uses, and nothing else of the instance.

seahub hands OnlyOffice two URLs, both at Seafile's public name: the document on
FILE_SERVER_ROOT + /files/<token>/<name>, which the Docker image serves under
/seafhttp, and the save callback on SERVICE_URL + /onlyoffice/editor-callback/
(seahub onlyoffice/utils.py, 13.0 and master). A closed access policy refuses
both from a container or another host (DEC-076), so the overlay carries one
router per path with access-public, the four positions and a priority above
the stack's catch-all router. This holds that shape for both stacks.

The other direction is apps/onlyoffice's `file-host-paths.yml`: the file host
fetches the edited file from the Document Server's /cache/files/ after the save
callback (seahub onlyoffice/views.py, requests.get on the callback's url) and
converts through /ConvertService.ashx, both at the server's public name. Behind
a closed policy the overlay opens exactly those two paths, and nothing else.

Run:
    python3 scripts/ci/test_onlyoffice_callback_overlay.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
STACKS = {"apps/seafile": "seafile", "apps/seafile-pro": "seafile-pro-app"}
PATHS = {"onlyoffice-files": "/seafhttp/files/", "onlyoffice-callback": "/onlyoffice/editor-callback"}
LABEL = re.compile(r"^traefik\.http\.routers\.\$\{COMPOSE_PROJECT_NAME\}-([a-z-]+)\.([a-z.]+)=(.*)$")


def routers(stack: str, service: str) -> dict[str, dict[str, str]]:
    data = yaml.safe_load((ROOT / stack / "onlyoffice-callback.yml").read_text(encoding="utf-8"))
    assert list(data["services"]) == [service], f"{stack}: the overlay extends {service} and nothing else"
    assert set(data["services"][service]) == {"labels"}, f"{stack}: labels only — no image, no network, no ports"
    found: dict[str, dict[str, str]] = {}
    for label in data["services"][service]["labels"]:
        m = LABEL.match(label)
        assert m, f"{stack}: every label is a router label of this project: {label}"
        found.setdefault(m.group(1), {})[m.group(2)] = m.group(3)
    return found


class OnlyOfficeOverlay(unittest.TestCase):
    def test_both_stacks_open_exactly_the_two_paths_the_document_server_uses(self):
        for stack, service in STACKS.items():
            with self.subTest(stack=stack):
                found = routers(stack, service)
                self.assertEqual(set(found), set(PATHS))
                for name, path in PATHS.items():
                    r = found[name]
                    self.assertEqual(r["rule"], f"Host(`${{APP_TRAEFIK_HOST}}`) && PathPrefix(`{path}`)")
                    self.assertEqual(r["entrypoints"], "websecure")
                    self.assertEqual(r["tls"], "true")
                    self.assertEqual(r["service"], "${COMPOSE_PROJECT_NAME}", "the stack's own service, not a new one")
                    self.assertGreater(int(r["priority"]), 0, "above the catch-all Host() router of the stack")
                    positions = r["middlewares"].split(",")
                    self.assertEqual(len(positions), 4, "the four positions")
                    self.assertEqual(positions[0], "${APP_TRAEFIK_HEADERS}@file")
                    self.assertEqual(positions[1], "access-public@file")
                    self.assertEqual(positions[2], "${SIDE_TRAEFIK_LIMIT}@file")
                    self.assertEqual(positions[3], "auth-none@file", "the token and the document key are the application's gate")

    def test_the_stacks_variables_exist_for_what_the_overlay_names(self):
        for stack in STACKS:
            env = (ROOT / stack / ".env.example").read_text(encoding="utf-8")
            for var in ("APP_TRAEFIK_HOST", "SIDE_TRAEFIK_LIMIT", "APP_TRAEFIK_HEADERS", "COMPOSE_PROJECT_NAME"):
                self.assertRegex(env, rf"(?m)^{var}=", f"{stack}: {var}")
            self.assertIn("onlyoffice-callback.yml", env, f"{stack}: the example names the overlay")

    def test_the_overlay_is_not_part_of_the_production_stack(self):
        for stack in STACKS:
            env = (ROOT / stack / ".env.example").read_text(encoding="utf-8")
            compose_file = re.search(r"(?m)^COMPOSE_FILE=(.*)$", env).group(1)
            self.assertNotIn("onlyoffice-callback.yml", compose_file, f"{stack}: opt-in, with OnlyOffice only")


DS = ROOT / "apps/onlyoffice"
DS_RULES = {
    "saved-files": "Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/cache/files/`)",
    "convert": "Host(`${APP_TRAEFIK_HOST}`) && Path(`/ConvertService.ashx`)",
}


class DocumentServerOverlay(unittest.TestCase):
    def routers(self) -> dict[str, dict[str, str]]:
        data = yaml.safe_load((DS / "file-host-paths.yml").read_text(encoding="utf-8"))
        self.assertEqual(list(data["services"]), ["onlyoffice-app"])
        self.assertEqual(set(data["services"]["onlyoffice-app"]), {"labels"}, "labels only")
        found: dict[str, dict[str, str]] = {}
        for label in data["services"]["onlyoffice-app"]["labels"]:
            m = LABEL.match(label)
            self.assertTrue(m, f"every label is a router label of this project: {label}")
            found.setdefault(m.group(1), {})[m.group(2)] = m.group(3)
        return found

    def test_opens_exactly_the_two_paths_the_file_host_calls(self):
        found = self.routers()
        self.assertEqual(set(found), set(DS_RULES))
        for name, rule in DS_RULES.items():
            with self.subTest(router=name):
                r = found[name]
                self.assertEqual(r["rule"], rule)
                self.assertEqual(r["entrypoints"], "websecure")
                self.assertEqual(r["tls"], "true")
                self.assertEqual(r["service"], "${COMPOSE_PROJECT_NAME}", "the stack's own service")
                self.assertGreater(int(r["priority"]), 0, "above the catch-all Host() router")
                chain = r["middlewares"].split(",")
                self.assertEqual(chain[1:5], ["${APP_TRAEFIK_HEADERS}@file", "access-public@file",
                                              "${APP_TRAEFIK_LIMIT}@file", "auth-none@file"],
                                 "the four positions: the signed link and the JWT are the server's gate")
                self.assertEqual(chain[0], "header-nosniff@file")
                self.assertEqual(chain[-1], "forwarded-proto-https@file")

    def test_the_base_router_keeps_the_stacks_policy_and_the_overlay_is_opt_in(self):
        base = (DS / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("${APP_TRAEFIK_ACCESS}@file", base)
        env = (DS / ".env.example").read_text(encoding="utf-8")
        self.assertIn("file-host-paths.yml", env, "the example names the overlay")
        self.assertNotRegex(env, r"(?m)^COMPOSE_FILE=.*file-host-paths\.yml")


if __name__ == "__main__":
    unittest.main()
