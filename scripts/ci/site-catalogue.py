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

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

# Compose discovery and parsing belong to check-structure.py. A second copy here
# would drift from the checker that decides which files are a stack's production
# set and which are opt-in overlays.
_spec = importlib.util.spec_from_file_location(
    "check_structure", Path(__file__).parent / "check-structure.py"
)
_structure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_structure)

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


# Images that mean a stack needs a piece of infrastructure beside the application.
# Matched as a substring of the image reference, so a registry prefix or a variant
# suffix does not hide it.
INFRASTRUCTURE = {
    "postgres": "PostgreSQL", "pgvector": "PostgreSQL", "pgautoupgrade": "PostgreSQL",
    "timescale": "PostgreSQL", "mariadb": "MariaDB", "mysql": "MySQL", "percona": "MySQL",
    "redis": "Redis", "valkey": "Valkey", "memcached": "Memcached",
    "minio": "object storage", "seaweedfs": "object storage",
    "elasticsearch": "Elasticsearch", "opensearch": "OpenSearch",
    "clickhouse": "ClickHouse", "rabbitmq": "RabbitMQ", "mongo": "MongoDB",
    "nats": "NATS", "kafka": "Kafka", "qdrant": "Qdrant", "weaviate": "Weaviate",
}


def _reserves_gpu(body: dict) -> bool:
    reservations = ((body.get("deploy") or {}).get("resources") or {}).get("reservations") or {}
    return bool(reservations.get("devices"))


# The maintained decision facts. Unlike the footprint these cannot be derived:
# what a licence permits, which features sit behind a paid edition and how money
# is asked for are answered by reading upstream's own terms.
#
# A field that is absent means **not researched** — never "nothing to declare".
# Filling all 91 stacks with a placeholder would be dormant configuration and
# would make the site imply an answer nobody looked up; a stack that was checked
# and gates nothing says so explicitly with `none`.
DECISION_FACTS = {
    "Use restrictions": "use_restrictions",
    "Edition gating": "edition_gating",
    "Commercial model": "commercial_model",
}

# Durable descriptions of how money is asked for. A price is deliberately not one
# of them: it moves, and an undated number in a repository is worse than none.
# Where the amount matters, the source link is where it is read.
COMMERCIAL_MODELS = {
    "free self-hosted", "no paid edition", "paid add-on", "paid self-hosted edition",
    "per-user subscription", "commercial licence", "quote only", "none",
}

# `<statement> — <source url> · checked YYYY-MM-DD`. Anchored at the end so an
# em dash inside the statement cannot be mistaken for the provenance separator.
PROVENANCE = re.compile(
    r"^(?P<statement>.+?)\s+—\s+(?P<source>https?://\S+)\s+·\s+checked\s+(?P<checked>\d{4}-\d{2}-\d{2})$"
)


# The per-stack research marker. Required on every stack, which is what stops a
# new one entering the repository with its W8 state unstated.
#
# It is a **process record, not a claim about upstream**: it says the three
# questions were asked on that day, so it carries no source. That is the whole
# difference between it and a `none` *fact*, which asserts something about
# someone else's terms and therefore does carry one. Without it the only way to
# say "asked, nothing worth recording" would be three `none` fields per stack,
# which is bookkeeping pretending to be knowledge.
CHECKED_FIELD = "Decision facts checked"
NOT_RESEARCHED = "not yet"


def decision_facts_checked(text: str, key: str, has_facts: bool, problems: list[str]) -> str | None:
    """The date the three questions were asked, or None when they have not been.

    Three states, told apart without padding any file:

      absent           → rejected; a stack may not leave its research state unsaid
      `not yet`        → nobody has looked
      a calendar date  → looked. Facts alongside it mean something was found;
                         none alongside it means nothing an operator decides on
    """
    raw = field(text, CHECKED_FIELD)
    if not raw:
        problems.append(
            f"{key}: UPSTREAM.md has no `- **{CHECKED_FIELD}:**` — give it a date "
            f"or `{NOT_RESEARCHED}`"
        )
        return None
    if raw == NOT_RESEARCHED:
        if has_facts:
            problems.append(
                f"{key}: {CHECKED_FIELD} says {NOT_RESEARCHED!r} but the stack records "
                "decision facts — date it instead"
            )
        return None
    try:
        date.fromisoformat(raw)
    except ValueError:
        problems.append(
            f"{key}: {CHECKED_FIELD} is {raw!r} — needs YYYY-MM-DD or {NOT_RESEARCHED!r}"
        )
        return None
    return raw


def decision_facts(text: str, key: str, problems: list[str]) -> dict:
    """The maintained facts a stack records, each with where it came from and when.

    Every fact carries its own source and date because they are checked at
    different times: a licence changes rarely, a pricing page often. A fact
    without both is rejected rather than published — an unsourced claim about
    someone else's terms is the thing this exists to prevent.

    The date is validated as a calendar date only. CI deliberately runs no
    time-based staleness math, so nothing here compares it against today; a
    fact going stale is a maintenance question, not a build failure.
    """
    out = {}
    for label, name in DECISION_FACTS.items():
        raw = field(text, label)
        if not raw:
            continue
        m = PROVENANCE.match(raw)
        if not m:
            problems.append(
                f"{key}: `- **{label}:**` needs `<statement> — <source url> · checked YYYY-MM-DD`"
            )
            continue
        try:
            date.fromisoformat(m.group("checked"))
        except ValueError:
            problems.append(f"{key}: {label} has no valid date — {m.group('checked')!r}")
            continue
        entry = {
            "statement": m.group("statement"),
            "source": m.group("source"),
            "checked": m.group("checked"),
        }
        if name == "commercial_model":
            # The vocabulary term is the leading clause; anything after `;` is a
            # qualifier the reader needs but the vocabulary should not grow for.
            term = entry["statement"].split(";")[0].strip()
            if term not in COMMERCIAL_MODELS:
                problems.append(
                    f"{key}: commercial model {term!r} is not one of "
                    f"{', '.join(sorted(COMMERCIAL_MODELS))}"
                )
                continue
            entry["model"] = term
        out[name] = entry
    return out


def footprint(production: list[Path], overlays: list[Path]) -> dict | None:
    """How much machinery a stack brings, read from its own compose files.

    Facts, not a verdict. Two products solving one problem at very different
    weights is a reason for both to exist here, not a reason to rank them: this
    is what separates a two-service stack with a MariaDB from a ten-service one
    with a database, a cache and workers, and it says nothing about which is
    better.

    **Memory is deliberately absent.** The compose files carry
    `deploy.resources.limits.memory`, which is the ceiling this repository sets
    on a service — not what the application needs. Publishing a configured limit
    as a RAM requirement would turn a policy into a fabricated fact about
    upstream. What upstream publishes as a minimum needs per-stack metadata with
    a source, and real idle, typical and peak figures need a host, which is what
    `docs/resource-measurement.md` governs.

    Takes the two file sets rather than finding them, so which files are a
    stack's production set and which are opt-in stays check-structure.py's
    decision and this stays answerable about any pair of lists.

    Returns None for a host-installed stack, which has no compose file to read.
    """
    if not production:
        return None

    services = init = 0
    infrastructure: set[str] = set()
    gpu = None
    for path in production:
        for body in ((_structure.compose_load(path) or {}).get("services") or {}).values():
            body = body or {}
            # A one-shot container runs once and exits; counting it as a running
            # service would overstate what the stack costs to keep up.
            if str(body.get("restart", "")).strip('"') == "no":
                init += 1
            else:
                services += 1
            image = str(body.get("image") or "").lower()
            for needle, label in INFRASTRUCTURE.items():
                if needle in image:
                    infrastructure.add(label)
            if _reserves_gpu(body):
                gpu = "required"

    if gpu is None:
        for path in overlays:
            data = _structure.compose_load(path) or {}
            if any(_reserves_gpu(b or {}) for b in (data.get("services") or {}).values()):
                gpu = "optional"
                break

    parts = [f"{services} service" + ("s" if services != 1 else "")]
    if init:
        parts.append(f"{init} one-shot")
    if infrastructure:
        parts.append(" + ".join(sorted(infrastructure)))
    if gpu:
        parts.append(f"GPU {gpu}")
    return {
        "services": services,
        "init_services": init,
        "infrastructure": sorted(infrastructure),
        "gpu": gpu,
        # One owner for the wording, so the site and llms.txt cannot phrase the
        # same facts two ways.
        "summary": " · ".join(parts),
    }


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

        facts = decision_facts(text, key, problems)
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
            "footprint": footprint(
                _structure.compose_files(stack), _structure.overlay_files(stack)
            ),
            "decision_facts": facts,
            "decision_facts_checked": decision_facts_checked(text, key, bool(facts), problems),
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
