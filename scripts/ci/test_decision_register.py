#!/usr/bin/env python3
"""Tests for decision-register.py.

The register at the top of `.ai/decisions.md` is generated from the ID heading
and the field lines of each entry. These tests hold the grammar and the
derivations in place: a valid fixture renders deterministically; a missing
field, a word outside the vocabulary, a duplicated id, a relation into the
void and a part suffix that Parts does not name are each reported under their
rule; and a block that no longer matches the entries is `stale-register`.

Run:
    python3 scripts/ci/test_decision_register.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("decision_register", HERE / "decision-register.py")
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)


INTRO = """# Decisions

Architecture and governance decisions with their reasoning, newest first.

---

"""

NEW = """## 2026-10-18 · The model as cut: two decisions (D1–D2)

### DEC-003

- **Decision:** decided 2026-10-18 · supersedes DEC-002 · depends on DEC-001 · answers review D1–D2 · area: reverse-proxy
- **Parts:** .1 threat on the entrypoint · .2 four positions on every router
- **Implementation:** implemented 2026-10-23 (#258) → core/traefik/ops/templates/dynamic/model.yml.tmpl
- **Verification:** mechanical — scripts/ci/test_traefik_model.py · open — host: migration §5 · .2 open — the `429` count per public stack
- **Inputs:** docs/audits/traefik-architecture-review-2026-10-17.md §9

The reasoning of the entry stays as it was written.

---

"""

OLD = """## 2026-10-15 · The model: six functions

### DEC-002

- **Decision:** superseded 2026-10-18 by DEC-003 · area: reverse-proxy
- **Implementation:** n/a (never shipped as such)
- **Verification:** n/a

---

"""

BASE = """## 2026-10-15 · Cloudflare is a supported operating variant

### DEC-001

- **Decision:** decided 2026-10-15 (amended 2026-10-17: the mechanism changed) · answers core D3 · area: reverse-proxy
- **Implementation:** implemented 2026-10-17 (#238) → core/traefik/ops/templates/traefik.yml.tmpl
- **Verification:** mechanical — scripts/ci/test_traefik_forwarded_proxy.py · review — docs/reviews/phase-3-cloudflare-mode-review-2026-10-17.md · open — ten host checks

---

"""

UNCLASSIFIED = """## 2026-09-19 · Personal data on the public site

The entry has no id heading yet.

---
"""

VALID = INTRO + NEW + OLD + BASE + UNCLASSIFIED

# one Decision line, two parts that speak for themselves on Implementation only
PARTS = INTRO + """## 2026-10-23 · Two parts, one decision line

### DEC-001

- **Decision:** decided 2026-10-23 (amended 2026-10-25) · area: release
- **Parts:** .1 the tag · .2 the guard
- **Implementation:** .1 not started (the tag) · .2 implemented
- **Verification:** .2 mechanical — scripts/ci/test_check_prose.py

---
"""


def rules(problems):
    return sorted({p["rule"] for p in problems})


class ValidFixture(unittest.TestCase):
    def setUp(self):
        self.entries, self.unclassified, self.problems = dr.parse(VALID)

    def test_three_classified_one_not(self):
        self.assertEqual([e["id"] for e in sorted(self.entries, key=dr.sort_key)],
                         ["DEC-001", "DEC-002", "DEC-003"])
        self.assertEqual(len(self.unclassified), 1)
        # the only problem is the unclassified entry — a failure since the transition ended
        self.assertEqual(rules(self.problems), ["unclassified"])
        self.assertEqual(dr.level("unclassified"), "FAIL")

    def test_states_and_relations(self):
        new = next(e for e in self.entries if e["id"] == "DEC-003")
        self.assertEqual(dr.entry_state(new, "Decision"), "decided")
        self.assertEqual(dr.entry_state(new, "Implementation"), "implemented")
        self.assertEqual(new["area"], "reverse-proxy")
        self.assertEqual(new["parts"], {"1": "threat on the entrypoint",
                                        "2": "four positions on every router"})
        kinds = {(r["kind"], r["target"]) for r in new["relations"]}
        self.assertIn(("supersedes", "DEC-002"), kinds)
        self.assertIn(("depends on", "DEC-001"), kinds)
        self.assertIn(("answers", "review D1–D2"), kinds)
        old = next(e for e in self.entries if e["id"] == "DEC-002")
        self.assertEqual(dr.entry_state(old, "Decision"), "superseded")
        self.assertIn(("superseded by", "DEC-003"), {(r["kind"], r["target"]) for r in old["relations"]})

    def test_render_is_deterministic_and_derives_the_inverse(self):
        block = dr.render(self.entries, self.unclassified)
        self.assertEqual(block, dr.render(*dr.parse(VALID)[:2]))
        self.assertTrue(block.startswith(dr.START))
        self.assertTrue(block.endswith(dr.END))
        # filters: the entry's own gap once, a part's own gap once more, and a part
        # that says nothing of its own is not repeated
        self.assertIn("### Implemented, not verified on a host", block)
        self.assertIn("- **DEC-003** [The model as cut: two decisions (D1–D2)](#dec-003) · mechanical — scripts/ci/test_traefik_model.py · open — host: migration §5", block)
        self.assertIn("- **DEC-003.2** [The model as cut: two decisions (D1–D2)](#dec-003) · open — the `429` count per public stack", block)
        self.assertNotIn("- **DEC-003.1** [", block)
        self.assertIn("implemented and not verified on a host: 3", block)
        self.assertIn("- **DEC-001** [Cloudflare is a supported operating variant](#dec-001)", block)
        # relations grouped by kind, the inverse of `supersedes` not repeated where the
        # target already says `superseded by`
        self.assertIn("supersedes DEC-002 · depends on DEC-001 · answers review D1–D2", block)
        self.assertNotIn("superseded by DEC-003", block)
        self.assertIn("superseded 2026-10-18 by DEC-003", block)
        # chain, oldest to newest, head in bold
        self.assertIn("DEC-002 The model: six functions (2026-10-15) → **DEC-003 The model as cut: two decisions (D1–D2) (2026-10-18)**", block)
        # the inverse relation is derived at the target
        self.assertIn("needed by DEC-003", block)
        # the unclassified entry is listed without any state
        self.assertIn("### Not yet classified", block)
        self.assertIn("- Personal data on the public site — 2026-09-19", block)
        self.assertIn("Transition: 1 entry carries no field lines yet and is listed", block)

    def test_write_then_check_round_trips(self):
        block = dr.render(self.entries, self.unclassified)
        written = dr.with_block(VALID, block)
        # the block sits after the intro and before the first rule
        self.assertLess(written.find(dr.START), written.find("\n---\n"))
        self.assertEqual(dr.split_file(written)[1], block)
        # the entries are untouched
        self.assertIn(NEW, written)
        self.assertIn(OLD, written)
        # a second write replaces the block in place
        again = dr.with_block(written, block)
        self.assertEqual(again, written)
        # re-parsing the written file skips the block
        entries, unclassified, problems = dr.parse(written)
        self.assertEqual(len(entries), 3)
        self.assertEqual(rules(problems), ["unclassified"])


class PartsWithoutOwnDecisionToken(unittest.TestCase):
    def test_not_implemented_part_shows_the_entry_decision(self):
        entries, unclassified, problems = dr.parse(PARTS)
        self.assertEqual(problems, [])
        block = dr.render(entries, unclassified)
        self.assertIn("- **DEC-001.1** [Two parts, one decision line](#dec-001) · "
                      "decided 2026-10-23 (amended 2026-10-25) · not started (the tag)", block)
        self.assertNotIn("·  ·", block)


class Problems(unittest.TestCase):
    def test_missing_field(self):
        text = INTRO + NEW.replace("- **Verification:** mechanical — scripts/ci/test_traefik_model.py · open — host: migration §5 · .2 open — the `429` count per public stack\n", "") + OLD + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("missing-field", rules(problems))

    def test_unknown_state_and_area(self):
        text = INTRO + NEW.replace("implemented 2026-10-23", "done 2026-10-23").replace("area: reverse-proxy", "area: proxy", 1) + OLD + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("unknown-state", rules(problems))
        self.assertIn("unknown-area", rules(problems))
        self.assertEqual(dr.level("unknown-state"), "FAIL")

    def test_duplicate_id(self):
        text = INTRO + NEW + OLD.replace("### DEC-002", "### DEC-003") + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("duplicate-id", rules(problems))

    def test_dangling_relation_depends_on_transition(self):
        text = INTRO + NEW.replace("depends on DEC-001", "depends on DEC-009") + OLD + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("dangling-relation", rules(problems))
        # the transition is over: both rules fail, and the switch still reads the other way
        self.assertEqual(dr.TRANSITION, "fail")
        self.assertEqual(dr.level("dangling-relation"), "FAIL")
        self.assertEqual(dr.level("unclassified"), "FAIL")
        saved = dr.TRANSITION
        try:
            dr.TRANSITION = "warn"
            self.assertEqual(dr.level("dangling-relation"), "WARN")
            self.assertEqual(dr.level("unclassified"), "WARN")
        finally:
            dr.TRANSITION = saved

    def test_bad_part(self):
        text = INTRO + NEW.replace(".2 open — the `429` count", ".9 open — the `429` count") + OLD + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("bad-part", rules(problems))
        text = INTRO + NEW + OLD.replace("by DEC-003", "by DEC-003.7") + BASE
        _, _, problems = dr.parse(text)
        self.assertIn("bad-part", rules(problems))

    def test_no_entry_target_is_a_warning(self):
        text = INTRO + NEW + OLD.replace("by DEC-003", "by [no entry: commit 760d564]") + BASE
        entries, unclassified, problems = dr.parse(text)
        self.assertIn("no-entry-target", rules(problems))
        self.assertEqual(dr.level("no-entry-target"), "WARN")
        block = dr.render(entries, unclassified)
        self.assertIn("[no entry: commit 760d564]", block)

    def test_stale_register(self):
        entries, unclassified, _ = dr.parse(VALID)
        block = dr.render(entries, unclassified)
        written = dr.with_block(VALID, block)
        edited = written.replace("- **DEC-001** [", "- **DEC-001** hand-edited [", 1)
        self.assertNotEqual(dr.split_file(edited)[1], dr.render(*dr.parse(edited)[:2]))
        self.assertEqual(dr.split_file(written)[1], dr.render(*dr.parse(written)[:2]))


if __name__ == "__main__":
    unittest.main()
