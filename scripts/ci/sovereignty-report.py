#!/usr/bin/env python3
"""Collect licence and origin from every UPSTREAM.md into one machine-readable file.

Both facts already live in the stacks — `- **License:**` and `- **Origin:**` in
the Source block. What was missing is a view: nothing in the repository could
answer "which of these are EU-governed, and which are not actually open source"
without opening fifty-one files.

So this reads the owners rather than restating them. The site imports the JSON;
`--check` fails CI when the generated file is stale or when a stack has dropped
either field, which is what stops the gaps from quietly coming back.

Deliberately *not* a score. A number would compress "AGPL, German GmbH" and
"BSL, no stated jurisdiction" onto one axis and invite an argument about the
weighting instead of about the facts. The facts are what get published.

Usage:
    scripts/ci/sovereignty-report.py            # write the JSON
    scripts/ci/sovereignty-report.py --check    # verify it is current and complete
"""

import json
import re
import sys
from pathlib import Path

CATEGORIES = ["core", "apps", "business", "monitoring", "backup"]
EXCEPT = {"apps/_reference": "the canonical reference itself"}

OUT = Path("site/src/data/sovereignty.json")

# OSI-approved, in the spellings this repository uses. Anything outside this set
# is reported as source-available or proprietary rather than silently counted as
# open source — the distinction is the whole point of publishing the field.
OSI = {
    "AGPL-3.0", "AGPL-3.0-or-later", "Apache-2.0", "BSD 3-Clause",
    "GPL-2.0", "GPL-3.0", "GPL-3.0-or-later", "GNU GPL v3.0",
    "MIT", "MPL-2.0", "zlib",
}

# Licences that ship source but restrict use. Matched as a substring, because
# these are the ones that carry a qualifying clause after the name.
SOURCE_AVAILABLE = ("BSL", "Business Source", "Elastic License", "Sustainable Use")

PROPRIETARY = ("Commercial", "EULA")


def stacks() -> list[tuple[str, Path]]:
    """Every stack carrying an UPSTREAM.md, as (key, path)."""
    found = []
    for category in CATEGORIES:
        cat = Path(category)
        if not cat.is_dir():
            continue
        for stack in sorted(p for p in cat.iterdir() if p.is_dir()):
            key = f"{category}/{stack.name}"
            if key in EXCEPT or not (stack / "UPSTREAM.md").is_file():
                continue
            found.append((key, stack / "UPSTREAM.md"))
    return found


def field(text: str, name: str) -> str:
    m = re.search(rf"^- \*\*{name}:\*\* (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def classify_licence(value: str) -> str:
    """osi | source-available | proprietary | mixed | unknown."""
    if not value or "__REPLACE_ME__" in value:
        return "unknown"
    # The name before any qualifier: "MIT (core; …)" → "MIT".
    head = re.split(r"[(\[—]", value, maxsplit=1)[0].strip().rstrip(",.")
    if any(s in value for s in SOURCE_AVAILABLE):
        return "source-available"
    if any(p in value for p in PROPRIETARY):
        # "EULA (Ubiquiti) / GPL-3 (LSIO scripts)" is genuinely both.
        return "mixed" if "/" in value else "proprietary"
    if "/" in head and head.split("/")[0].strip() in OSI:
        return "mixed"
    if head in OSI or head.split(" or ")[0].strip() in OSI:
        # "MIT (core; some features under a separate enterprise licence)"
        return "mixed" if "enterprise" in value.lower() else "osi"
    return "unknown"


def classify_bloc(origin: str) -> str:
    """EU | non-EU | none | unknown — read from the origin string's last segment."""
    if not origin or "__REPLACE_ME__" in origin:
        return "unknown"
    if "no single jurisdiction" in origin or "no country" in origin:
        return "none"
    # non-EU must be tested first; it contains "EU".
    if "non-EU" in origin:
        return "non-EU"
    if re.search(r"\bEU\b", origin):
        return "EU"
    return "unknown"


def split_origin(origin: str) -> tuple[str, str]:
    """(country, entity) — best effort; the full string stays authoritative."""
    parts = [p.strip() for p in origin.split("·")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", origin


def collect() -> tuple[dict, list[str]]:
    rows, problems = {}, []
    for key, path in stacks():
        text = path.read_text(encoding="utf-8")
        licence, origin = field(text, "License"), field(text, "Origin")

        for name, value in (("License", licence), ("Origin", origin)):
            if not value:
                problems.append(f"{key}: UPSTREAM.md has no `- **{name}:**` field")

        lic_class, bloc = classify_licence(licence), classify_bloc(origin)
        for name, value, raw in (("licence", lic_class, licence), ("bloc", bloc, origin)):
            if value == "unknown" and raw:
                problems.append(f"{key}: {name} not recognised — {raw!r}")

        country, entity = split_origin(origin)
        rows[key] = {
            "license": licence,
            "license_class": lic_class,
            "origin": origin,
            "country": country,
            "entity": entity,
            "bloc": bloc,
        }
    return rows, problems


def main() -> int:
    check = "--check" in sys.argv
    rows, problems = collect()
    payload = json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != payload:
            problems.append(
                f"{OUT} is stale — run scripts/ci/sovereignty-report.py"
            )
        if problems:
            print("❌ sovereignty report")
            for p in problems:
                print(f"   {p}")
            return 1
        eu = sum(1 for r in rows.values() if r["bloc"] == "EU")
        osi = sum(1 for r in rows.values() if r["license_class"] == "osi")
        print(f"✅ {len(rows)} stacks · {eu} EU · {osi} OSI-licensed · 0 gaps")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    print(f"✅ wrote {OUT} — {len(rows)} stacks")
    for p in problems:
        print(f"   ⚠️  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
