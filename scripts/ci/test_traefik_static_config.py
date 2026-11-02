"""validate.sh compares the static configuration Traefik runs with config/traefik.yml.

Traefik reads its static configuration once, at the start of the container.
render.sh replaces config/traefik.yml, and the running container keeps the file
it started with until it is recreated — a plain `docker compose up -d` does not
do that. Step 8 host run: after switching the entrypoint bouncer on and a plain
`up -d`, --strict reported the bouncer present while the running Traefik had no
plugin. validate.sh now reads the file inside the container: a difference, or a
change after the start, is PENDING; what cannot be read is NOT VERIFIED. Both
fail --strict and never read as verified.

Run:
    python3 scripts/ci/test_traefik_static_config.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK  # noqa: E402

VALID_ENV = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")
STARTED = "2026-11-01T10:00:00.123456789Z"
BEFORE, AFTER = "1793527190", "1793527300"  # 09:59:50 and 10:01:40 UTC that day


class StaticConfiguration(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parents[1] / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")
        self.render(VALID_ENV)
        self.stub_bin = tmp / "bin"
        self.stub_bin.mkdir()
        self.running = tmp / "running.yml"

    def render(self, env):
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        r = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def validate(self, *args, running="true", started=STARTED, mtime=BEFORE, readable=True, docker=True):
        """validate.sh with a stub docker: the fixture container runs (or not),
        started at `started`, and holds self.running as its static file with
        the time `mtime`. The copy has no docker-compose.yml, so the
        published-address checks stay NOT VERIFIED — the assertions read the
        static-configuration lines."""
        stub = self.stub_bin / "docker"
        if docker:
            cat = f'cat "{self.running}"' if readable else "exit 1"
            stat = f"echo {mtime}" if readable else "exit 1"
            stub.write_text(f"""#!/usr/bin/env bash
case "$1" in
  info) exit 0 ;;
  ps) exit 0 ;;
  inspect)
    case "$*" in
      *State.Running*) [ "{running}" = absent ] && exit 1; echo "{running} {started}" ;;
      *) echo "proxy-public " ;;
    esac ;;
  exec) case "$3" in cat) {cat} ;; stat) {stat} ;; esac ;;
  compose) [ "$2" = version ] && echo 2.40.0 ;;
esac
exit 0
""", encoding="utf-8")
        else:
            # the CLI is installed, the daemon does not answer
            stub.write_text('#!/usr/bin/env bash\n[ "$1 $2" = "compose version" ] && echo 2.40.0 && exit 0\nexit 1\n',
                            encoding="utf-8")
        stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{self.stub_bin}:{os.environ['PATH']}")
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh"), *args],
                              capture_output=True, text=True, env=env)

    def started_with_the_rendered_file(self):
        shutil.copy(self.root / "config" / "traefik.yml", self.running)

    def test_the_rendered_file_traefik_started_with_reports_nothing(self):
        self.started_with_the_rendered_file()
        r = self.validate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("static configuration", r.stdout)
        self.assertNotIn("config/traefik.yml was changed", r.stdout)

    def test_a_plugin_rendered_after_the_start_is_pending_and_fails_strict(self):
        # The host run: the bouncer switched on and rendered, Traefik not recreated.
        self.started_with_the_rendered_file()
        self.render(dict(VALID_ENV, CROWDSEC_BOUNCER_ENABLED="true", CROWDSEC_BOUNCER_KEY="k" * 32))
        self.assertIn("plugin", (self.root / "config" / "traefik.yml").read_text(encoding="utf-8"))
        r = self.validate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PENDING: config/traefik.yml differs from the static configuration traefik-core-fixture started with", r.stdout)
        self.assertIn("--force-recreate traefik", r.stdout)
        self.assertIn("SECURITY NOT CONFIRMED", r.stdout)
        r = self.validate("--strict")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("PENDING: config/traefik.yml differs", r.stdout)

    def test_an_edit_in_place_after_the_start_is_pending(self):
        # Same content inside the container, but written after Traefik read it.
        self.started_with_the_rendered_file()
        r = self.validate(mtime=AFTER)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PENDING: config/traefik.yml was changed after traefik-core-fixture started", r.stdout)
        self.assertEqual(self.validate("--strict", mtime=AFTER).returncode, 1)

    def test_a_file_that_cannot_be_read_in_the_container_is_not_verified(self):
        r = self.validate(readable=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOT VERIFIED: /etc/traefik/traefik.yml could not be read in traefik-core-fixture", r.stdout)
        self.assertEqual(self.validate("--strict", readable=False).returncode, 1)

    def test_a_start_time_that_cannot_be_read_is_not_verified(self):
        self.started_with_the_rendered_file()
        r = self.validate(started="not-a-time")
        self.assertIn("NOT VERIFIED: the start of traefik-core-fixture or the time of /etc/traefik/traefik.yml could not be read", r.stdout)
        self.assertEqual(self.validate("--strict", started="not-a-time").returncode, 1)

    def test_a_stopped_or_missing_container_is_not_verified(self):
        for running in ("false", "absent"):
            r = self.validate(running=running)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("NOT VERIFIED: traefik-core-fixture is not running — the static configuration it runs was not compared", r.stdout)
            self.assertEqual(self.validate("--strict", running=running).returncode, 1)

    def test_docker_that_does_not_answer_is_not_verified(self):
        r = self.validate(docker=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOT VERIFIED: the static configuration Traefik runs was not compared with config/traefik.yml (Docker did not answer here)", r.stdout)
        self.assertEqual(self.validate("--strict", docker=False).returncode, 1)


if __name__ == "__main__":
    unittest.main()
