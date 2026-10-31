"""apps/seafile and apps/seafile-pro: the opt-in OnlyOffice overlay opens exactly
the two paths the Document Server uses, and nothing else of the instance.

seahub hands OnlyOffice two URLs, both at Seafile's public name: the document on
FILE_SERVER_ROOT + /files/<token>/<name>, which the Docker image serves under
/seafhttp, and the save callback on SERVICE_URL + /onlyoffice/editor-callback/
(seahub onlyoffice/utils.py, 13.0 and master). A closed access policy refuses
both from a container or another host (DEC-076), so the overlay carries one
router per path with access-public, the four positions and a priority above
the stack's catch-all router. This holds that shape for both stacks.

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
                    self.assertEqual(positions[0], "access-public@file")
                    self.assertEqual(positions[1], "${SIDE_TRAEFIK_LIMIT}@file")
                    self.assertEqual(positions[2], "${APP_TRAEFIK_HEADERS}@file")
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


if __name__ == "__main__":
    unittest.main()
