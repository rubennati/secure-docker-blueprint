#!/usr/bin/env python3
"""borgmatic's example names PostgreSQL's programs of one major per entry.

The host's `pg_dump` is the newest installed client. Its dump of an older server
did not restore into that server (Debian 13's 17 against postgres 16, step 8 lab
host), so every PostgreSQL entry of backup/borgmatic/config.yaml.example names
`pg_dump`, `pg_restore` and `psql` from the same /usr/lib/postgresql/<major>/bin.

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
    "pg_dump_command": "pg_dump",
    "pg_restore_command": "pg_restore",
    "psql_command": "psql",
}
PATH = re.compile(r"^/usr/lib/postgresql/(\d+)/bin/([a-z_]+)$")


def majors(entry):
    """The major of each named program; a problem string for anything else."""
    found, problems = {}, []
    for option, program in PROGRAMS.items():
        value = entry.get(option)
        m = PATH.match(value or "")
        if not m:
            problems.append(f"{option} is {value!r}, not /usr/lib/postgresql/<major>/bin/{program}")
        elif m.group(2) != program:
            problems.append(f"{option} runs {m.group(2)}, not {program}")
        else:
            found[option] = m.group(1)
    if len(set(found.values())) > 1:
        problems.append(f"the programs come from different majors: {found}")
    return problems


class ShippedExample(unittest.TestCase):
    def test_every_postgresql_entry_names_one_major(self):
        config = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
        entries = config.get("postgresql_databases") or []
        self.assertTrue(entries, "the example has no postgresql_databases entry")
        for entry in entries:
            with self.subTest(database=entry.get("name")):
                self.assertEqual(majors(entry), [])


class Rule(unittest.TestCase):
    def entry(self, **commands):
        return {"name": "myapp", **commands}

    def test_an_entry_without_the_programs_is_refused(self):
        self.assertEqual(len(majors(self.entry())), 3)

    def test_the_program_on_the_path_is_refused(self):
        problems = majors(self.entry(
            pg_dump_command="pg_dump",
            pg_restore_command="/usr/lib/postgresql/16/bin/pg_restore",
            psql_command="/usr/lib/postgresql/16/bin/psql"))
        self.assertEqual(len(problems), 1)
        self.assertIn("pg_dump_command", problems[0])

    def test_mixed_majors_are_refused(self):
        problems = majors(self.entry(
            pg_dump_command="/usr/lib/postgresql/17/bin/pg_dump",
            pg_restore_command="/usr/lib/postgresql/16/bin/pg_restore",
            psql_command="/usr/lib/postgresql/16/bin/psql"))
        self.assertEqual(len(problems), 1)
        self.assertIn("different majors", problems[0])

    def test_a_swapped_program_is_refused(self):
        problems = majors(self.entry(
            pg_dump_command="/usr/lib/postgresql/16/bin/pg_dump",
            pg_restore_command="/usr/lib/postgresql/16/bin/psql",
            psql_command="/usr/lib/postgresql/16/bin/psql"))
        self.assertEqual(problems, ["pg_restore_command runs psql, not pg_restore"])

    def test_one_major_passes(self):
        self.assertEqual(majors(self.entry(
            pg_dump_command="/usr/lib/postgresql/16/bin/pg_dump",
            pg_restore_command="/usr/lib/postgresql/16/bin/pg_restore",
            psql_command="/usr/lib/postgresql/16/bin/psql")), [])


if __name__ == "__main__":
    unittest.main()
