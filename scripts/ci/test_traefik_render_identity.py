#!/usr/bin/env python3
"""An installation that declares nothing new renders exactly what v0.9.5 rendered.

The ingress programme (DEC-075 to DEC-078) changes what core/traefik renders for
an installation that declares the new variables. An existing installation does
not declare them, and its rendered configuration — traefik.yml, every file under
dynamic/, the HAProxy template — must stay byte-identical to the release it runs,
in both shapes a deployment has today:

  A  IPv4-only: docker-compose.yml alone, no subnets, no overlay
  B  dual-stack: COMPOSE_FILE with network-dual-stack.yml, both subnets, TRAEFIK_BIND_V6

The reference is the tagged release in the checkout: `git archive v0.9.5` of
core/traefik is rendered with the same .env, and the two config/ trees are
compared file by file. A shallow checkout without the tag skips, as the other
tag-dependent tests do; CI fetches tags.

Run:
    python3 scripts/ci/test_traefik_render_identity.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import filecmp
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

REPO = Path(__file__).resolve().parents[2]
REFERENCE_TAG = "v0.9.5"

SHAPE_A = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")
SHAPE_B = dict(SHAPE_A,
               COMPOSE_FILE="docker-compose.yml:network-dual-stack.yml",
               PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16",
               PUBLIC_NETWORK_SUBNET_V6="fd3a:91c2:7e04::/64",
               TRAEFIK_BIND_V4="0.0.0.0",
               TRAEFIK_BIND_V6="[::]")


def _render(root: Path, env: dict) -> Path:
    (root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
    r = subprocess.run(["bash", str(root / "ops/scripts/render.sh")], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)
    return root / "config"


def _tree(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())


class RenderIdentity(unittest.TestCase):
    def setUp(self):
        r = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", REFERENCE_TAG, "core/traefik"],
                           capture_output=True)
        if r.returncode != 0:
            self.skipTest(f"tag {REFERENCE_TAG} not in this checkout")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        with tarfile.open(fileobj=BytesIO(r.stdout)) as tar:
            tar.extractall(self.tmp / "release", filter="data")
        self.release = self.tmp / "release" / "core" / "traefik"
        self.head = self.tmp / "head" / "core" / "traefik"
        shutil.copytree(TRAEFIK, self.head, ignore=shutil.ignore_patterns(".env", "volumes"))

    def _assert_identical(self, env: dict):
        a, b = _render(self.release, env), _render(self.head, env)
        self.assertEqual(_tree(a), _tree(b), "the set of rendered files changed")
        for rel in _tree(a):
            self.assertTrue(filecmp.cmp(a / rel, b / rel, shallow=False),
                            f"{rel} renders differently from {REFERENCE_TAG} for an .env that declares nothing new")

    def test_shape_a_ipv4_only_renders_as_the_release(self):
        self._assert_identical(SHAPE_A)

    def test_shape_b_dual_stack_renders_as_the_release(self):
        self._assert_identical(SHAPE_B)


if __name__ == "__main__":
    unittest.main()
