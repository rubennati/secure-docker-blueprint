#!/usr/bin/env python3
"""Collect every stack's catalogue entry into one machine-readable file for the site.

The site had a hand-kept list of stacks and fell 48 behind. Each stack already owns
its facts in UPSTREAM.md — this adds two fields there, `Domain` and `Role`, and
reads the rest from the owners: the version and state from lifecycle.json, the name
from the README heading, the upstream link from the Source block.

`--check` fails CI when the generated file is stale, when a stack has no valid
domain or role, or when a stack directory has no entry. Nothing is retyped.

Usage:
    scripts/ci/site-catalogue.py            # write the JSON
    scripts/ci/site-catalogue.py --check    # verify it is current and complete
"""

import json
import re
import sys
from pathlib import Path

CATEGORIES = ["core", "apps", "business", "monitoring", "backup"]
EXCEPT = {"apps/_reference": "the canonical reference itself"}

OUT = Path("site/src/data/catalogue.json")
LIFECYCLE = Path("site/src/data/lifecycle.json")

# Grouping by what a reader wants done, independent of the directory a stack sits in.
DOMAINS = [
    "Infrastructure",
    "Identity, access and secrets",
    "Security operations",
    "AI and local AI",
    "Documents and e-signature",
    "Files, wiki and collaboration",
    "Photos",
    "Dashboards",
    "Publishing, forms and scheduling",
    "Automation and data",
    "Developer tools",
    "Business operations",
    "Monitoring",
    "Backup",
]

ROLE_MAX = 140


def stacks() -> list[tuple[str, Path]]:
    """Every stack directory, as (key, path) — the same set the other checkers use."""
    found = []
    for category in CATEGORIES:
        cat = Path(category)
        if not cat.is_dir():
            continue
        for stack in sorted(p for p in cat.iterdir() if p.is_dir()):
            key = f"{category}/{stack.name}"
            if key in EXCEPT or not (stack / "UPSTREAM.md").is_file():
                continue
            found.append((key, stack))
    return found


def field(text: str, name: str) -> str:
    m = re.search(rf"^- \*\*{name}:\*\* (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def upstream_link(text: str) -> str | None:
    """First URL of the Source block — the lines before the licence."""
    head = text.split("- **License:**", 1)[0]
    m = re.search(r"https?://[^\s)`>]+", head)
    return m.group(0).rstrip(".,") if m else None


def title(stack: Path) -> str:
    readme = stack / "README.md"
    if readme.is_file():
        m = re.search(r"^# (.+)$", readme.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            return re.sub(r"\s*\(.*\)$", "", m.group(1)).strip()
    return stack.name


def version(life: dict, upstream: str) -> str:
    """The pinned tag, without a leading `v` and without the image name."""
    pinned = life.get("pinned", "")
    tag = pinned.split("=", 1)[1].strip() if "=" in pinned else ""
    if not tag:
        m = re.search(r"^- \*\*Based on version:\*\* `?([^`\n]+?)`?\s*$", upstream, re.MULTILINE)
        tag = m.group(1) if m else ""
    tag = tag.rsplit(":", 1)[-1]
    return re.sub(r"^v(?=\d)", "", tag)


def collect() -> tuple[dict, list[str]]:
    rows, problems = {}, []
    lifecycle = json.loads(LIFECYCLE.read_text(encoding="utf-8")) if LIFECYCLE.is_file() else {}
    for key, stack in stacks():
        text = (stack / "UPSTREAM.md").read_text(encoding="utf-8")
        domain, role = field(text, "Domain"), field(text, "Role")

        if not domain:
            problems.append(f"{key}: UPSTREAM.md has no `- **Domain:**` field")
        elif domain not in DOMAINS:
            problems.append(f"{key}: domain {domain!r} is not one of the {len(DOMAINS)} defined")
        if not role:
            problems.append(f"{key}: UPSTREAM.md has no `- **Role:**` field")
        elif len(role) > ROLE_MAX:
            problems.append(f"{key}: role is {len(role)} characters, limit {ROLE_MAX}")

        life = lifecycle.get(key, {})
        rows[key] = {
            "name": title(stack),
            "domain": domain,
            "role": role,
            "upstream": upstream_link(text),
            "version": version(life, text),
            "state": life.get("state", "scaffolded"),
            "verified": life.get("verified") if life.get("verified_anchored") and life.get("verified") not in (None, "—") else None,
            "verified_version": life.get("verified_version") or None,
            "path": key,
        }
    return rows, problems


def main() -> int:
    check = "--check" in sys.argv
    rows, problems = collect()
    payload = json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != payload:
            problems.append(f"{OUT} is stale — run scripts/ci/site-catalogue.py")
        if problems:
            print("❌ site catalogue")
            for p in problems:
                print(f"   {p}")
            return 1
        print(f"✅ {len(rows)} stacks · {len({r['domain'] for r in rows.values()})} domains · 0 gaps")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    print(f"✅ wrote {OUT} — {len(rows)} stacks")
    for p in problems:
        print(f"   ⚠️  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
