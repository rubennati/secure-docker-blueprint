#!/usr/bin/env python3
"""borgmatic's example runs PostgreSQL's own client inside the server's container.

A host client of another major cannot be trusted: Debian 13's pg_dump 17 refused
a PostgreSQL 18 server, and its dump of a 14 or 16 server did not restore. The
server's own client always matches (FA-03), so every PostgreSQL entry of
backup/borgmatic/config.yaml.example runs `pg_dump`, `pg_restore` and `psql`
through `docker exec` in one container — `-i` for the two that read the archive
from borgmatic — and carries no `container:` and no `password:`: the official
images trust the local socket.

Run:
    python3 scripts/ci/test_borgmatic_example.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "backup" / "borgmatic" / "config.yaml.example"
PROGRAMS = {
    "pg_dump_command": ("pg_dump", False),
    "pg_restore_command": ("pg_restore", True),
    "psql_command": ("psql", True),
}
COMMAND = re.compile(r"^docker exec (-i )?([A-Za-z0-9][A-Za-z0-9_.-]*) ([a-z_]+)$")


def problems(entry):
    """A problem string for every way the entry leaves the server's own client."""
    found, out = {}, []
    for option, (program, stdin) in PROGRAMS.items():
        value = entry.get(option)
        m = COMMAND.match(value or "")
        if not m:
            out.append(f"{option} is {value!r}, not 'docker exec <container> {program}'")
            continue
        if m.group(3) != program:
            out.append(f"{option} runs {m.group(3)}, not {program}")
        if bool(m.group(1)) != stdin:
            out.append(f"{option} {'needs' if stdin else 'takes no'} -i")
        found[option] = m.group(2)
    if len(set(found.values())) > 1:
        out.append(f"the programs run in different containers: {found}")
    for key in ("container", "password"):
        if key in entry:
            out.append(f"the entry sets {key}:, which the server's own client does not need")
    return out


class ShippedExample(unittest.TestCase):
    def test_every_postgresql_entry_runs_the_servers_own_client(self):
        config = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        entries = config.get("postgresql_databases") or []
        self.assertTrue(entries, "the example has no postgresql_databases entry")
        for entry in entries:
            with self.subTest(database=entry.get("name")):
                self.assertEqual(problems(entry), [])


class Rule(unittest.TestCase):
    def entry(self, **options):
        return {"name": "myapp", **options}

    def shipped(self, **override):
        options = {
            "pg_dump_command": "docker exec myapp-db pg_dump",
            "pg_restore_command": "docker exec -i myapp-db pg_restore",
            "psql_command": "docker exec -i myapp-db psql",
        }
        options.update(override)
        return self.entry(**options)

    def test_an_entry_without_the_programs_is_refused(self):
        self.assertEqual(len(problems(self.entry())), 3)

    def test_the_host_client_is_refused(self):
        found = problems(self.shipped(pg_dump_command="/usr/lib/postgresql/17/bin/pg_dump"))
        self.assertEqual(len(found), 1)
        self.assertIn("pg_dump_command", found[0])

    def test_different_containers_are_refused(self):
        found = problems(self.shipped(psql_command="docker exec -i other-db psql"))
        self.assertEqual(len(found), 1)
        self.assertIn("different containers", found[0])

    def test_a_swapped_program_is_refused(self):
        self.assertEqual(problems(self.shipped(pg_restore_command="docker exec -i myapp-db psql")),
                         ["pg_restore_command runs psql, not pg_restore"])

    def test_a_restore_without_stdin_is_refused(self):
        self.assertEqual(problems(self.shipped(pg_restore_command="docker exec myapp-db pg_restore")),
                         ["pg_restore_command needs -i"])

    def test_container_and_password_are_refused(self):
        entry = self.shipped()
        entry.update(container="myapp-db", password="secret")
        self.assertEqual(len(problems(entry)), 2)

    def test_the_shipped_form_passes(self):
        self.assertEqual(problems(self.shipped()), [])


if __name__ == "__main__":
    unittest.main()
