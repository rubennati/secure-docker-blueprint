#!/usr/bin/env python3
"""Find the recurring formulations that make documentation read as commentary.

The rules are in docs/standards/writing-style.md. Nothing here judges whether a
file reads well — it matches an exact phrase list drawn from text that was in
this repository, and reports where those phrases occur.

Reader-facing files fail. Maintainer files warn, because a findings log has a
different job and its cleanup is not urgent — the register rules still apply
there, they are just not a merge gate yet.

Usage:
    scripts/ci/check-prose.py            # report
    scripts/ci/check-prose.py --hints    # with the suggested replacement
"""

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "archive", "inbox", "dist", ".astro"}

# The standard quotes each phrase in order to forbid it, which is the one file
# where the wording belongs. Nothing else is exempt.
SKIP_FILES = {
    "docs/standards/writing-style.md",
}

# phrase -> (category, what to write instead)
PHRASES: dict[str, tuple[str, str]] = {}


def add(category: str, hint: str, *phrases: str) -> None:
    for p in phrases:
        PHRASES[p.lower()] = (category, hint)


add("author's expectation",
    "state the measurement; the reader has no prior expectation to correct",
    "better than expected", "worse than expected", "it turns out",
    "surprises people", "on the reasoning that", "more than expected",
    "less than expected")

add("self-justification",
    "why the format was chosen belongs in CHANGELOG.md or docs/architecture.md",
    "deliberately not", "deliberately *not*", "which is the point",
    "that is the point", "the point is that", "is itself the statement",
    "rather than assumed", "which is the whole point")

add("dramatic emphasis",
    "give the fact and its consequence; ranking importance is the reader's job",
    "is the dangerous one", "deserve attention", "deserves attention",
    "the one to avoid", "worth naming", "and not close", "is the smoking gun",
    "is the whole question", "the one that actually")

add("stage direction",
    "write the sentence instead of announcing its shape",
    "the trade in one line", "in one line:", "the short version",
    "to read out of it", "worth stating once", "two things to read",
    "the useful version is", "put simply", "in short:")

add("aphorism",
    "say which check ran, against what, and what it does not cover",
    "ages badly", "is not the same one", "nothing more.", ", not protected",
    "proves that the searches ran")

add("software with intentions",
    "name the process and the call it makes",
    "tends to want to", "tells the user something", "nobody is looking",
    "nobody looked", "wants to know", "does not care")

add("evaluation in place of a value",
    "give the two facts and let the reader rank them",
    "genuinely better", "the interesting case", "is milder", "the weakest of",
    "worth knowing", "worth being precise", "worth stating", "is harmless,",
    "worth it, and not")

PUBLIC_ROOT = {
    "README.md", "CHANGELOG.md", "ROADMAP.md", "CONTRIBUTING.md", "SECURITY.md",
}
# UPSTREAM.md is deliberately absent: the standard assigns it to a maintainer
# upgrading the stack, and rationale is what it is for.
STACK_README = re.compile(
    r"^(core|apps|business|monitoring|backup)/[^/]+/README\.md$"
)


def audience(path: str) -> str:
    if path in PUBLIC_ROOT or STACK_README.match(path):
        return "reader-facing"
    if path.startswith("site/"):
        return "reader-facing"
    return "maintainer"


def scan() -> tuple[list[tuple], list[tuple]]:
    fails, warns = [], []
    for path in sorted(Path(".").rglob("*.md*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = str(path)
        if rel in SKIP_FILES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        in_code = False
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            low = line.lower()
            for phrase, (category, hint) in PHRASES.items():
                if phrase in low:
                    row = (rel, n, phrase, category, hint, line.strip())
                    (fails if audience(rel) == "reader-facing" else warns).append(row)
    return fails, warns


def report(rows: list[tuple], hints: bool) -> None:
    for rel, n, phrase, category, hint, text in rows:
        print(f"   {rel}:{n}  “{phrase}” — {category}")
        print(f"      {text[:110]}")
        if hints:
            print(f"      → {hint}")


def main() -> int:
    hints = "--hints" in sys.argv
    fails, warns = scan()

    if fails:
        print(f"❌ {len(fails)} in reader-facing files")
        report(fails, hints)
    if warns:
        print(f"\n🟡 {len(warns)} in maintainer files (not a gate)")
        report(warns, hints)

    total = len(fails) + len(warns)
    print(f"\n{'❌' if fails else '✅'} {total} phrase(s) · "
          f"{len(fails)} blocking · {len(warns)} warning(s)")
    if not hints and total:
        print("   run with --hints for the suggested replacement")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
