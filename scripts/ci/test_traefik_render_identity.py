#!/usr/bin/env python3
"""What core/traefik renders for an unchanged .env is what v0.9.5 rendered —
except where a step of the ingress programme changed the model by decision.

The reference is the tagged release in the checkout: `git archive v0.9.5` of
core/traefik is rendered with the same .env, for the two shapes a deployment has
— IPv4-only and dual-stack — and the config/ trees are compared file by file.
Position 1 of model.yml is one decided difference (DEC-076, step 3:
access-trusted and access-trusted-vpn in place of access-lan and access-lan-vpn)
and the rendered edge-networks.yml the other (DEC-075, step 5); that region is cut out of both renders before the comparison and checked on its
own, and comment-only lines of model.yml are not compared; a step that changes
anything else, anywhere, fails here. A shallow
checkout without the tag skips, as the other tag-dependent tests do.

Run:
    python3 scripts/ci/test_traefik_render_identity.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import filecmp
import re
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


POSITION_1 = re.compile(r"    # -------- 1  access --------\n.*?(?=    # -------- 2  limit --------\n)", re.S)


COMMENT_LINE = re.compile(r"^[ \t]*#.*\n", re.M)


def _without_position_1(text: str) -> tuple[str, str]:
    """(the file without its access section and without comment-only lines, the access section).

    Comments carry no configuration; a step that renames a policy corrects the
    comments that name it wherever they stand, and that is not a change of what
    Traefik loads.
    """
    m = POSITION_1.search(text)
    if m is None:
        raise AssertionError("model.yml has no access section between the position markers")
    rest = text[:m.start()] + text[m.end():]
    return COMMENT_LINE.sub("", rest), m.group(0)


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

    STEP_5_FILE = "edge-networks.yml"  # DEC-075: rendered from EDGE_NETWORKS, new since step 5

    def _assert_identical(self, env: dict):
        a, b = _render(self.release, env), _render(self.head, env)
        self.assertIn(self.STEP_5_FILE, _tree(b), "step 5 renders the edge networks")
        self.assertEqual(_tree(a), [f for f in _tree(b) if f != self.STEP_5_FILE], "the set of rendered files changed")
        for rel in _tree(a):
            if rel == "dynamic/model.yml":
                rest_a, access_a = _without_position_1((a / rel).read_text(encoding="utf-8"))
                rest_b, access_b = _without_position_1((b / rel).read_text(encoding="utf-8"))
                self.assertEqual(rest_a, rest_b, f"{rel} differs from {REFERENCE_TAG} outside position 1")
                self.assertIn("    access-lan:", access_a)
                self.assertIn("    access-trusted:", access_b)
                self.assertNotIn("access-lan", access_b, "the LAN class is gone (DEC-076)")
                continue
            self.assertTrue(filecmp.cmp(a / rel, b / rel, shallow=False),
                            f"{rel} renders differently from {REFERENCE_TAG} for an unchanged .env")

    def test_shape_a_ipv4_only_renders_as_the_release(self):
        self._assert_identical(SHAPE_A)

    def test_shape_b_dual_stack_renders_as_the_release(self):
        self._assert_identical(SHAPE_B)


if __name__ == "__main__":
    unittest.main()
