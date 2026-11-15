#!/usr/bin/env python3
"""tls-standard offers the post-quantum hybrid key exchange first.

A curvePreferences list replaces Go's default, which carries X25519MLKEM768;
without the entry tls-standard negotiated X25519 alone and refused a client
offering only the hybrid (measured with Traefik 3.7.17 and OpenSSL 3.5.9,
2026-11-15). Every name in the list must be one Traefik accepts: an unknown
name makes it refuse the whole TLS option.

Run:
    python3 scripts/ci/test_traefik_tls_profiles.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

# The names Traefik 3.7.17 maps in pkg/tls/certificate.go (CurveIDs).
TRAEFIK_CURVES = {
    "secp256r1", "CurveP256", "secp384r1", "CurveP384", "secp521r1", "CurveP521",
    "x25519", "X25519", "x25519mlkem768", "X25519MLKEM768",
    "secp256r1mlkem768", "SecP256r1MLKEM768", "secp384r1mlkem1024", "SecP384r1MLKEM1024",
}


class TlsStandardCurves(unittest.TestCase):

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(TRAEFIK / "ops", tmp / "ops")
        env = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com", TLS_DEFAULT_OPTION="tls-standard")
        (tmp / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        r = subprocess.run(["bash", str(tmp / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        doc = yaml.safe_load((tmp / "config/dynamic/tls-profiles.yml").read_text(encoding="utf-8"))
        self.options = doc["tls"]["options"]

    def test_the_hybrid_comes_first_and_the_classic_curves_stay(self):
        self.assertEqual(self.options["tls-standard"]["curvePreferences"],
                         ["X25519MLKEM768", "X25519", "CurveP256", "CurveP384"])

    def test_default_built_from_tls_standard_carries_the_same_list(self):
        self.assertEqual(self.options["default"]["curvePreferences"][0], "X25519MLKEM768")

    def test_every_curve_name_is_one_traefik_accepts(self):
        for name, option in self.options.items():
            for curve in option.get("curvePreferences") or []:
                with self.subTest(option=name, curve=curve):
                    self.assertIn(curve, TRAEFIK_CURVES)


if __name__ == "__main__":
    unittest.main()
