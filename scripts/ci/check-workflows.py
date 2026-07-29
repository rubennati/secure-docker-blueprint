#!/usr/bin/env python3
"""
Workflow supply-chain checker for secure-docker-blueprint.

A GitHub Action referenced by tag is mutable. `@v7` is a branch-like pointer the
action's owner can move at any time, so a workflow that passes today can run
different code tomorrow — with the same repository permissions. Pinning to a
commit SHA is what makes a workflow run reproducible, and it is what the OpenSSF
Scorecard checks under Pinned-Dependencies.

This repository pinned by SHA everywhere except `site.yml`, which drifted back to
`@v7` unnoticed because nothing checked. That is the gap this closes.

FAIL:
  unpinned-action      `uses:` references a tag or branch instead of a 40-character
                       commit SHA
  missing-sha-comment  pinned correctly, but with no `# vX.Y.Z` comment — the SHA
                       alone tells a reader nothing about what version is running
  missing-permissions  no top-level `permissions:` block, so the workflow inherits
                       the repository default instead of declaring least privilege

Local actions (`uses: ./...`) and reusable workflows in this repository are
exempt: they are versioned by the commit that contains them.

Usage:
  python3 scripts/ci/check-workflows.py [github-summary-path]
"""

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)\s*(?:#\s*(.*))?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"v?\d+\.\d+(\.\d+)?|v\d+$")


def main() -> int:
    findings: list[dict] = []

    files = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    for wf in files:
        text = wf.read_text(encoding="utf-8", errors="replace")

        if not re.search(r"^permissions:", text, re.M):
            findings.append({
                "rule": "missing-permissions", "file": str(wf), "line": 1,
                "detail": "no top-level `permissions:` — the workflow inherits the "
                          "repository default instead of declaring least privilege",
            })

        for lineno, line in enumerate(text.splitlines(), 1):
            m = USES.match(line)
            if not m:
                continue
            ref, comment = m.group(1), (m.group(2) or "").strip()

            if ref.startswith("./") or ref.startswith(".github/"):
                continue

            _, _, version = ref.partition("@")
            if not SHA.match(version):
                findings.append({
                    "rule": "unpinned-action", "file": str(wf), "line": lineno,
                    "detail": f"`{ref}` is pinned to a mutable tag — use the commit "
                              "SHA with a `# vX.Y.Z` comment",
                })
                continue

            if not VERSION_COMMENT.search(comment):
                findings.append({
                    "rule": "missing-sha-comment", "file": str(wf), "line": lineno,
                    "detail": f"`{ref.split('@')[0]}` is SHA-pinned but carries no "
                              "version comment — nobody can tell what is running",
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

    uses_total = sum(
        1
        for w in files
        for line in w.read_text(encoding="utf-8", errors="replace").splitlines()
        if USES.match(line)
    )
    status = "❌" if findings else "✅"
    print(f"  {status} {len(files)} workflows  ·  {uses_total} action reference(s)  "
          f"·  {len(findings)} failure(s)")
    print()

    if len(sys.argv) > 1:
        lines = ["## Workflows\n",
                 f"{status} {len(files)} workflows, {uses_total} action references — "
                 f"**{len(findings)} failure(s)**\n"]
        if findings:
            lines += ["| Rule | File | Line | Detail |", "|---|---|---|---|"]
            lines += [f"| {f['rule']} | `{f['file']}` | {f['line']} | {f['detail']} |"
                      for f in findings]
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
