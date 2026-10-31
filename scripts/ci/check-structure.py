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
  no-resources      service without a memory or pids limit
  no-swap-policy    service with a memory limit and no explicit memswap_limit —
                    coverage completed 2026-09-16 (every production service);
                    this guards the property, it does not report a migration
  burst-exposure    a router whose rate-limit bucket holds a whole first load
                    (limit-extra-large) while its access policy admits more
                    than a closed set of clients
  router-positions  a router that does not carry the four positions of the
                    middleware model — access, limit, headers, auth — once
                    each and in that order, or carries a name the model
                    replaced (D2/D6, 2026-10-18; headers is the mandatory
                    position, HSTS lives there)
  tls-conflict      two routers of one stack serve the same host name with
                    different tls.options — Traefik logs the conflict and
                    serves `default` to both
  retired-name      a stack still carries the vocabulary from before the
                    model: *_TRAEFIK_SECURITY or *_TRAEFIK_THREAT, an
                    acc-* / sec-* / tls-basic|aplus|modern value, a router
                    naming such a TLS profile — scripts/migrate-traefik-env.sh
                    maps every one of them
  missing-network-label
                    a service with traefik.enable=true and no
                    traefik.docker.network label — without it Traefik takes
                    the first network of the container in map order, which
                    is random, and a route lands on the internal network in
                    some of its reloads (measured 2026-10-31: two of six)
  port-no-host-address
                    a published port without a host address: it listens on
                    every address of the host, IPv4 and IPv6, and on an
                    IPv4-only network Docker relays the IPv6 side from the
                    bridge gateway (docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md).
                    The stacks that did so before the rule are listed in
                    KNOWN_UNBOUND_PORTS and reported as WARN until each is
                    bound; a new one fails

WARN (reported — structural drift):
  missing-file      .env.example / README.md / UPSTREAM.md absent
  project-name      COMPOSE_PROJECT_NAME missing or not before the first section
  section-order     .env.example sections out of canonical order
  container-name    CONTAINER_NAME_* not derived from ${COMPOSE_PROJECT_NAME}
  env-file          `env_file:` used instead of an explicit `environment:` map
  no-healthcheck    service without a healthcheck
  tls-options       Traefik tls.options without the @file suffix
  real-domain       a hostname that is not *.example.com
  block-order       a per-app block on the wrong side of the four: a response
                    header block (hsts-include-subdomains, frame-self,
                    csp-self-only, header-*) after the headers profile loses
                    to it; forwarded-proto-https before the four is a request
                    header the gate never sees

Known limits (deliberate, to keep the report actionable):
  - `16-alpine` style tags (bare major + variant) are accepted, though the spec
    asks for major.minor. Tightening this is a follow-up, not a blocker.
  - Section order only checks sections it recognises; custom ones are ignored.

Usage:
  python3 scripts/ci/check-structure.py [github-summary-path]

Exit code is 1 only when a FAIL rule triggers, so WARN drift can be paid down
gradually without blocking work.
"""

import functools
import re
import subprocess
import sys
from pathlib import Path

import yaml

# "development" is not a sixth access-pattern category (docs/architecture.md
# still defines five) — it is a Supporting-tier directory that happens to hold
# real, buildable compose files, so it gets the same structural check as any
# stack root. See docs/architecture.md#development-is-a-supporting-tier-domain-not-a-sixth-category.
ROOTS = ["core", "apps", "business", "monitoring", "backup", "development"]

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

# The whole-first-load bucket (limit-extra-large) lets one address issue a
# thousand requests before the sustained rate applies. These access policies
# keep the set of such addresses closed — access-blocked closes the router
# altogether. The names before the model are kept so that a stack carrying
# them is still judged (and fails for the name, see retired-name).
CLOSED_ACCESS = {"access-lan", "access-vpn", "access-lan-vpn", "access-blocked",
                 "acc-private", "acc-tailscale", "acc-deny"}

# The middleware model (core/traefik/config/dynamic/model.yml, decided
# 2026-10-18): four positions on every router, in this order. A router names
# each through its stack's variable — ${X_TRAEFIK_ACCESS}@file and so on — and
# the auth position carries its provider in the value (auth-none@file,
# <stack>-auth@docker), so it is recognised by the variable as well as by name.
POSITIONS = ("access", "limit", "headers", "auth")
POSITION_VAR = re.compile(r"TRAEFIK_[A-Z0-9_]*?(ACCESS|LIMIT|HEADERS|AUTH)$")
# The names the model replaced (v0.9.4: access.yml, security-blocks.yml,
# security-chains.yml, crowdsec.yml, tls-profiles.yml). A stack carrying one
# has not been migrated — scripts/migrate-traefik-env.sh maps every one.
OLD_NAME = re.compile(r"^(sec-|acc-|hdr-|rl-|crowdsec-(basic|appsec))")
RETIRED_VALUE = re.compile(r"^(sec-|acc-|hdr-|rl-|crowdsec-(basic|appsec)|tls-(basic|aplus|modern))")
RETIRED_KEY = re.compile(r"TRAEFIK_[A-Z0-9_]*(SECURITY|THREAT)$")
TLS_RETIRED = {"tls-basic", "tls-aplus", "tls-modern"}
# Per-app blocks and the side of the four they belong on (model.yml).
BEFORE_PROFILE = re.compile(r"^(hsts-include-subdomains|frame-self|csp-self-only|header-[a-z0-9-]+)$")
AFTER_FOUR = {"forwarded-proto-https"}
# Severity of the two rules that describe the model's shape. Every router
# carries the four positions since the cut (Phase 4.3); a router that does
# not is a regression, and blocks.
MODEL_LEVEL = "FAIL"
# Substitution of ${VAR} and ${VAR:-default} in a label, with the stack's
# .env.example values standing in for a deployment's .env.
LABEL_VAR = re.compile(r"\$\{([A-Za-z0-9_]+)(?::?-([^}]*))?\}")

# Accepted placeholders in a committed example file.
PLACEHOLDER = re.compile(r"^(__REPLACE_ME__|<.*>|changeme|CHANGEME|\$\{.*\}|)$")

# Tag values that are not reproducible: latest, or a bare major (8, v2, 16).
# Bounded to 3 digits so date-based CalVer tags (photoprism 260601) are not
# mistaken for a major — those pin an exact build and are reproducible.
BAD_TAG = re.compile(r"^(latest|v?\d{1,3})$")

# Stacks that publish a port without a host address today. Each is a known
# finding of the ingress audit (docs/audits/ingress-architecture-2026-10-31.md),
# reported as WARN so it stays visible without blocking, until the stack binds
# the port to a *_BIND variable. Nothing is added here without the same audit
# trail; a stack not listed fails.
KNOWN_UNBOUND_PORTS = {
    "apps/unifi": "device-facing STUN, discovery and inform ports — devices on every interface",
    "apps/opencanary": "honeypot — every published port is meant to be reached",
    "core/teleport": "proxy and auth ports of the bastion",
    "core/shellhub": "SSH gateway on 2222",
    "core/warpgate": "SSH gateway on 2222",
    "core/jumpserver": "SSH gateway on 2222",
    "core/orion-belt": "SSH gateway on 2222",
    "core/step-ca": "the CA's API port",
    "core/headscale": "the DERP relay's STUN port, in the opt-in derp.yml overlay",
}

# Directories that are structural exceptions, with the reason.
EXCEPT_DIRS = {
    "apps/_reference": "the canonical reference itself — stand-in images, no UPSTREAM",
    "development/static-site": "reusable deployment pattern, not a versioned app — no single upstream, no UPSTREAM",
    "development/web-api": "reusable deployment pattern, not a versioned app — no single upstream, no UPSTREAM",
}


@functools.lru_cache(maxsize=1)
def repository_files() -> frozenset[str] | None:
    """Paths Git considers part of the repository, or None when Git is absent.

    `--cached` is what is tracked, `--others --exclude-standard` adds files that
    are new but not ignored. Together they are exactly "the repository as it
    would be committed", which is what a blueprint gate should judge.

    What this deliberately leaves out is material the working tree carries but
    the repository does not own: `.gitignore`d runtime directories and anything
    listed in `.git/info/exclude`. Walking the filesystem instead made local
    scratch space and generated volume data indistinguishable from blueprint
    content, and a checker that fails on those is reporting on the machine
    rather than on the repository.

    Returning None (no Git, e.g. a source tarball) falls back to the filesystem
    walk, so the checker still runs — it simply cannot make the distinction.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return frozenset(line for line in out.splitlines() if line)


def in_repository(path: Path) -> bool:
    """True when Git owns this path, or when Git cannot be consulted."""
    known = repository_files()
    return True if known is None else path.as_posix() in known


class ComposeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates Compose's own YAML tags.

    Compose 2.24+ uses `!reset` and `!override` in an overlay to clear or replace
    a value the base file set. `yaml.safe_load` raises on an unknown tag, and
    `is_compose()` read that as "not a compose file" — which is how
    `backup/urbackup/network-host.yml` became invisible to every checker instead
    of being reported.
    """


def _compose_tag(loader, suffix, node):
    """Resolve `!reset` / `!override` to the value underneath the tag.

    The tag decides how Compose *merges* the value, which no rule here asks
    about; the rules read what the value is. `!reset null` therefore becomes
    None, and an `!override` list stays that list.
    """
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    scalar = loader.construct_scalar(node)
    return None if scalar in ("", "null", "~") else scalar


ComposeLoader.add_multi_constructor("!", _compose_tag)


def compose_load(path: Path):
    """Parse a compose file, tolerating Compose's tags. Raises on real YAML errors."""
    return yaml.load(path.read_text(encoding="utf-8", errors="replace"), ComposeLoader) or {}


def is_compose(path: Path) -> bool:
    """True when a YAML file declares Compose services."""
    try:
        data = compose_load(path)
    except yaml.YAMLError:
        return False
    return isinstance(data, dict) and bool(data.get("services"))


# Top-level keys Compose itself defines. A fragment may carry any subset — an
# overlay that only redefines networks is still a compose file.
COMPOSE_TOP_LEVEL = {"services", "networks", "volumes", "configs", "secrets",
                     "name", "include", "version"}
COMPOSE_CONTENT = {"services", "networks", "volumes", "configs", "secrets"}


def is_compose_fragment(path: Path) -> bool:
    """True for a compose file or a fragment of one, services or not.

    `is_compose()` requires `services:`, which is right for finding a stack —
    a directory holding only a networks file is not one. It is wrong for finding
    overlays: `core/traefik/network-dual-stack.yml` redefines the public network
    and nothing else, and reading it as "not a compose file" left the one overlay
    that changes the address plan of every routed service unvalidated.

    A stack's own config examples are excluded by the same test: gatus's
    `config.example.yaml` is `endpoints`/`storage`/`ui`, none of which Compose
    defines.
    """
    try:
        data = compose_load(path)
    except yaml.YAMLError:
        return False
    if not isinstance(data, dict) or not data:
        return False
    keys = {str(k) for k in data if not str(k).startswith("x-")}
    return bool(keys & COMPOSE_CONTENT) and keys <= COMPOSE_TOP_LEVEL


def compose_files(app: Path) -> list[Path]:
    """The compose files that define the stack.

    Normally that is `docker-compose.yml` alone — overlays such as
    `activitypub.yml` or `docker-compose.local.yml` are opt-in and deliberately
    not checked. Some stacks (seafile, seafile-pro) instead split the stack
    across one file per component with no `docker-compose.yml` at all; those
    were invisible to this checker until every part was picked up.
    """
    main = app / "docker-compose.yml"
    if main.exists() and in_repository(main):
        return [main]
    # For a split stack the glob decides what counts as production, so the
    # local test stack must be excluded from it.
    return sorted(p for p in app.glob("*.yml")
                  if in_repository(p) and is_compose(p) and not p.name.endswith(".local.yml"))


def overlay_files(app: Path) -> list[Path]:
    """Opt-in compose files that are not part of the canonical production stack.

    An overlay is applied on top of the stack with a second `-f`, and several of
    them are mutually exclusive — `network-host.yml` replaces the bridge network
    the base file sets, `docker-compose.gpu.yml` replaces the CPU runtime. They
    are therefore never part of the stack's service inventory and never counted
    as one: `compose_files()` stays the canonical production set.

    They do run, though, so whatever an overlay *introduces* is a real service on
    a real host and the runtime rules apply to it. Before this existed, six files
    were checked by nothing.
    """
    canonical = {p.name for p in compose_files(app)}
    return sorted(p for p in app.glob("*.yml")
                  if in_repository(p) and is_compose_fragment(p)
                  and p.name not in canonical and not p.name.endswith(".local.yml"))


def base_service_names(app: Path) -> set[str]:
    """Service names the canonical production compose defines."""
    names: set[str] = set()
    for path in compose_files(app):
        try:
            data = compose_load(path)
        except yaml.YAMLError:
            continue
        names.update((data.get("services") or {}))
    return names


def introduces_service(svc: dict) -> bool:
    """True when a service block stands on its own rather than patching a base one.

    A block with `image:` or `build:` adds a service. A block without either only
    modifies a service the base file already defines, inherits everything else
    from it, and cannot be judged on its own — checking one would report a
    missing image on `db: {environment: …}`.
    """
    return bool(svc.get("image") or svc.get("build"))


def find_apps() -> list[Path]:
    apps = {p.parent for root in ROOTS for p in Path(root).rglob("docker-compose.yml")
            if in_repository(p)}
    # Split-compose stacks: a directory with compose files but no docker-compose.yml.
    for root in ROOTS:
        for candidate in Path(root).iterdir() if Path(root).is_dir() else []:
            if candidate.is_dir() and candidate not in apps:
                if any(in_repository(p) and is_compose(p) for p in candidate.glob("*.yml")):
                    apps.add(candidate)
    return sorted(apps)


def _expand(value: str, env: dict) -> str:
    """Substitute ${VAR} from a stack's .env.example, leaving unknowns intact."""
    return re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}",
                  lambda m: env.get(m.group(1), m.group(0)), value)


def external_networks(app: Path) -> dict:
    """Compose network key -> effective Docker network name, external only.

    The key is a local label, not an identity: three stacks in this repository
    declare the same shared network under the key `proxy` or `proxy-public`,
    and two of them name it through `${TRAEFIK_NETWORK}`. Only the resolved
    `name:` says which Docker network is actually joined.
    """
    env_path = app / ".env.example"
    env = dict(parse_env(env_path)[0]) if env_path.exists() else {}
    out: dict = {}
    for path in compose_files(app):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
        except yaml.YAMLError:
            continue
        for key, net in (data.get("networks") or {}).items():
            if isinstance(net, dict) and net.get("external"):
                out[key] = _expand(str(net.get("name", key)), env)
    return out


@functools.lru_cache(maxsize=1)
def canonical_shared_network():
    """The proxy network the repository itself declares as shared.

    core/traefik owns it, so its own .env.example is the source of truth rather
    than a constant repeated here.
    """
    env_path = Path("core/traefik/.env.example")
    if not env_path.exists():
        return None
    for key, value in parse_env(env_path)[0]:
        if key == "PUBLIC_NETWORK":
            return value.strip() or None
    return None


def shared_external_networks() -> set:
    """Effective names of external networks shared between deployable stacks.

    `external: true` alone does not make a network shared — a stack may attach
    to an external network nothing else uses. A network counts as shared when
    the repository declares it as the common proxy network, or when two
    independently deployable stacks demonstrably attach to the same effective
    name. Both are derived, so a second shared network needs no code change.
    """
    users: dict = {}
    for app in find_apps():
        if str(app) in EXCEPT_DIRS:
            continue
        for effective in set(external_networks(app).values()):
            users.setdefault(effective, set()).add(str(app))
    shared = {name for name, stacks in users.items() if len(stacks) >= 2}
    canonical = canonical_shared_network()
    if canonical:
        shared.add(canonical)
    return shared


def stack_identity(app: Path) -> tuple[str, str | None]:
    """(identity, disagreement) for a stack.

    `COMPOSE_PROJECT_NAME` is the canonical identity because it is the name
    Compose itself derives container and default network names from. The
    directory name is the fallback and the sanity check; where the two differ
    this returns the disagreement instead of silently preferring one.
    """
    directory = app.name
    env = app / ".env.example"
    project = ""
    if env.exists():
        for key, value in parse_env(env)[0]:
            if key == "COMPOSE_PROJECT_NAME":
                project = value.strip()
                break
    if not project:
        return directory, None
    if project != directory:
        return project, f"COMPOSE_PROJECT_NAME is {project!r} but the directory is {directory!r}"
    return project, None


def identity_conforms(service: str, identity: str) -> bool:
    """A shared-network service key must be application-specific.

    Either it *is* the stack identity — `seafile` needs no role suffix — or it
    carries the identity as a prefix, `<stack>-<role>`.
    """
    return service == identity or service.startswith(identity + "-")


def check_shared_network_identity(by_app: dict) -> None:
    """Services on a shared external network carry an unambiguous identity.

    Compose publishes the service key as a discoverable name on every network
    the service joins. Docker states that a network-wide name shared by more
    than one container resolves to an unspecified one of them, so two
    independently deployable stacks must not publish the same key into the same
    shared network.

    Two rules, deliberately independent:
      shared-net-identity   fires on the first generic key, before a second
                            stack exists to collide with it.
      shared-net-duplicate  the backstop, in case identity derivation is wrong.
    """
    shared = shared_external_networks()
    if not shared:
        return
    claimed: dict[tuple[str, str], set[str]] = {}

    for app in find_apps():
        if str(app) in EXCEPT_DIRS:
            continue
        identity, disagreement = stack_identity(app)
        external = external_networks(app)
        entries = by_app.setdefault(app, [])
        noted = False

        for path in compose_files(app):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
            except yaml.YAMLError:
                continue
            for name, svc in (data.get("services") or {}).items():
                if not isinstance(svc, dict):
                    continue
                nets = svc.get("networks") or []
                netnames = nets if isinstance(nets, list) else list(nets)
                joined = sorted({external[n] for n in netnames
                                 if n in external and external[n] in shared})
                if not joined:
                    continue
                if disagreement and not noted:
                    entries.append({"level": "WARN", "rule": "identity-source", "service": name,
                                    "detail": disagreement + " — resolve before relying on the derived identity"})
                    noted = True
                if not identity_conforms(name, identity):
                    entries.append({"level": "FAIL", "rule": "shared-net-identity", "service": name,
                                    "detail": f"joins {', '.join(joined)} with a generic key — "
                                              f"use '{identity}-<role>' so blueprints stay unambiguous"})
                for net in joined:
                    claimed.setdefault((net, name), set()).add(str(app))

    for (net, name), stacks in sorted(claimed.items()):
        if len(stacks) > 1:
            for stack in sorted(stacks):
                by_app.setdefault(Path(stack), []).append(
                    {"level": "FAIL", "rule": "shared-net-duplicate", "service": name,
                     "detail": f"'{name}' is published into {net} by {len(stacks)} stacks — "
                               f"Docker does not define which container the name resolves to"})


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


IMAGE_VAR = re.compile(r"\$\{([A-Za-z0-9_]+)(?::?-([^}]*))?\}")


def split_image_ref(ref: str) -> tuple[str, str]:
    """An image reference as (repository, pin), the pin keeping any digest.

    A colon also separates a registry from its port, so only a colon after the
    last `/` introduces a tag: `registry:5000/app` is a repository with no pin,
    `uroni/urbackup-server:2.5.x@sha256:…` pins through both halves and the
    digest is the part that actually fixes the image.
    """
    base, _, digest = ref.partition("@")
    suffix = f"@{digest}" if digest else ""
    head, sep, tail = base.rpartition(":")
    if not sep or "/" in tail:
        return base, suffix.lstrip("@") if suffix else ""
    return head, tail + suffix


def _substitute(env: dict):
    """Replace `${VAR}` from `env`, leaving an unknown one in place.

    Substituting an unknown variable with "" would turn `app:${MISSING}` into
    `app:`, which reads as a repository pinned to nothing rather than as a
    reference that could not be resolved. The caller relies on the `${` marker
    surviving to tell those apart.
    """
    def one(m):
        name, default = m.group(1), m.group(2)
        if name in env:
            return env[name]
        return default if default is not None else m.group(0)
    return one


def resolved_images(compose: Path, env: dict) -> dict[str, set[str]]:
    """{repository: {pin, ...}} for one compose file, variables substituted.

    A reference that still holds an unresolved variable is skipped rather than
    guessed at: it means the example file does not define what the compose file
    reads, which is a different finding and belongs to whoever reports that.
    """
    out: dict[str, set[str]] = {}
    for body in ((compose_load(compose) or {}).get("services") or {}).values():
        ref = str((body or {}).get("image") or "")
        if not ref:
            continue
        ref = IMAGE_VAR.sub(_substitute(env), ref)
        if not ref or "${" in ref:
            continue
        repo, pin = split_image_ref(ref)
        out.setdefault(repo, set()).add(pin)
    return out


def check_local_pins(app: Path, findings: list[dict]) -> None:
    """Where the local stack runs production's image, it runs production's version.

    The local file exists so a stack can be tried on one machine. That only
    means anything if what gets tried is what the repository ships: 41 pins had
    drifted behind production when this rule was written, one by ten minor
    versions, and nothing had decided they should differ — `docs/maintenance.md`
    simply never named `.env.local.example` in the Version Chain, so no bump
    ever reached it.

    The comparison joins on the image repository rather than on the variable
    name or the service key, both of which legitimately differ between the two
    files. That makes the exceptions fall out instead of needing a list: a local
    stack on a different image (`apps/vllm` runs the CPU build) shares no
    repository and is never compared, and a service the local stack does not run
    at all simply is not there.
    """
    local = app / "docker-compose.local.yml"
    if not local.exists():
        return

    prod: dict[str, set[str]] = {}
    for path in compose_files(app):
        for repo, pins in resolved_images(path, dict(parse_env(app / ".env.example")[0])).items():
            prod.setdefault(repo, set()).update(pins)

    env_local = app / ".env.local.example"
    mine = resolved_images(local, dict(parse_env(env_local)[0]) if env_local.exists() else {})
    for repo in sorted(set(prod) & set(mine)):
        if prod[repo] != mine[repo]:
            want = ", ".join(sorted(prod[repo])) or "(none)"
            got = ", ".join(sorted(mine[repo])) or "(none)"
            findings.append({"level": "FAIL", "rule": "local-pin-drift",
                             "detail": f"{repo}: local pins {got}, production pins {want} "
                                       "— the local stack must evaluate the shipped version"})


IMAGE_LINE = re.compile(r"^\s*image:\s*(.+)$")
IMAGE_VARIABLE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)")


def image_variables(app: Path) -> frozenset[str]:
    """Every variable an `image:` line of the stack's production compose files
    reads — the set that decides whether a `<NAME>_VERSION` variable is a pin.
    """
    names: set[str] = set()
    for path in compose_files(app):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = IMAGE_LINE.match(line)
            if m:
                names.update(IMAGE_VARIABLE.findall(m.group(1)))
    return frozenset(names)


def pinned_tag(key: str, value: str, image_vars: frozenset[str] = frozenset()) -> str | None:
    """The tag a variable pins, for the pinning styles in this repository.

    Most stacks split the reference, naming the image in the compose file and
    the version in `<NAME>_TAG`. A few carry the whole reference in
    `<NAME>_IMAGE` instead — Seafile for all eight of its images, Authentik and
    Traefik for one each. The rule is about reproducibility, which does not
    depend on which half of the reference the variable holds.

    A `<NAME>_VERSION` variable counts only when an `image:` line reads it —
    `core/shellhub` pins three images through `SHELLHUB_VERSION`, while
    `CROWDSEC_BOUNCER_PLUGIN_VERSION` names a Traefik plugin release and no
    image. The name alone cannot tell the two apart; the compose file can.

    Returns None for a variable that pins nothing. Any digest is stripped
    first: `2.5.x@sha256:…` is reproducible through the digest, and it is the
    tag that has to be judged on its own.
    """
    if key.endswith("_TAG") or (key.endswith("_VERSION") and key in image_vars):
        tag = value
    elif key.endswith("_IMAGE"):
        tag = split_image_ref(value)[1]
        if not tag:
            return None
    else:
        return None
    tag = tag.split("@")[0]
    return tag or None


def check_env_pins(app: Path, findings: list[dict]) -> None:
    """The tag rule, over every committed `*.env*.example` file in the stack.

    `check_env` reads `.env.example` alone, because the structural rules —
    section order, `COMPOSE_PROJECT_NAME` first — describe that file and no
    other. Reproducibility is not like that: an unpinned image in
    `.env.local.example` is as irreproducible as one in the production file,
    and someone evaluating a stack from the local path is the person least
    able to tell which version they ended up running.

    84 committed example files sat outside the check until this ran over them,
    and none violated the rule. That is what makes this enforcement of a
    property the repository already has rather than a migration.
    """
    image_vars = image_variables(app)
    for path in sorted(app.glob("*.env*.example")):
        for key, value in parse_env(path)[0]:
            tag = pinned_tag(key, value, image_vars)
            if tag and BAD_TAG.match(tag):
                findings.append({"level": "FAIL", "rule": "latest-tag",
                                 "detail": f"{path.name}: {key}={value} is not "
                                           "reproducible — pin a full version"})


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

        # -- image tags: check_env_pins owns them, across every example file ---

        # -- container naming (WARN) ------------------------------------------
        if key.startswith("CONTAINER_NAME_") and "${COMPOSE_PROJECT_NAME}" not in value:
            findings.append({"level": "WARN", "rule": "container-name",
                             "detail": f"{key}={value} should derive from ${{COMPOSE_PROJECT_NAME}}"})

        # -- the vocabulary before the middleware model (FAIL) ----------------
        if "TRAEFIK" in key:
            if RETIRED_KEY.search(key):
                findings.append({"level": "FAIL", "rule": "retired-name",
                                 "detail": f"{key} is a variable from before the middleware model — the four "
                                           "positions are *_TRAEFIK_ACCESS, _LIMIT, _HEADERS and _AUTH; threat "
                                           "enforcement is core/traefik's switch. scripts/migrate-traefik-env.sh maps it"})
            elif RETIRED_VALUE.match(value):
                findings.append({"level": "FAIL", "rule": "retired-name",
                                 "detail": f"{key}={value} names what the middleware model replaced — "
                                           "scripts/migrate-traefik-env.sh maps it"})

        # -- real domains (WARN) ----------------------------------------------
        if key.endswith("_HOST") and value and "TRAEFIK" in key:
            # endswith alone accepts any host whose name merely ends in those
            # characters, without a label boundary in front of them.
            reserved = value == "example.com" or value.endswith(".example.com")
            if not reserved and "${" not in value:
                findings.append({"level": "WARN", "rule": "real-domain",
                                 "detail": f"{key}={value} — use *.example.com in a committed file"})

    # -- the wide first-load burst is judged per router: check_routers --------



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

    swapless: list[str] = []

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

        # -- resources (FAIL) -------------------------------------------------
        # `memory` and `pids` are the two limits that bound the host: an unbounded
        # leak reaches the OOM-killer, which does not necessarily select the process
        # that allocated, and a fork bomb exhausts the global pid space. `cpus` is
        # not checked — it bounds neither, and compose-structure.md states the two
        # cases in which one is set.
        #
        # FAIL rather than WARN: every service in the tree carries both, so this
        # guards the property rather than reporting drift towards it.
        limits = ((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}
        absent = [k for k in ("memory", "pids") if k not in limits]
        if absent:
            findings.append({"level": "FAIL", "rule": "no-resources", "service": name,
                             "detail": f"deploy.resources.limits without {' and '.join(absent)}"
                                       " — unbounded container"})

        # -- swap policy (FAIL) -------------------------------------------------
        # A memory limit leaves swap unbounded: with `memswap_limit` unset Docker
        # grants as much swap again as the memory limit, so a container inside its
        # cap can still page the host into unusability without being killed.
        # Coverage completed 2026-09-16 — every production service states a
        # policy, so this now guards the property rather than reporting a
        # migration. Counted per stack rather than per service, matching the
        # reporting shape from when it was a WARN: a regression here is
        # expected to be rare, and the per-file grouping still reads cleanly.
        # compose-structure.md owns which value belongs to which workload.
        if "memory" in limits and "memswap_limit" not in svc:
            swapless.append(name)

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
        # `healthcheck: {disable: true}` counts as having none. The dict is truthy,
        # so a bare `if not hc` waved it through — four services used it and none
        # was reported. In Compose the key suppresses a HEALTHCHECK baked into the
        # image; it never defines one, so the service still needs the same written
        # reason as a service with no healthcheck block at all.
        hc = svc.get("healthcheck")
        disabled = isinstance(hc, dict) and hc.get("disable")
        if (not hc or disabled) and not _healthcheck_waived(raw_text, name):
            findings.append({"level": "WARN", "rule": "no-healthcheck", "service": name,
                             "detail": "healthcheck disabled" if disabled else "no healthcheck"})

        # -- traefik tls.options needs @file (WARN) ---------------------------
        labels = svc.get("labels") or []
        label_list = labels if isinstance(labels, list) else [f"{k}={v}" for k, v in labels.items()]
        for label in label_list:
            if "tls.options=" in str(label) and "@file" not in str(label):
                findings.append({"level": "WARN", "rule": "tls-options", "service": name,
                                 "detail": "tls.options without @file will not resolve"})

    # -- swap policy, one line per compose file (FAIL) -------------------------
    if swapless:
        findings.append({"level": "FAIL", "rule": "no-swap-policy",
                         "detail": f"{path.name}: {len(swapless)} service(s) with a memory "
                                   f"limit and no memswap_limit — swap left implicit "
                                   f"({', '.join(sorted(swapless))})"})


def resolve_label(value: str, env: dict) -> str:
    """Substitute ${VAR} and ${VAR:-default} from the stack's variables.

    A variable the file does not set resolves to its default, else to the
    empty string — which is what Compose passes to Docker, and what makes an
    empty position disable a router rather than merely leave it bare.
    """
    seen = 0
    while LABEL_VAR.search(value) and seen < 10:
        value = LABEL_VAR.sub(lambda m: env.get(m.group(1), m.group(2) or ""), value)
        seen += 1
    return value


def router_labels(path: Path) -> dict[str, dict[str, str]]:
    """Every `traefik.http.routers.<name>.<key>=<value>` label in a compose
    file, keyed by the raw router name, with the service it is declared on."""
    try:
        data = compose_load(path)
    except yaml.YAMLError:
        return {}
    routers: dict[str, dict[str, str]] = {}
    for svc_name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        labels = svc.get("labels") or []
        label_list = labels if isinstance(labels, list) else [f"{k}={v}" for k, v in labels.items()]
        for label in label_list:
            key, sep, value = str(label).partition("=")
            m = re.match(r"^traefik\.http\.routers\.([^.]+)\.(.+)$", key.strip())
            if not sep or not m:
                continue
            r = routers.setdefault(m.group(1), {"_service": svc_name, "_file": path.name})
            r[m.group(2)] = value.strip()
    return routers


def classify(entry: str, family_by_value: dict[str, str]) -> str | None:
    """The position an entry of a middlewares list fills, or None for a block."""
    name = entry.split("@", 1)[0]
    for family in POSITIONS:
        if name.startswith(family + "-"):
            return family
    if name.startswith("acc-"):
        return "access"
    if name.startswith("rl-"):
        return "limit"
    if name.startswith(("sec-", "hdr-")):
        return "headers"
    # A credential gate the stack owns (<stack>-auth@docker) carries no
    # family prefix; the variable it came from names its position.
    return family_by_value.get(entry) or family_by_value.get(name)


def check_routers(app: Path, findings: list[dict]) -> None:
    """The middleware model on every router of the stack (Phase 4, D2/D6):
    the four positions once each and in order, a per-app block on its side of
    them, the whole-first-load bucket only behind a closed access policy, and
    one TLS option per host name across the stack's routers."""
    env_file = app / ".env.example"
    env = dict(parse_env(env_file)[0]) if env_file.exists() else {}
    family_by_value: dict[str, str] = {}
    for key, value in env.items():
        m = POSITION_VAR.search(key)
        if m and value:
            # the value as written and as Compose resolves it: a stack's own
            # gate is ${COMPOSE_PROJECT_NAME}-auth@docker in the file
            for v in {value, resolve_label(value, env)}:
                family_by_value[v] = m.group(1).lower()
                family_by_value.setdefault(v + "@file", m.group(1).lower())

    tls_by_host: dict[str, dict[str, list[str]]] = {}
    for path in compose_files(app):
        for raw_name, labels in router_labels(path).items():
            if "rule" not in labels:
                continue
            name = resolve_label(raw_name, env)
            hosts = re.findall(r"Host\(`([^`]+)`\)", resolve_label(labels["rule"], env))
            option = resolve_label(labels.get("tls.options", ""), env).strip() or "default"
            for host in hosts:
                tls_by_host.setdefault(host, {}).setdefault(option, []).append(name)
            if option.split("@", 1)[0] in TLS_RETIRED:
                findings.append({"level": "FAIL", "rule": "retired-name", "service": name,
                                 "detail": f"tls.options names {option}, a profile the middleware model replaced "
                                           "(tls-compatible / tls-standard / tls-strict) — and the deployment "
                                           "standard needs no label at all"})

            raw = labels.get("middlewares", "")
            entries = [e.strip() for e in resolve_label(raw, env).split(",") if e.strip()]
            empty = [m.group(1) for m in LABEL_VAR.finditer(raw)
                     if POSITION_VAR.search(m.group(1)) and not env.get(m.group(1), m.group(2) or "")]
            families = [classify(e, family_by_value) for e in entries]
            old = sorted({e.split("@", 1)[0] for e in entries if OLD_NAME.match(e)})

            # -- the four positions, once each, in order (MODEL_LEVEL) -------
            problems: list[str] = []
            missing = [p for p in POSITIONS if p not in families]
            if missing:
                problems.append("missing " + ", ".join(missing))
            twice = [p for p in POSITIONS if families.count(p) > 1]
            if twice:
                problems.append("twice: " + ", ".join(twice))
            present = [f for f in families if f in POSITIONS]
            if present != sorted(present, key=POSITIONS.index):
                problems.append("out of order: " + " → ".join(present))
            if empty:
                problems.append("empty variable " + ", ".join(sorted(set(empty))) + " disables the router")
            if old:
                problems.append("names the model replaces: " + ", ".join(old))
            if problems:
                findings.append({"level": MODEL_LEVEL, "rule": "router-positions", "service": name,
                                 "detail": "; ".join(problems)})

            # -- a per-app block on its side of the four (WARN) --------------
            headers_at = families.index("headers") if "headers" in families else None
            auth_at = families.index("auth") if "auth" in families else None
            for i, entry in enumerate(entries):
                block = entry.split("@", 1)[0]
                if BEFORE_PROFILE.match(block) and headers_at is not None and i > headers_at:
                    findings.append({"level": "WARN", "rule": "block-order", "service": name,
                                     "detail": f"{block} stands after the headers profile and loses "
                                               "to it on the response — place it before"})
                if block in AFTER_FOUR and auth_at is not None and i < auth_at:
                    findings.append({"level": "WARN", "rule": "block-order", "service": name,
                                     "detail": f"{block} stands before the auth position — "
                                               "place it after the four"})

            # -- the whole-first-load bucket behind a closed policy (FAIL) ----
            wide = [e.split("@", 1)[0] for e in entries
                    if e.split("@", 1)[0] == "limit-extra-large" or
                    (e.split("@", 1)[0].startswith("sec-") and e.split("@", 1)[0].endswith("-xl"))]
            if wide:
                access = [e.split("@", 1)[0] for e, f in zip(entries, families) if f == "access"]
                if not access or any(a not in CLOSED_ACCESS for a in access):
                    findings.append({"level": "FAIL", "rule": "burst-exposure", "service": name,
                                     "detail": f"{wide[0]} holds a whole first load in one burst — "
                                               f"pair it with a closed access policy "
                                               f"({', '.join(sorted(CLOSED_ACCESS))}), "
                                               f"found '{', '.join(access) or 'none'}'"})

    # -- one TLS option per host name across the stack (MODEL_LEVEL) ----------
    for host, by_option in sorted(tls_by_host.items()):
        if len(by_option) > 1:
            shape = "; ".join(f"{opt}: {', '.join(names)}" for opt, names in sorted(by_option.items()))
            findings.append({"level": MODEL_LEVEL, "rule": "tls-conflict",
                             "detail": f"{host} is served with different tls.options — "
                                       f"Traefik falls back to `default` for all of them ({shape})"})


IPV4_LITERAL = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _port_has_host_address(entry, env: dict) -> bool:
    """True when a `ports:` entry names the host address it binds to.

    Short syntax: `host:published:target[/proto]`, where `host` is an IPv4
    literal or a bracketed IPv6 literal after the stack's example values are
    substituted — `${APP_MAIL_BIND}:25:25` with `APP_MAIL_BIND=0.0.0.0`,
    `${APP_TRAPPER_BIND}:10051` with `APP_TRAPPER_BIND=0.0.0.0:10051`. Long
    syntax: a non-empty `host_ip`. A variable the example does not set, or sets
    to nothing, leaves the host empty, and Compose then binds every address of
    the host — so it does not count, whatever the variable is called.
    """
    if isinstance(entry, dict):
        host = str(entry.get("host_ip") or "").strip()
        return bool(host) and "${" not in host
    raw = str(entry).strip().strip("'\"")
    value = resolve_label(raw, env).split("/", 1)[0]
    if "${" in value:
        return False
    if value.startswith("["):
        return "]:" in value and value.count(":") >= 2
    parts = value.split(":")
    return len(parts) >= 3 and bool(IPV4_LITERAL.fullmatch(parts[0]))


def check_ports_and_labels(app: Path, findings: list[dict]) -> None:
    """Two guards of the ingress programme (DEC-075, step 1).

    A published port binds to a host address, or the host listens on every
    address it has — IPv4 and IPv6 alike, which is how an IPv6 client reached
    Traefik as the bridge gateway before v0.9.5. A routed service names the
    network Traefik reaches it on, or Traefik picks one at random.
    """
    env_file = app / ".env.example"
    env = dict(parse_env(env_file)[0]) if env_file.exists() else {}
    labels_by_service: dict[str, list[str]] = {}
    routed: set[str] = set()
    for path in compose_files(app) + overlay_files(app):
        try:
            data = compose_load(path)
        except yaml.YAMLError:
            continue
        for name, svc in (data.get("services") or {}).items():
            if not isinstance(svc, dict):
                continue
            labels = svc.get("labels") or []
            label_list = labels if isinstance(labels, list) else [f"{k}={v}" for k, v in labels.items()]
            labels_by_service.setdefault(name, []).extend(str(l) for l in label_list)
            for entry in svc.get("ports") or []:
                if _port_has_host_address(entry, env):
                    continue
                known = KNOWN_UNBOUND_PORTS.get(str(app))
                findings.append({"level": "WARN" if known else "FAIL", "rule": "port-no-host-address",
                                 "service": name,
                                 "detail": f"{path.name}: '{entry}' binds to every host address, IPv4 and IPv6 — "
                                           "publish on a *_BIND variable"
                                           + (f" (known: {known})" if known else "")})
    for name, labels in labels_by_service.items():
        enabled = any(re.fullmatch(r"traefik\.enable\s*=\s*['\"]?true['\"]?", l.strip()) for l in labels)
        named = any(l.strip().startswith("traefik.docker.network=") for l in labels)
        if enabled and not named:
            findings.append({"level": "FAIL", "rule": "missing-network-label", "service": name,
                             "detail": "traefik.enable=true without traefik.docker.network — Traefik then "
                                       "takes a random network of the container; name the one it reaches "
                                       "the service on (traefik.docker.network=${TRAEFIK_NETWORK})"})


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

    # `--list-overlays` prints the opt-in files instead. They are deliberately a
    # separate list: they are validated, never counted as part of a stack.
    if "--list-overlays" in sys.argv[1:]:
        for app in find_apps():
            for f in overlay_files(app):
                print(f)
        return 0

    fails = warns = 0
    root_gi = root_gitignore()
    by_app: dict[Path, list[dict]] = {}

    for app in find_apps():
        key = str(app)
        if key in EXCEPT_DIRS:
            continue
        findings: list[dict] = []
        check_files(app, findings, root_gi)
        check_env(app, findings)
        check_env_pins(app, findings)
        check_local_pins(app, findings)
        check_compose(app, findings)
        check_routers(app, findings)
        check_ports_and_labels(app, findings)
        if findings:
            by_app.setdefault(app, []).extend(findings)

    # Runs once over every stack: the shared-network rules are cross-stack and
    # cannot be decided while looking at a single compose file.
    check_shared_network_identity(by_app)

    results: list[tuple[Path, list[dict]]] = [(a, f) for a, f in sorted(by_app.items()) if f]
    for _app, findings in results:
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
