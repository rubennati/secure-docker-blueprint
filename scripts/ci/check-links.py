#!/usr/bin/env python3
"""
Internal link checker for secure-docker-blueprint.

Validates every relative link and heading anchor in the repository's Markdown.
External URLs are deliberately not fetched: they make CI fail for reasons that
have nothing to do with a commit, and a dead upstream link is a documentation
problem to notice, not a merge to block.

What it catches — both of which happen during ordinary refactors:

  broken-path      a link to a file or directory that does not exist
  broken-anchor    a link to a heading that does not exist in the target file

Anchors are resolved the way GitHub does: lowercase, spaces to hyphens, drop
everything that is not a letter, digit, hyphen or underscore. Emoji and inline
code in a heading are handled by that rule, so `## Backup` and
`## ✅ Ready Criteria` both resolve.

Absolute paths under site/ are routes for the static site generator, not
filesystem paths, and are skipped — an earlier ad-hoc version of this check
reported all 19 of them as broken.

Usage:
  python3 scripts/ci/check-links.py [github-summary-path]
"""

import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "archive", "inbox", "dist"}

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*```")


def slug(text: str) -> str:
    """GitHub's heading-anchor rule."""
    text = re.sub(r"`([^`]*)`", r"\1", text)          # inline code keeps its text
    text = re.sub(r"\*\*|\*|__|_", "", text)          # emphasis markers drop out
    text = text.strip().lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9\-_]", "", text)


def anchors_of(path: Path) -> set[str]:
    """Every heading anchor a file offers, with GitHub's duplicate suffixes."""
    found: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if not m:
            continue
        base = slug(m.group(2))
        if not base:
            continue
        n = seen.get(base, 0)
        seen[base] = n + 1
        found.add(base if n == 0 else f"{base}-{n}")
    return found


def markdown_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.md"],
                         capture_output=True, text=True, check=True).stdout
    return [Path(p) for p in out.splitlines()
            if p and not SKIP_DIRS & set(Path(p).parts)]


def main() -> int:
    findings: list[dict] = []
    anchor_cache: dict[Path, set[str]] = {}

    for md in markdown_files():
        in_fence = False
        for lineno, line in enumerate(
                md.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "tel:")):
                    continue
                # Site routes, not paths — resolved by the static site generator.
                if target.startswith("/"):
                    continue

                path_part, _, anchor = target.partition("#")

                if not path_part:                      # same-file anchor
                    dest = md
                else:
                    dest = (md.parent / path_part).resolve()
                    try:
                        dest = dest.relative_to(Path.cwd())
                    except ValueError:
                        continue                       # outside the repo, not ours
                    if not dest.exists():
                        findings.append({
                            "rule": "broken-path", "file": str(md), "line": lineno,
                            "detail": f"`{target}` — no such file or directory",
                        })
                        continue

                if not anchor or dest.suffix != ".md" or not dest.is_file():
                    continue
                if dest not in anchor_cache:
                    anchor_cache[dest] = anchors_of(dest)
                if slug(anchor) not in anchor_cache[dest]:
                    findings.append({
                        "rule": "broken-anchor", "file": str(md), "line": lineno,
                        "detail": f"`{target}` — `{dest}` has no heading `#{anchor}`",
                    })

    by_rule: dict[str, list[dict]] = {}
    for f in findings:
        by_rule.setdefault(f["rule"], []).append(f)

    print()
    for rule, items in sorted(by_rule.items(), key=lambda kv: -len(kv[1])):
        print(f"  🔴 FAIL  {rule}  ({len(items)})")
        for f in items[:10]:
            print(f"       {f['file']}:{f['line']}: {f['detail']}")
        if len(items) > 10:
            print(f"       … and {len(items) - 10} more")
        print()

    checked = len(markdown_files())
    status = "❌" if findings else "✅"
    print(f"  {status} {checked} files checked  ·  {len(findings)} broken link(s)")
    print()

    if len(sys.argv) > 1:
        lines = ["## Links\n",
                 f"{status} {checked} Markdown files — **{len(findings)} broken link(s)**\n"]
        if findings:
            lines += ["| Rule | File | Line | Detail |", "|---|---|---|---|"]
            lines += [f"| {f['rule']} | `{f['file']}` | {f['line']} | {f['detail']} |"
                      for f in findings]
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
