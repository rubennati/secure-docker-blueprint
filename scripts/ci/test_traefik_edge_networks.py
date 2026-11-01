"""core/traefik renders the edge networks of the installed stacks (DEC-075, step 5).

EDGE_NETWORKS in .env, quoted and space-separated, names the network of every
installed stack — its TRAEFIK_NETWORK. render.sh writes config/edge-networks.yml,
a Compose file COMPOSE_FILE applies next to docker-compose.yml: Traefik joins and
creates each network, the stack declares it external. Unset stops the render,
empty means the shared network; a name Compose would refuse, a duplicate or one
of the stack's own networks is refused before Compose sees it, and validate.sh
refuses a rendered file that disagrees with the list.

Run:
    python3 scripts/ci/test_traefik_edge_networks.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK  # noqa: E402

VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")


class EdgeNetworks(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            shutil.copy(TRAEFIK / name, self.root / name)

    def _env(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")

    def render(self, env):
        self._env(env)
        return subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)

    def validate(self):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh")], capture_output=True, text=True)

    def rendered(self, env):
        r = self.render(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        path = self.root / "config" / "edge-networks.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8")), r.stdout

    def test_two_networks_are_joined_and_created(self):
        data, out = self.rendered(dict(VALID_ENV, EDGE_NETWORKS="nextcloud-edge vaultwarden-edge"))
        self.assertEqual(list(data["services"]["traefik"]["networks"]), ["nextcloud-edge", "vaultwarden-edge"])
        self.assertEqual(data["networks"]["nextcloud-edge"], {"name": "nextcloud-edge", "driver": "bridge"})
        self.assertEqual(data["networks"]["vaultwarden-edge"]["name"], "vaultwarden-edge")
        self.assertIn("2 edge network(s)", out)

    def test_empty_means_the_shared_network_and_a_file_compose_accepts(self):
        data, out = self.rendered(dict(VALID_ENV, EDGE_NETWORKS=""))
        self.assertEqual(data["services"]["traefik"]["networks"], {})
        self.assertEqual(data["networks"], {})
        self.assertIn("0 edge network(s)", out)

    @unittest.skipUnless(shutil.which("docker"), "docker compose is needed to merge the files")
    def test_compose_merges_the_rendered_file_with_the_base(self):
        for edges in ("", "nextcloud-edge vaultwarden-edge"):
            self.rendered(dict(VALID_ENV, EDGE_NETWORKS=edges))
            r = subprocess.run(["docker", "compose", "-f", "docker-compose.yml", "-f", "config/edge-networks.yml",
                                "config", "--format", "json"], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            nets = json.loads(r.stdout)["services"]["traefik"]["networks"]
            self.assertIn("public", nets)
            for e in edges.split():
                self.assertIn(e, nets)

    def test_unset_is_refused_by_render_and_validate(self):
        env = {k: v for k, v in VALID_ENV.items() if k != "EDGE_NETWORKS"}
        r = self.render(env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("EDGE_NETWORKS is not set", r.stdout + r.stderr)
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("EDGE_NETWORKS is not set", v.stdout + v.stderr)

    def test_a_name_compose_would_refuse_a_duplicate_and_the_shared_network_are_refused(self):
        for edges, message in (("-bad", "not a Docker network name"),
                               ("a-edge a-edge", "listed twice"),
                               (BASE_ENV["PUBLIC_NETWORK"], "already defines")):
            r = self.render(dict(VALID_ENV, EDGE_NETWORKS=edges))
            self.assertNotEqual(r.returncode, 0, edges)
            self.assertIn(message, r.stdout + r.stderr)

    def test_validate_refuses_a_rendered_file_that_disagrees_with_the_list(self):
        self.rendered(dict(VALID_ENV, EDGE_NETWORKS="nextcloud-edge"))
        self._env(dict(VALID_ENV, EDGE_NETWORKS="other-edge"))
        v = self.validate()
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("edge-networks.yml lists [nextcloud-edge ] but EDGE_NETWORKS says [other-edge ]", v.stdout)

    def test_the_example_ships_the_variable_and_applies_the_file(self):
        text = (TRAEFIK / ".env.example").read_text(encoding="utf-8")
        self.assertIn('\nEDGE_NETWORKS=""\n', text)
        self.assertIn("\nCOMPOSE_FILE=docker-compose.yml:config/edge-networks.yml\n", text)
        self.assertIn("config/edge-networks.yml", (TRAEFIK / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
