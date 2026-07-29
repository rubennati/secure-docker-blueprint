#!/usr/bin/env python3
"""
Coverage checker for secure-docker-blueprint.

Answers one question the other checkers structurally cannot: **is there content
in this repository that no checker looks at?**

Three coverage gaps surfaced within a single day, all found by accident:

  - `apps/seafile` and `apps/seafile-pro` split their compose across per-component
    files, so a discovery that keyed on `docker-compose.yml` never saw them —
    two ✅ stacks never checked for `:latest`, plaintext secrets or exposed
    datastores.
  - `backup/borgmatic` is host-installed and has no compose file at all.
  - The whole `backup` category was missing from `check-structure.py` ROOTS.

Each was fixed where it was found. The pattern is what this file addresses:
finding the next one by accident does not scale, so the check is inverted —
enumerate the content, then ask which checker claims it.

A directory counts as covered when **either** `check-structure.py` enumerates it
or `lifecycle-report.py` reports on it. Neither alone is enough: the structure
checker keys on compose files and so cannot see `backup/borgmatic`, which is
host-installed by design, while the lifecycle report covers it but checks nothing
about tags, secrets or network exposure.

FAIL (blocks CI — content nothing verifies):
  unchecked-dir     a directory under a stack root holds tracked files, and
                    neither checker enumerates it
  unknown-root      a tracked top-level directory is neither a stack root nor a
                    declared non-stack area

WARN (reported — worth a look, not a defect):
  structure-blind   covered by the lifecycle report but not by the structure
                    checker: no compose file, so tags, secrets and exposure are
                    verified by hand. Legitimate for host-installed components;
                    listed so the count cannot drift silently.

Usage:
  python3 scripts/ci/check-coverage.py [github-summary-path]
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Reuse the real discovery rather than restating it — a second copy of this list
# is exactly how `backup` went unchecked in the first place.
import importlib.util


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


structure = _load("check_structure", "check-structure.py")
lifecycle = _load("lifecycle_report", "lifecycle-report.py")

# Tracked top-level directories that hold no stacks, with what covers them.
NON_STACK_ROOTS = {
    ".ai": "AI working context — prose, reviewed by hand",
    ".cursor": "editor pointer file",
    ".github": "CI workflows and templates",
    "docs": "documentation — prose, reviewed by hand",
    "scripts": "the checkers themselves",
    "site": "operator site — built and deployed by .github/workflows/site.yml",
}

# Any tracked file makes a directory content. Keying on marker filenames instead
# is what let backup/borgmatic — README, restore playbook, config example, no
# compose — pass unnoticed by an earlier version of this very check.


def tracked_paths() -> list[Path]:
    """Every path git tracks — untracked scratch directories are not our problem."""
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [Path(line) for line in out.splitlines() if line]


def main() -> int:
    findings: list[dict] = []

    paths = tracked_paths()
    top_level = {p.parts[0] for p in paths if len(p.parts) > 1}

    # ── unknown-root: a tracked top-level directory nobody declared ──────────
    for name in sorted(top_level):
        if name in structure.ROOTS or name in NON_STACK_ROOTS:
            continue
        findings.append({
            "level": "FAIL",
            "rule": "unknown-root",
            "path": name,
            "detail": "tracked top-level directory in neither ROOTS nor NON_STACK_ROOTS "
                      "— add it to a checker or declare it here",
        })

    # ── unchecked-dir: content under a stack root that neither checker sees ──
    by_structure = {str(p) for p in structure.find_apps()}
    rows, _ = lifecycle.collect()
    by_lifecycle = {r["stack"] for r in rows}

    # Directories holding at least one tracked file, directly under a stack root.
    content_dirs: set[str] = set()
    for path in paths:
        if len(path.parts) < 3 or path.parts[0] not in structure.ROOTS:
            continue
        content_dirs.add(str(Path(path.parts[0]) / path.parts[1]))

    for directory in sorted(content_dirs):
        if directory in by_structure or directory in by_lifecycle:
            continue
        findings.append({
            "level": "FAIL",
            "rule": "unchecked-dir",
            "path": directory,
            "detail": "holds tracked files, but neither check-structure.py nor "
                      "lifecycle-report.py enumerates it",
        })

    # ── structure-blind: the lifecycle sees it, the structure checker cannot ─
    for directory in sorted(by_lifecycle - by_structure):
        findings.append({
            "level": "WARN",
            "rule": "structure-blind",
            "path": directory,
            "detail": "no compose file — tags, secrets and exposure are verified by "
                      "hand, not by check-structure.py",
        })

    # ── Console output ──────────────────────────────────────────────────────
    fails = sum(1 for f in findings if f["level"] == "FAIL")
    warns = sum(1 for f in findings if f["level"] == "WARN")

    by_rule: dict[str, list[dict]] = {}
    for f in findings:
        by_rule.setdefault(f["rule"], []).append(f)

    print()
    for level in ("FAIL", "WARN"):
        rules = {r: v for r, v in by_rule.items() if v[0]["level"] == level}
        if not rules:
            continue
        icon = "🔴" if level == "FAIL" else "🟡"
        for rule, items in sorted(rules.items(), key=lambda kv: -len(kv[1])):
            print(f"  {icon} {level}  {rule}  ({len(items)})")
            for f in items[:6]:
                print(f"       {f['path']}: {f['detail']}")
            if len(items) > 6:
                print(f"       … and {len(items) - 6} more")
        print()

    checked = len(structure.find_apps())
    declared = len(structure.ROOTS) + len(NON_STACK_ROOTS)
    status = "❌" if fails else "✅"
    print(
        f"  {status} {checked} stacks enumerated  ·  {declared} roots declared  "
        f"·  {fails} failure(s)  ·  {warns} warning(s)"
    )
    print()

    # ── GitHub Actions Job Summary ──────────────────────────────────────────
    if len(sys.argv) > 1:
        lines = ["## Coverage\n"]
        lines.append(
            f"{status} {checked} stacks enumerated across {declared} declared roots — "
            f"**{fails} failure(s)**, {warns} warning(s)\n"
        )
        if findings:
            lines.append("| Level | Rule | Path | Detail |")
            lines.append("|---|---|---|---|")
            for f in findings:
                icon = "🔴" if f["level"] == "FAIL" else "🟡"
                lines.append(
                    f"| {icon} {f['level']} | {f['rule']} | `{f['path']}` | {f['detail']} |"
                )
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
