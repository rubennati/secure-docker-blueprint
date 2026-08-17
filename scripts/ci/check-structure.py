#!/usr/bin/env python3
"""
Structure checker for secure-docker-blueprint.

Reports drift from the canonical structure embodied by apps/_reference/ and
specified in docs/standards/{env,compose}-structure.md + naming-conventions.md.

Severity is per RULE, not per category — what can hurt you fails, what is merely
inconsistent warns.

FAIL (blocks CI — dangerous or leak-prone):
  latest-tag        image tag is :latest or major-only — not reproducible
  plaintext-secret  a password/secret/token carries a real value in .env.example
  gitignore-gap     .gitignore missing or not covering .env / .secrets/ / volumes/
  db-exposed        a datastore joins proxy-public or publishes a host port

WARN (reported — structural drift):
  missing-file      .env.example / README.md / UPSTREAM.md absent
  project-name      COMPOSE_PROJECT_NAME missing or not before the first section
  section-order     .env.example sections out of canonical order
  container-name    CONTAINER_NAME_* not derived from ${COMPOSE_PROJECT_NAME}
  env-file          `env_file:` used instead of an explicit `environment:` map
  no-resources      service without a memory or pids limit
  no-healthcheck    service without a healthcheck
  tls-options       Traefik tls.options without the @file suffix
  real-domain       a hostname that is not *.example.com

Known limits (deliberate, to keep the report actionable):
  - `16-alpine` style tags (bare major + variant) are accepted, though the spec
    asks for major.minor. Tightening this is a follow-up, not a blocker.
  - Section order only checks sections it recognises; custom ones are ignored.

Usage:
  python3 scripts/ci/check-structure.py [github-summary-path]

Exit code is 1 only when a FAIL rule triggers, so WARN drift can be paid down
gradually without blocking work.
"""

import re
import sys
from pathlib import Path

import yaml

ROOTS = ["core", "apps", "business", "monitoring", "backup"]

# Canonical .env.example section order (docs/standards/env-structure.md).
# A file may omit any section; the ones present must appear in this order.
CANONICAL_SECTIONS = [
    "Project",
    "Domain & Traefik",
    "Images",
    "Containers",
    "Network",
    "Database",
    "App Configuration",
    "SMTP",
    "Timezone",
    "Secrets",
]

# Service names treated as datastores — must never be publicly reachable.
DATASTORE_NAMES = {"db", "redis", "database", "mariadb", "postgres", "mysql", "memcached", "elasticsearch"}

# Variables whose value must never be committed. _KEY is excluded on purpose:
# NEXT_PUBLIC_VAPID_PUBLIC_KEY and friends are public by design.
SECRET_VAR = re.compile(r"^[A-Z0-9_]*(PASSWORD|SECRET|TOKEN|PASSWD|PWD)$")

# Accepted placeholders in a committed example file.
PLACEHOLDER = re.compile(r"^(__REPLACE_ME__|<.*>|changeme|CHANGEME|\$\{.*\}|)$")

# Tag values that are not reproducible: latest, or a bare major (8, v2, 16).
# Bounded to 3 digits so date-based CalVer tags (photoprism 260601) are not
# mistaken for a major — those pin an exact build and are reproducible.
BAD_TAG = re.compile(r"^(latest|v?\d{1,3})$")

# Directories that are structural exceptions, with the reason.
EXCEPT_DIRS = {
    "apps/_reference": "the canonical reference itself — stand-in images, no UPSTREAM",
}


def is_compose(path: Path) -> bool:
    """True when a YAML file declares Compose services."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except yaml.YAMLError:
        return False
    return isinstance(data, dict) and bool(data.get("services"))


def compose_files(app: Path) -> list[Path]:
    """The compose files that define the stack.

    Normally that is `docker-compose.yml` alone — overlays such as
    `activitypub.yml` or `docker-compose.local.yml` are opt-in and deliberately
    not checked. Some stacks (seafile, seafile-pro) instead split the stack
    across one file per component with no `docker-compose.yml` at all; those
    were invisible to this checker until every part was picked up.
    """
    main = app / "docker-compose.yml"
    if main.exists():
        return [main]
    return sorted(p for p in app.glob("*.yml") if is_compose(p))


def find_apps() -> list[Path]:
    apps = {p.parent for root in ROOTS for p in Path(root).rglob("docker-compose.yml")}
    # Split-compose stacks: a directory with compose files but no docker-compose.yml.
    for root in ROOTS:
        for candidate in Path(root).iterdir() if Path(root).is_dir() else []:
            if candidate.is_dir() and candidate not in apps:
                if any(is_compose(p) for p in candidate.glob("*.yml")):
                    apps.add(candidate)
    return sorted(apps)


def parse_env(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Return (variables, section names in file order)."""
    variables: list[tuple[str, str]] = []
    sections: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        m = re.match(r"^#\s*-{2,}\s*(.+?)\s*-{2,}", line)
        if m:
            # Strip a trailing layer tag such as "[traefik]".
            sections.append(re.sub(r"\s*\[[a-z]+\]\s*$", "", m.group(1)).strip())
            continue
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        variables.append((key.strip(), value.strip()))
    return variables, sections


def check_env(app: Path, findings: list[dict]) -> None:
    env = app / ".env.example"
    if not env.exists():
        findings.append({"level": "WARN", "rule": "missing-file",
                         "detail": ".env.example is absent"})
        return

    variables, sections = parse_env(env)
    names = [k for k, _ in variables]

    # -- project name (FAIL-adjacent structure, but harmless → WARN) ----------
    if "COMPOSE_PROJECT_NAME" not in names:
        findings.append({"level": "WARN", "rule": "project-name",
                         "detail": "COMPOSE_PROJECT_NAME is not set"})
    elif names[0] != "COMPOSE_PROJECT_NAME":
        findings.append({"level": "WARN", "rule": "project-name",
                         "detail": f"COMPOSE_PROJECT_NAME should come first, found '{names[0]}'"})

    # -- section order --------------------------------------------------------
    known = [s for s in sections if s in CANONICAL_SECTIONS]
    expected = [s for s in CANONICAL_SECTIONS if s in known]
    if known != expected:
        findings.append({"level": "WARN", "rule": "section-order",
                         "detail": f"got {known} — canonical: {expected}"})

    for key, value in variables:
        # -- plaintext secrets (FAIL) ----------------------------------------
        if SECRET_VAR.match(key) and not PLACEHOLDER.match(value):
            findings.append({"level": "FAIL", "rule": "plaintext-secret",
                             "detail": f"{key} carries a value — secrets belong in .secrets/"})

        # -- image tags (FAIL) ------------------------------------------------
        if key.endswith("_TAG"):
            # Strip any digest pin before judging the tag itself.
            tag = value.split("@")[0]
            if BAD_TAG.match(tag):
                findings.append({"level": "FAIL", "rule": "latest-tag",
                                 "detail": f"{key}={value} is not reproducible — pin a full version"})

        # -- container naming (WARN) ------------------------------------------
        if key.startswith("CONTAINER_NAME_") and "${COMPOSE_PROJECT_NAME}" not in value:
            findings.append({"level": "WARN", "rule": "container-name",
                             "detail": f"{key}={value} should derive from ${{COMPOSE_PROJECT_NAME}}"})

        # -- real domains (WARN) ----------------------------------------------
        if key.endswith("_HOST") and value and "TRAEFIK" in key:
            if not value.endswith("example.com") and "${" not in value:
                findings.append({"level": "WARN", "rule": "real-domain",
                                 "detail": f"{key}={value} — use *.example.com in a committed file"})



def _healthcheck_waived(text: str, service: str) -> bool:
    """True when the service block carries a documented reason for having none.

    Comments do not survive YAML parsing, so this reads the raw file and looks
    only inside the block belonging to `service`.
    """
    m = re.search(rf"(?m)^  {re.escape(service)}:\n", text)
    if not m:
        return False
    rest = text[m.end():]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_.-]+:\n|^[a-z]+:\n", rest)
    block = rest[: nxt.start()] if nxt else rest
    return bool(re.search(r"#\s*healthcheck:\s*(inherited|none)\b", block, re.I))

def check_compose(app: Path, findings: list[dict]) -> None:
    for path in compose_files(app):
        check_one_compose(app, path, findings)


def check_one_compose(app: Path, path: Path, findings: list[dict]) -> None:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        findings.append({"level": "FAIL", "rule": "yaml-parse",
                         "detail": f"{path.name} is not valid YAML: {exc}"})
        return

    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue

        # -- datastore exposure (FAIL) ---------------------------------------
        if name in DATASTORE_NAMES:
            nets = svc.get("networks") or []
            netnames = nets if isinstance(nets, list) else list(nets)
            if "proxy-public" in netnames:
                findings.append({"level": "FAIL", "rule": "db-exposed", "service": name,
                                 "detail": "datastore joins proxy-public — keep it on the internal network"})
            if svc.get("ports"):
                findings.append({"level": "FAIL", "rule": "db-exposed", "service": name,
                                 "detail": "datastore publishes a host port"})

        # -- env_file (WARN) --------------------------------------------------
        if svc.get("env_file"):
            findings.append({"level": "WARN", "rule": "env-file", "service": name,
                             "detail": "uses env_file: — prefer an explicit environment: map"})

        # -- resources (WARN) -------------------------------------------------
        # `memory` and `pids` are the two limits that bound the host: an unbounded
        # leak reaches the OOM-killer, which does not necessarily select the process
        # that allocated, and a fork bomb exhausts the global pid space. `cpus` is
        # not checked — it bounds neither, and compose-structure.md states the two
        # cases in which one is set.
        limits = ((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}
        absent = [k for k in ("memory", "pids") if k not in limits]
        if absent:
            findings.append({"level": "WARN", "rule": "no-resources", "service": name,
                             "detail": f"deploy.resources.limits without {' and '.join(absent)}"
                                       " — unbounded container"})

        # -- healthcheck (WARN) -----------------------------------------------
        # A service can legitimately have none: some images ship their own, which
        # Compose inherits, and some are built FROM scratch with no shell to run
        # one in. Neither is visible here — reading it would mean pulling images,
        # which CI should not do. So the compose file declares the reason and
        # this accepts it:
        #
        #   # healthcheck: inherited from the image
        #   # healthcheck: none — <why not>
        #
        # Anything else still warns, so the escape hatch cannot be used to wave
        # a service through quietly.
        hc = svc.get("healthcheck")
        if not hc and not _healthcheck_waived(raw_text, name):
            findings.append({"level": "WARN", "rule": "no-healthcheck", "service": name,
                             "detail": "no healthcheck"})

        # -- traefik tls.options needs @file (WARN) ---------------------------
        labels = svc.get("labels") or []
        label_list = labels if isinstance(labels, list) else [f"{k}={v}" for k, v in labels.items()]
        for label in label_list:
            if "tls.options=" in str(label) and "@file" not in str(label):
                findings.append({"level": "WARN", "rule": "tls-options", "service": name,
                                 "detail": "tls.options without @file will not resolve"})


def root_gitignore() -> str:
    p = Path(".gitignore")
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def uses_secrets(app: Path) -> bool:
    """True when the stack mounts Docker Secrets — i.e. .secrets/ will hold real values."""
    for path in compose_files(app):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
        except yaml.YAMLError:
            continue
        if data.get("secrets"):
            return True
    return False


def check_files(app: Path, findings: list[dict], root_gi: str) -> None:
    # A path counts as protected when either the repo-root or the app's own
    # .gitignore covers it — root rules apply to every app.
    local_gi = (app / ".gitignore")
    local = local_gi.read_text(encoding="utf-8", errors="replace") if local_gi.exists() else ""

    def covered(*patterns: str) -> bool:
        return any(p in root_gi or p in local for p in patterns)

    # Secret material unprotected is the only real leak risk here → FAIL, and
    # only when the app actually keeps secrets.
    if uses_secrets(app) and not covered(".secrets/"):
        findings.append({"level": "FAIL", "rule": "gitignore-gap",
                         "detail": "app uses Docker Secrets but .secrets/ is not gitignored"})
    if not covered(".env"):
        findings.append({"level": "FAIL", "rule": "gitignore-gap",
                         "detail": ".env is not gitignored"})
    if not covered("volumes/"):
        findings.append({"level": "WARN", "rule": "gitignore-gap",
                         "detail": "volumes/ is not gitignored"})
    if not local_gi.exists():
        findings.append({"level": "WARN", "rule": "missing-file",
                         "detail": ".gitignore is absent (relying on the repo-root one)"})

    for doc in ("README.md", "UPSTREAM.md"):
        if not (app / doc).exists():
            findings.append({"level": "WARN", "rule": "missing-file",
                             "detail": f"{doc} is absent"})


def main() -> int:
    # `--list` prints one compose file per line and exits. It exists so the shell
    # jobs in ci.yml can consume this discovery instead of keeping their own: a
    # `find … -name docker-compose.yml` misses every split-compose stack and every
    # root this file knows about, which left fifteen files unvalidated while the
    # Python checkers reported full coverage.
    # EXCEPT_DIRS is not applied here. It waives the structure rules for
    # apps/_reference, not the file's existence — the canonical template still has
    # to parse, and check-baseline.py scans it for the same reason.
    if "--list" in sys.argv[1:]:
        for app in find_apps():
            for f in compose_files(app):
                print(f)
        return 0

    results: list[tuple[Path, list[dict]]] = []
    fails = warns = 0
    root_gi = root_gitignore()

    for app in find_apps():
        key = str(app)
        if key in EXCEPT_DIRS:
            continue
        findings: list[dict] = []
        check_files(app, findings, root_gi)
        check_env(app, findings)
        check_compose(app, findings)
        if findings:
            results.append((app, findings))
        fails += sum(1 for f in findings if f["level"] == "FAIL")
        warns += sum(1 for f in findings if f["level"] == "WARN")

    # ── Console output — grouped by rule, so it reads as a work list ─────────
    by_rule: dict[str, list[tuple[Path, dict]]] = {}
    for app, findings in results:
        for f in findings:
            by_rule.setdefault(f["rule"], []).append((app, f))

    print()
    for level in ("FAIL", "WARN"):
        rules = {r: v for r, v in by_rule.items() if v[0][1]["level"] == level}
        if not rules:
            continue
        icon = "🔴" if level == "FAIL" else "🟡"
        for rule, items in sorted(rules.items(), key=lambda kv: -len(kv[1])):
            print(f"  {icon} {level}  {rule}  ({len(items)})")
            for app, f in items[:6]:
                svc = f" [{f['service']}]" if "service" in f else ""
                print(f"       {app}{svc}: {f['detail']}")
            if len(items) > 6:
                print(f"       … and {len(items) - 6} more")
        print()

    total = len(find_apps()) - len(EXCEPT_DIRS)
    status = "❌" if fails else "✅"
    print(f"  {status} {total} apps checked  ·  {fails} failure(s)  ·  {warns} warning(s)")
    if EXCEPT_DIRS:
        print(f"     {len(EXCEPT_DIRS)} excepted: {', '.join(EXCEPT_DIRS)}")
    print()

    # ── GitHub Actions Job Summary ──────────────────────────────────────────
    if len(sys.argv) > 1:
        lines = ["## Structure\n"]
        lines.append(
            f"{status} {total} apps checked — **{fails} failure(s)**, {warns} warning(s)\n"
        )
        if by_rule:
            lines.append("| Level | Rule | App | Service | Detail |")
            lines.append("|---|---|---|---|---|")
            for rule, items in sorted(by_rule.items()):
                for app, f in items:
                    icon = "🔴" if f["level"] == "FAIL" else "🟡"
                    lines.append(
                        f"| {icon} {f['level']} | {rule} | `{app}` "
                        f"| `{f.get('service', '—')}` | {f['detail']} |"
                    )
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
