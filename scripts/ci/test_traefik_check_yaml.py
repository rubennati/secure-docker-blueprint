"""ops/scripts/check-yaml.py: a rendered file Traefik would reject is refused.

A duplicated key in config/dynamic/crowdsec.yml took every @file middleware
and TLS option with it at Traefik's next start (step 8 lab host); PyYAML alone
would have kept the second value without a word. render.sh runs the check on
everything it writes, so every test that renders also checks the shipped
templates.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[2] / "core/traefik/ops/scripts/check-yaml.py"


def run(*texts):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for i, text in enumerate(texts):
            p = Path(d) / f"f{i}.yml"
            p.write_text(text)
            paths.append(str(p))
        return subprocess.run([sys.executable, str(CHECK), *paths], capture_output=True, text=True)


class CheckYaml(unittest.TestCase):
    def test_a_duplicated_key_is_refused(self):
        out = run("http:\n  middlewares:\n    m:\n      plugin:\n        bouncer:\n          updateMaxFailure: -1\n          updateMaxFailure: -1\n")
        self.assertEqual(out.returncode, 1)
        self.assertIn('mapping key "updateMaxFailure" already defined', out.stdout)

    def test_a_syntax_error_is_refused(self):
        self.assertEqual(run("a: [1\n").returncode, 1)

    def test_the_same_key_in_two_mappings_and_merge_keys_pass(self):
        out = run("tls: &t {minVersion: VersionTLS12}\noptions:\n  a:\n    <<: *t\n    sniStrict: true\n  b:\n    <<: *t\n    sniStrict: true\n")
        self.assertEqual(out.returncode, 0, out.stdout)


if __name__ == "__main__":
    unittest.main()
