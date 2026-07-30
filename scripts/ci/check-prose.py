#!/usr/bin/env python3
"""Find the recurring formulations that make documentation read as commentary.

The rules are in docs/standards/writing-style.md. Nothing here judges whether a
file reads well — it matches an exact phrase list drawn from text that was in
this repository, and reports where those phrases occur.

Reader-facing files fail. Maintainer files warn, because a findings log has a
different job and its cleanup is not urgent — the register rules still apply
there, they are just not a merge gate.

`--changed-only` reports the same findings for the lines a diff touches, and
nothing else. That is what CI gates on: a file may carry older findings without
blocking a change, but a line this change writes has to meet the standard.

Usage:
    scripts/ci/check-prose.py                             # whole repository
    scripts/ci/check-prose.py --hints                     # with the suggested replacement
    scripts/ci/check-prose.py --changed-only --base REF   # only lines the diff touches
    PROSE_DIFF_BASE=REF scripts/ci/check-prose.py --changed-only

The base is required in `--changed-only`; there is no default, because guessing
one silently checks the wrong range. Locally, `--base HEAD` covers uncommitted
work. The diff is taken from the merge base of REF and HEAD, so a base branch
that has moved on does not drag unrelated commits into the range.
"""

import os
import re
import subprocess
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


def is_documentation(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.startswith(".md")


# Each of these starts its own unit. A heading, a table row, a thematic break or
# a tag line also ends there — joining one to the paragraph beneath it would
# assemble a sentence the author never wrote.
ALONE = re.compile(r"^\s*(\#{1,6}\s|\||(-{3,}|\*{3,}|_{3,})\s*$|<)")
# A list item and a block quote open a unit that its own continuation lines join:
# both wrap like any other prose.
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s")
QUOTE = re.compile(r"^\s*>")


def prose_units(lines: list[str]) -> list[list[tuple[int, str]]]:
    """Consecutive lines that form one piece of prose, as the author wrote it.

    Markdown wraps a sentence at whatever column suits the editor, so a phrase
    can sit across two lines while belonging to one paragraph — or to one list
    item. Matching per line misses exactly those. A unit continues while the
    following line belongs to the same piece: plain prose continues a paragraph,
    an indented line continues a list item, and a `>` line continues a quote.
    """
    units: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    kind = None          # None | "prose" | "list" | "quote"
    in_code = False

    def flush() -> None:
        nonlocal current, kind
        if current:
            units.append(current)
        current, kind = [], None

    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            flush()
            continue
        if in_code:
            continue
        if not line.strip():
            flush()
            continue

        if ALONE.match(line):
            flush()
            units.append([(n, line)])
            continue

        if LIST_ITEM.match(line):
            flush()                      # a new marker ends the previous item
            current, kind = [(n, line)], "list"
            continue

        if QUOTE.match(line):
            if kind != "quote":
                flush()
                kind = "quote"
            current.append((n, line.lstrip().lstrip(">").lstrip()))
            continue

        if kind == "quote":              # the quote ended at this line
            flush()
        if kind is None:
            kind = "prose"
        current.append((n, line))        # continues a paragraph or a list item
    flush()
    return units


def scan_file(path: Path, rel: str) -> list[tuple]:
    """Every phrase occurrence in one file, in source order.

    A row carries the line the phrase starts on and the set of lines it spans,
    so a wrapped match is still attributable to a diff.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    rows = []
    for unit in prose_units(lines):
        # Join with a single space and remember where each source line lands,
        # so a match offset maps back to the line the author typed.
        spans, parts, cursor = [], [], 0
        for n, line in enumerate([t[1] for t in unit], 0):
            text = line.strip()
            spans.append((cursor, cursor + len(text), unit[n][0]))
            parts.append(text)
            cursor += len(text) + 1
        joined = " ".join(parts)
        low = joined.lower()

        for phrase, (category, hint) in PHRASES.items():
            start = low.find(phrase)
            while start != -1:
                end = start + len(phrase)
                touched = [ln for a, b, ln in spans if a < end and b > start]
                first = touched[0] if touched else unit[0][0]
                excerpt = joined[max(0, start - 40):end + 40].strip()
                rows.append((rel, first, phrase, category, hint, excerpt,
                             frozenset(touched)))
                start = low.find(phrase, start + 1)
    rows.sort(key=lambda r: (r[1], r[2]))
    return rows


def split_by_audience(rows: list[tuple]) -> tuple[list[tuple], list[tuple]]:
    fails, warns = [], []
    for row in rows:
        (fails if audience(row[0]) == "reader-facing" else warns).append(row)
    return fails, warns


def scan() -> tuple[list[tuple], list[tuple]]:
    rows = []
    for path in sorted(Path(".").rglob("*.md*")):
        rel = str(path)
        if not is_documentation(path) or rel in SKIP_FILES:
            continue
        rows.extend(scan_file(path, rel))
    return split_by_audience(rows)


# ── differential mode ────────────────────────────────────────────────────────

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class GitError(RuntimeError):
    pass


def git(*args: str) -> str:
    """Run git without a shell, so paths with spaces stay intact."""
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"`git {' '.join(args)}` failed")
    return proc.stdout


def resolve_base(ref: str) -> str:
    """The commit the diff is taken from: the merge base of ref and HEAD."""
    try:
        sha = git("rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    except GitError:
        raise GitError(
            f"diff base {ref!r} is not a commit in this repository — "
            "pass --base <ref> or set PROSE_DIFF_BASE to one that is"
        )
    try:
        return git("merge-base", sha, "HEAD").strip()
    except GitError:
        print(f"   note: no merge base with HEAD, comparing against {ref} directly")
        return sha


def changed_documentation(base_sha: str) -> list[str]:
    """Documentation files added, copied, modified or renamed since base.

    Deletions are excluded by --diff-filter: a file that is gone has no line to
    check, and reading it would fail.
    """
    out = git("diff", "--name-only", "-z", "-M", "--diff-filter=ACMR", base_sha)
    return [p for p in out.split("\0") if p]


def untracked_documentation() -> list[str]:
    """Documentation git cannot see yet.

    `git diff` compares commits and tracked files, so a new file that has not
    been added is in no diff and would pass unexamined. In CI there are none;
    locally this is the file someone just created.
    """
    out = git("ls-files", "--others", "--exclude-standard", "-z")
    return [p for p in out.split("\0") if p and is_documentation(Path(p))]


def changed_lines(base_sha: str, rel: str) -> set[int]:
    """Line numbers on the new side of the diff for one file."""
    out = git("diff", "--unified=0", "--no-color", "-M", base_sha, "--", rel)
    touched: set[int] = set()
    for line in out.splitlines():
        m = HUNK.match(line)
        if m:
            start = int(m.group(1))
            count = 1 if m.group(2) is None else int(m.group(2))
            touched.update(range(start, start + count))
    return touched


def scan_changed(base_sha: str) -> tuple[list[tuple], list[tuple], list[tuple]]:
    rows, checked = [], []
    for rel in changed_documentation(base_sha):
        path = Path(rel)
        if not is_documentation(path) or rel in SKIP_FILES or not path.is_file():
            continue
        touched = changed_lines(base_sha, rel)
        if not touched:
            continue
        checked.append((rel, len(touched)))
        rows.extend(row for row in scan_file(path, rel) if row[6] & touched)
    fails, warns = split_by_audience(rows)
    return fails, warns, checked


def report(rows: list[tuple], hints: bool) -> None:
    for rel, n, phrase, category, hint, text, _lines in rows:
        print(f"   {rel}:{n}  “{phrase}” — {category}")
        print(f"      {text[:110]}")
        if hints:
            print(f"      → {hint}")


def base_from_args(argv: list[str]) -> str | None:
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            return argv[i + 1]
        return None
    return os.environ.get("PROSE_DIFF_BASE") or None


def run_changed_only(argv: list[str], hints: bool) -> int:
    ref = base_from_args(argv)
    if not ref:
        print("❌ --changed-only needs a diff base")
        print("   pass --base <ref>, or set PROSE_DIFF_BASE=<ref>")
        print("   locally, --base HEAD covers uncommitted work")
        return 2

    try:
        base_sha = resolve_base(ref)
        fails, warns, checked = scan_changed(base_sha)
        untracked = untracked_documentation()
    except GitError as exc:
        print(f"❌ {exc}")
        return 2

    print(f"Changed documentation since {base_sha[:12]} ({ref}):")
    for rel, count in checked:
        print(f"   {rel} — {count} changed line(s)")
    if not checked:
        print("   none")

    for rel in untracked:
        print(f"   {rel} — untracked, not in any diff; `git add` it to have it checked")

    if not checked:
        print("\n✅ no changed documentation lines in this diff")
        return 0

    if fails:
        print(f"\n❌ {len(fails)} on changed lines in reader-facing files")
        report(fails, hints)
    if warns:
        print(f"\n🟡 {len(warns)} on changed lines in maintainer files (not a gate)")
        report(warns, hints)

    total = len(fails) + len(warns)
    print(f"\n{'❌' if fails else '✅'} {total} phrase(s) on changed lines · "
          f"{len(fails)} blocking · {len(warns)} warning(s) · "
          f"{len(checked)} file(s) checked")
    if not hints and total:
        print("   run with --hints for the suggested replacement")
    print("   findings outside these lines are reported by a run without --changed-only")
    return 1 if fails else 0


def main() -> int:
    argv = sys.argv[1:]
    hints = "--hints" in argv
    if "--changed-only" in argv:
        return run_changed_only(argv, hints)

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
