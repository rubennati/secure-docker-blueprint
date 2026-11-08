#!/usr/bin/env python3
"""
Stack status for secure-docker-blueprint: what is pinned, what upstream has
published since, and what the pinned images carry.

One row per stack, for someone deciding whether to use it or update it:

  Pinned       the tag of the stack's primary image and when upstream released
               that version
  Newest       the newest tag upstream publishes in the same shape as the pin,
               and when it was released
  Upstream     whether the upstream repository is archived, and when it last
               published a stable release
  CRITICAL ·   fixable findings in the stack's images, read from the Trivy
  HIGH         reports of the same workflow run; every image of the stack
               counts, a database or a cache as much as the application. Per
               image they are split by where they sit: the base system's
               packages, the application's libraries, or a compiled program
               shipped in the image

This reports and never judges. It exits 0 whatever it finds; it exits non-zero
only when it cannot run at all. A lookup that fails is shown in the row as not
determinable, with the reason, never as "current".

Where a tag's version is read from:

  The primary image is the one whose `image:` line uses the pin variable that
  LIFECYCLE.md shows (APP_TAG, else APP_IMAGE, else the first *_TAG, *_IMAGE or
  *_VERSION — lifecycle-report.py's pinned_version()). Images are resolved the
  way scripts/ci/list-images.sh resolves them, so the names match the scanned
  ones: `${VAR}` from the sibling .env.example, `${VAR:-default}` from the
  inline default.

  "Same shape" means the same prefix (`v`), the same number of numeric parts
  and the same suffix (`-alpine`, `-apache`). A suffix that is a commit hash
  matches any hash. A suffix with digits of its own (`-alpine3.20`,
  `14-vectorchord1.1.1`) and a tag without a version (`latest`) cannot be
  compared, and the row says so rather than guessing.

  Dates come from the upstream release where one matches. The upstream
  repository is the first GitHub repository in the `## Source` section of the
  stack's UPSTREAM.md; a release matches when its tag carries the same version
  numbers as the image tag (`v2.4.29` for `2.4.29-alpine`). An image tag is
  rebuilt and pushed again for a base-image update, so a registry date says
  when the image was built, not when the version was released. Only where no
  release matches is the registry date used, and the data says so
  (`pinned_date_source: image`). GitHub is read with GITHUB_TOKEN when it is
  set; without it the anonymous limit of 60 requests an hour covers a few
  stacks only, and the rest show the registry date.

  Docker Hub records when a tag was last pushed; other registries are read
  through the OCI distribution API, from the image config's `created`.

The data file (--json) is what the repository commits as upstream-status.json:
the maintainer writes it at a pin move and before a release, and
lifecycle-report.py renders it. With --stack, an existing file is updated for
the named stacks only.

Usage:
  upstream-status.py [--results-dir DIR] [--json FILE] [--markdown FILE]
                     [--stack KEY ...]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent

_spec = importlib.util.spec_from_file_location("lifecycle_report", HERE / "lifecycle-report.py")
lifecycle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lifecycle)

USER_AGENT = "secure-docker-blueprint-stack-status"
TIMEOUT = 20
# Docker Hub lists tags newest first; five pages of 100 reach far enough back
# for every repository here, and bound the requests per stack.
HUB_PAGES = 5
OCI_PAGES = 30
STALE_AFTER = timedelta(days=365)
REPO_URL = "https://github.com/rubennati/secure-docker-blueprint"

# ---------------------------------------------------------------------------
# Image references
# ---------------------------------------------------------------------------

IMAGE_LINE = re.compile(r"^\s+image:\s*(.+?)\s*$")
VAR = re.compile(r"\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
DEFAULT = re.compile(r"\$\{[A-Za-z0-9_]+:-([^}]*)\}")


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        env[key.strip()] = value
    return env


def resolve(raw: str, env: dict[str, str]) -> str | None:
    """An `image:` value as list-images.sh resolves it, or None if it does not."""
    value = raw.split("#", 1)[0].strip().strip("'\"").replace(" ", "")
    # envsubst first (plain ${VAR}), then the inline default — the same order,
    # so a `${VAR:-default}` resolves to its default, as the scan saw it.
    value = VAR.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), value)
    value = DEFAULT.sub(lambda m: m.group(1), value)
    if not value or "$" in value or "-local:" in value:
        return None
    return value


def stack_images(stack: Path) -> list[tuple[str, str]]:
    """[(raw image value, resolved image)] across the stack's production files."""
    env = read_env(stack / ".env.example")
    seen: dict[str, str] = {}
    files = sorted(stack.glob("*.yml"))
    files.sort(key=lambda p: p.name != "docker-compose.yml")
    for compose in files:
        if compose.name == "docker-compose.local.yml":
            continue
        for line in compose.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = IMAGE_LINE.match(line)
            if not m:
                continue
            image = resolve(m.group(1), env)
            if image and image not in seen:
                seen[image] = m.group(1)
    return [(raw, image) for image, raw in seen.items()]


def primary_image(stack: Path, images: list[tuple[str, str]]) -> str | None:
    """The image whose line uses the pin variable LIFECYCLE.md shows."""
    if not images:
        return None
    pinned = lifecycle.pinned_version(stack).strip("`")
    var = pinned.split("=", 1)[0] if "=" in pinned else ""
    if var:
        for raw, image in images:
            if re.search(r"\$\{?" + re.escape(var) + r"\b", raw):
                return image
        if local_build(stack, var):
            return None
    return images[0][1]


def local_build(stack: Path, var: str) -> bool:
    """True when the pin variable names an image the stack builds itself."""
    compose = stack / "docker-compose.yml"
    if not compose.is_file():
        return False
    pattern = re.compile(r"^\s+image:\s*\S*-local:\$\{?" + re.escape(var) + r"\b", re.M)
    return bool(pattern.search(compose.read_text(encoding="utf-8", errors="replace")))


def split_ref(image: str) -> tuple[str, str, str]:
    """(registry, repository, tag) — Docker Hub as `docker.io`, `library/` added."""
    base = image.split("@", 1)[0]
    head, sep, tail = base.rpartition(":")
    if sep and "/" not in tail:
        name, tag = head, tail
    else:
        name, tag = base, ""
    first, slash, rest = name.partition("/")
    if slash and ("." in first or ":" in first or first == "localhost"):
        registry, repo = first, rest
    else:
        registry, repo = "docker.io", name
    if registry in ("docker.io", "index.docker.io", "registry-1.docker.io"):
        registry = "docker.io"
        if "/" not in repo:
            repo = f"library/{repo}"
    return registry, repo, tag


# ---------------------------------------------------------------------------
# Tag shapes
# ---------------------------------------------------------------------------

# Each repetition of the prefix group ends in a separator, so a run of letters
# can be split only one way and matching stays linear (no nested `+…*`).
SHAPE = re.compile(
    r"^(?P<prefix>(?:[A-Za-z]+[-_.])*[A-Za-z]*)(?P<core>\d+(?:\.\d+)*)(?P<suffix>.*)$")
HASH_SUFFIX = re.compile(r"^-[0-9a-f]{7,40}$")
REVISION_SUFFIX = re.compile(r"^-(\d+)$")


def shape(tag: str) -> tuple[str, int, int, str] | None:
    """(prefix, numeric parts, digits of the first part, suffix key), or None.

    The digit count of the first part keeps a date-style tag (`2021.11.28`,
    `20220121`) from passing as a newer release of `2.8.4` or `261029`.
    """
    m = SHAPE.match(tag)
    if not m:
        return None
    suffix = m.group("suffix")
    if HASH_SUFFIX.match(suffix):
        key = "-<hash>"
    elif REVISION_SUFFIX.match(suffix):
        key = "-<revision>"
    elif re.search(r"\d", suffix):
        return None
    else:
        key = suffix
    core = m.group("core")
    return m.group("prefix"), core.count(".") + 1, len(core.split(".")[0]), key


def version(tag: str) -> tuple[int, ...]:
    m = SHAPE.match(tag)
    if not m:
        return ()
    parts = [int(p) for p in m.group("core").split(".")]
    revision = REVISION_SUFFIX.match(m.group("suffix"))
    if revision:
        parts.append(int(revision.group(1)))
    return tuple(parts)


def newest(pin: str, tags: list[str]) -> str | None:
    """The highest tag in the pin's shape; None when the pin has no shape."""
    want = shape(pin)
    if want is None:
        return None
    same = [t for t in tags if shape(t) == want]
    if pin not in same:
        same.append(pin)
    return max(same, key=version)


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

class RegistryError(RuntimeError):
    """A registry answered in a way this script cannot use."""


def http_get(url: str, headers: dict[str, str] | None = None) -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read(), {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(15 * (attempt + 1))
                continue
            exc.headers_lower = {k.lower(): v for k, v in exc.headers.items()}
            raise
    raise RegistryError(f"{url}: rate limited")


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    # Reproducible builds stamp the epoch; that is no publication date.
    return when if when.year >= 2000 else None


class DockerHub:
    API = "https://hub.docker.com/v2/repositories"

    def tags(self, repo: str) -> dict[str, datetime | None]:
        found: dict[str, datetime | None] = {}
        url = f"{self.API}/{repo}/tags?page_size=100&ordering=last_updated"
        for _ in range(HUB_PAGES):
            body, _ = http_get(url)
            data = json.loads(body)
            for t in data.get("results") or []:
                found[t["name"]] = parse_date(t.get("tag_last_pushed") or t.get("last_updated"))
            url = data.get("next")
            if not url:
                break
        return found

    def date(self, repo: str, tag: str) -> datetime | None:
        body, _ = http_get(f"{self.API}/{repo}/tags/{urllib.parse.quote(tag)}")
        data = json.loads(body)
        return parse_date(data.get("tag_last_pushed") or data.get("last_updated"))


MANIFEST_TYPES = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


class Oci:
    """Any registry speaking the OCI distribution API, anonymously."""

    def __init__(self, registry: str):
        self.base = f"https://{registry}/v2"
        self.tokens: dict[str, str] = {}

    def _get(self, repo: str, path: str, accept: str | None = None) -> tuple[bytes, dict[str, str]]:
        url = path if path.startswith("http") else f"{self.base}/{repo}/{path}"
        headers = {"Accept": accept} if accept else {}
        if repo in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[repo]}"
        try:
            return http_get(url, headers)
        except urllib.error.HTTPError as exc:
            challenge = getattr(exc, "headers_lower", {}).get("www-authenticate", "")
            if exc.code != 401 or repo in self.tokens or not challenge.lower().startswith("bearer"):
                raise
            params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
            realm = params.pop("realm", "")
            params.setdefault("scope", f"repository:{repo}:pull")
            body, _ = http_get(f"{realm}?{urllib.parse.urlencode(params)}")
            data = json.loads(body)
            self.tokens[repo] = data.get("token") or data.get("access_token") or ""
            headers["Authorization"] = f"Bearer {self.tokens[repo]}"
            return http_get(url, headers)

    def tags(self, repo: str) -> dict[str, datetime | None]:
        found: dict[str, datetime | None] = {}
        path = "tags/list?n=1000"
        for _ in range(OCI_PAGES):
            body, headers = self._get(repo, path)
            for tag in json.loads(body).get("tags") or []:
                found[tag] = None
            link = headers.get("link", "")
            m = re.search(r"<([^>]+)>", link)
            if not m:
                break
            nxt = m.group(1)
            path = nxt if nxt.startswith("http") else f"https://{self.base.split('/')[2]}{nxt}"
        return found

    def date(self, repo: str, tag: str) -> datetime | None:
        body, _ = self._get(repo, f"manifests/{tag}", MANIFEST_TYPES)
        manifest = json.loads(body)
        created = (manifest.get("annotations") or {}).get("org.opencontainers.image.created")
        if parse_date(created):
            return parse_date(created)
        if "manifests" in manifest:
            entries = manifest["manifests"]
            pick = next((m for m in entries
                         if (m.get("platform") or {}).get("architecture") == "amd64"
                         and (m.get("platform") or {}).get("os") == "linux"), None)
            pick = pick or (entries[0] if entries else None)
            if not pick:
                return None
            body, _ = self._get(repo, f"manifests/{pick['digest']}", MANIFEST_TYPES)
            manifest = json.loads(body)
        config = (manifest.get("config") or {}).get("digest")
        if not config:
            return None
        body, _ = self._get(repo, f"blobs/{config}")
        return parse_date(json.loads(body).get("created"))


GITHUB_REPO = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
RELEASE_PAGES = 3


def github_repo(stack: Path) -> str | None:
    """`owner/repo` whose releases name the stack's versions.

    A `**Releases:**` line in UPSTREAM.md's `## Source` wins — for an image whose
    versions are released in another repository than its source (the Portainer
    agent follows Portainer's releases). Otherwise the first GitHub repository
    of the section.
    """
    path = stack / "UPSTREAM.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    source = text.split("## Source", 1)
    if len(source) < 2:
        return None
    section = source[1].split("\n## ", 1)[0]
    releases = re.search(r"\*\*Releases:\*\*\s*(\S+)", section)
    m = GITHUB_REPO.search(releases.group(1) if releases else "") or GITHUB_REPO.search(section)
    if not m:
        return None
    name = m.group(2)
    return f"{m.group(1)}/{name[:-4] if name.endswith('.git') else name}"


def release_version(tag: str) -> tuple[int, ...]:
    """The version numbers in a release tag or an image tag, suffix ignored.

    The run with the most parts wins, so a digit inside a name (`n8n@2.46.6`)
    is not read as the version."""
    runs = re.findall(r"\d+(?:\.\d+)*", tag)
    if not runs:
        return ()
    best = max(runs, key=lambda r: r.count("."))
    return tuple(int(p) for p in best.split("."))


class GitHub:
    API = "https://api.github.com/repos"

    def __init__(self, token: str | None):
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def repo(self, name: str) -> dict:
        """{archived, releases: [(tag, date, prerelease, name)]} newest first."""
        body, _ = http_get(f"{self.API}/{name}", self.headers)
        info = json.loads(body)
        releases = []
        for page in range(1, RELEASE_PAGES + 1):
            body, _ = http_get(f"{self.API}/{name}/releases?per_page=100&page={page}",
                               self.headers)
            batch = json.loads(body)
            for r in batch:
                if r.get("draft"):
                    continue
                releases.append((r.get("tag_name") or "",
                                 parse_date(r.get("published_at")),
                                 bool(r.get("prerelease")),
                                 r.get("name") or ""))
            if len(batch) < 100:
                break
        return {"archived": bool(info.get("archived")), "releases": releases}


def release_date(releases: list, tag: str | None) -> datetime | None:
    """The date of the release whose version numbers match the image tag."""
    want = release_version(tag or "")
    if not want:
        return None
    for name, when, *_ in releases:
        if release_version(name) == want and when:
            return when
    return None


CHANNEL = re.compile(r"\b(LTS|STS)\b")


def release_filter(releases: list, pinned: str):
    """Which registry versions may be offered as newer: a test on a version tuple.

    A GitHub pre-release (n8n's next line) is not offered unless upstream also
    published that version as a stable release. Next to a pin upstream names
    LTS (Portainer), only versions upstream released as LTS are offered."""
    stable, pre, lts, pinned_lts = set(), set(), set(), False
    want = release_version(pinned)
    for name, _, prerelease, *rest in releases:
        v = release_version(name)
        if not v:
            continue
        (pre if prerelease else stable).add(v)
        m = CHANNEL.search(rest[0] if rest else "")
        if m and m.group(1) == "LTS":
            lts.add(v)
            pinned_lts = pinned_lts or v == want
    skip = pre - stable
    if pinned_lts:
        return lambda v: v in lts and v not in skip
    return lambda v: v not in skip


def step_down(row: dict, allowed) -> None:
    """Re-pick the newest registry tag among the versions `allowed` admits."""
    tags = row.get("_tags")
    pin = row["pinned"]
    if not tags or not row["newest"] or allowed(release_version(row["newest"])):
        return
    want = shape(pin)
    same = [t for t in tags if shape(t) == want and allowed(release_version(t))]
    best = max(same + [pin], key=version)
    row["newest"] = best
    row["status"] = "current" if version(best) == version(pin) else "behind"
    row["newest_date"] = row["pinned_date"] if best == pin else tags.get(best)


def upstream(stack: Path, row: dict, gh: GitHub | None) -> None:
    """Add the release dates, the archive flag and the last stable release."""
    row.update({"repo": github_repo(stack), "archived": None, "last_release": None,
                "pinned_date_source": "image" if row["pinned_date"] else None,
                "newest_date_source": "image" if row["newest_date"] else None})
    if not row["repo"] or gh is None:
        return
    try:
        data = gh.repo(row["repo"])
    except (urllib.error.URLError, OSError, ValueError, KeyError, RegistryError):
        return
    row["archived"] = data["archived"]
    step_down(row, release_filter(data["releases"], row["pinned"]))
    stable = [when for _, when, pre, *_ in data["releases"] if not pre and when]
    row["last_release"] = max(stable) if stable else None
    if row["reason"] == "built locally":
        want = release_version(row["pinned"])
        same = [(release_version(n), n, w) for n, w, pre, *_ in data["releases"]
                if not pre and w and len(release_version(n)) == len(want)]
        if want and same:
            best = max(same)
            row["newest"] = best[1].lstrip("v") if not row["pinned"].startswith("v") else best[1]
            row["status"] = "current" if best[0] <= want else "behind"
            row["reason"] = ""
    for key in ("pinned", "newest"):
        when = release_date(data["releases"], row[key] if row[key] != "—" else None)
        if when:
            row[f"{key}_date"] = when
            row[f"{key}_date_source"] = "release"


_clients: dict[str, object] = {}


def client(registry: str):
    if registry not in _clients:
        _clients[registry] = DockerHub() if registry == "docker.io" else Oci(registry)
    return _clients[registry]


def lookup(image: str) -> dict:
    """Pinned and newest tag with their dates, or the reason they are unknown."""
    registry, repo, tag = split_ref(image)
    row = {"image": image, "pinned": tag or "—", "pinned_date": None,
           "newest": None, "newest_date": None, "status": "undetermined", "reason": ""}
    if not tag:
        row["reason"] = "pinned by digest or without a tag"
        return row
    if shape(tag) is None:
        row["reason"] = f"`{tag}` carries no comparable version"
    reg = client(registry)
    try:
        tags = reg.tags(repo)
        row["_tags"] = tags
        if shape(tag) is not None:
            best = newest(tag, list(tags))
            row["newest"] = best
            row["status"] = "current" if version(best) == version(tag) else "behind"
        row["pinned_date"] = tags.get(tag) or reg.date(repo, tag)
        if row["newest"] and row["newest"] != tag:
            row["newest_date"] = tags.get(row["newest"]) or reg.date(repo, row["newest"])
        elif row["newest"]:
            row["newest_date"] = row["pinned_date"]
    except (urllib.error.URLError, OSError, ValueError, KeyError, RegistryError) as exc:
        detail = f"HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
        row["status"] = "undetermined"
        row["reason"] = f"{registry} did not answer ({detail})"
    return row


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

# Where a finding sits, from Trivy's result class and type: the base system's
# packages, the application's libraries, or a compiled program in the image.
AREAS = ("system", "libraries", "programs")
PROGRAM_TYPES = {"gobinary", "rustbinary"}


def area(result: dict) -> str:
    if result.get("Class") == "os-pkgs":
        return "system"
    if result.get("Type") in PROGRAM_TYPES:
        return "programs"
    return "libraries"


def scan_findings(results_dir: Path | None) -> dict[str, dict] | None:
    """{image: {"CRITICAL": {CVE}, "HIGH": {CVE}, "areas": {area: {sev: {CVE}}}}}."""
    if results_dir is None or not results_dir.is_dir():
        return None
    found: dict[str, dict[str, set[str]]] = {}
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        image = data.get("ArtifactName")
        if not image:
            continue
        sev = found.setdefault(image, {
            "CRITICAL": set(), "HIGH": set(),
            "areas": {a: {"CRITICAL": set(), "HIGH": set()} for a in AREAS}})
        for result in data.get("Results") or []:
            where = sev["areas"][area(result)]
            for vuln in result.get("Vulnerabilities") or []:
                level = vuln.get("Severity")
                if level in ("CRITICAL", "HIGH") and vuln.get("VulnerabilityID"):
                    sev[level].add(vuln["VulnerabilityID"])
                    where[level].add(vuln["VulnerabilityID"])
    return found


def stack_findings(images: list[str], scan: dict | None) -> dict | None:
    if scan is None:
        return None
    critical: set[str] = set()
    high: set[str] = set()
    unscanned = []
    per_image = {}
    for image in images:
        if image not in scan:
            unscanned.append(image)
            continue
        critical |= scan[image]["CRITICAL"]
        high |= scan[image]["HIGH"]
        counts = {a: [len(scan[image]["areas"][a]["CRITICAL"]),
                      len(scan[image]["areas"][a]["HIGH"])] for a in AREAS}
        # An area without findings is left out; an image without any keeps {}.
        per_image[image] = {a: c for a, c in counts.items() if any(c)}
    return {"critical": len(critical), "high": len(high), "unscanned": unscanned,
            "images": per_image}


# ---------------------------------------------------------------------------
# Collect and render
# ---------------------------------------------------------------------------

def stacks(selected: list[str]) -> list[Path]:
    found = []
    for cat in lifecycle.CATEGORIES:
        cat_dir = Path(cat)
        if not cat_dir.is_dir():
            continue
        for stack in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
            key = f"{cat}/{stack.name}"
            if key in lifecycle.EXCEPT or (selected and key not in selected):
                continue
            found.append(stack)
    return found


def collect(selected: list[str], results_dir: Path | None) -> list[dict]:
    scan = scan_findings(results_dir)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    gh = GitHub(token)
    rows = []
    for stack in stacks(selected):
        key = stack.as_posix()
        images = stack_images(stack)
        primary = primary_image(stack, images)
        pin = lifecycle.pinned_version(stack).strip("`")
        var, _, value = pin.partition("=")
        if primary is None and value and local_build(stack, var):
            # Built from upstream source here: no registry tag to compare, so
            # the version is read against the upstream releases alone.
            row = {"image": None, "pinned": value, "pinned_date": None, "newest": None,
                   "newest_date": None, "status": "undetermined",
                   "reason": "built locally"}
        elif primary is None:
            row = {"image": None, "pinned": "—", "pinned_date": None, "newest": None,
                   "newest_date": None, "status": "undetermined",
                   "reason": "host-installed" if not lifecycle.has_compose(stack)
                   else "no resolvable image"}
        else:
            row = lookup(primary)
        upstream(stack, row, gh)
        row.pop("_tags", None)
        row["stack"] = key
        row["images"] = [image for _, image in images]
        row["findings"] = stack_findings(row["images"], scan)
        readme = stack / "README.md"
        row["assessed"] = readme.is_file() and bool(
            lifecycle.OPEN_FINDINGS.search(readme.read_text(encoding="utf-8", errors="replace")))
        rows.append(row)
    return rows


def day(when: datetime | None) -> str:
    return when.strftime("%Y-%m-%d") if when else "—"


def quiet(row: dict, now: datetime) -> bool:
    """Nothing new for twelve months: no stable release on GitHub and no newer
    image. Both count, because some projects publish images without GitHub
    releases and some keep releasing on GitHub after the image moved."""
    dates = [row.get("last_release"), row["newest_date"],
             row["pinned_date"] if row["status"] == "current" else None]
    dates = [d for d in dates if d]
    return bool(dates and now - max(dates) > STALE_AFTER)


def notes(row: dict, now: datetime) -> list[str]:
    out = []
    if row["status"] == "behind":
        out.append("newer version upstream")
    if row["reason"]:
        out.append(f"not determinable: {row['reason']}")
    if row.get("archived"):
        out.append("upstream repository archived")
    if quiet(row, now):
        out.append("no release in over 12 months")
    f = row["findings"]
    if f and f["unscanned"]:
        out.append(f"{len(f['unscanned'])} image(s) not scanned")
    return out


def render_markdown(rows: list[dict], now: datetime, scanned: bool) -> str:
    behind = sum(1 for r in rows if r["status"] == "behind")
    undetermined = sum(1 for r in rows if r["status"] == "undetermined")
    with_critical = sum(1 for r in rows if r["findings"] and r["findings"]["critical"])
    lines = [
        "# Stack status",
        "",
        (f"Generated {now.strftime('%Y-%m-%d %H:%M')} UTC by "
         "[`scripts/ci/upstream-status.py`]"
         f"({REPO_URL}/blob/main/scripts/ci/upstream-status.py) in the weekly Trivy run. "
         "This issue is overwritten on every run; it reports and decides nothing."),
        "",
        (f"{len(rows)} stacks · {behind} with a newer upstream version · "
         f"{undetermined} not determinable · "
         + (f"{with_critical} with fixable CRITICAL findings" if scanned
            else "findings not available in this run")),
        "",
        ("- **Pinned** — the tag of the stack's primary image in `main`, and when that "
         "version was released upstream."),
        ("- **Newest** — the newest upstream tag in the same shape as the pin "
         "(same prefix, number of parts and suffix), and when it was released. "
         "Where no upstream release matches, the date is the image's build date."),
        ("- **CRITICAL · HIGH** — findings with a published fix, in every image of the "
         "stack. A linked count means the stack README assesses the CRITICAL ones "
         "under *Open findings*."),
        "",
    ]
    for cat in lifecycle.CATEGORIES:
        part = [r for r in rows if r["stack"].split("/", 1)[0] == cat]
        if not part:
            continue
        lines += [f"## `{cat}/`", "",
                  "| Stack | Pinned | Published | Newest | Published | CRITICAL · HIGH | Note |",
                  "|---|---|---|---|---|---|---|"]
        for r in part:
            f = r["findings"]
            if f is None:
                counts = "—"
            else:
                counts = f"{f['critical']} · {f['high']}"
                if f["critical"] and r["assessed"]:
                    counts = f"[{counts}]({REPO_URL}/blob/main/{r['stack']}/README.md#open-findings)"
            newest_tag = f"`{r['newest']}`" if r["newest"] else "—"
            lines.append(
                f"| [`{r['stack']}`]({REPO_URL}/tree/main/{r['stack']}) "
                f"| `{r['pinned']}` | {day(r['pinned_date'])} "
                f"| {newest_tag} | {day(r['newest_date'])} "
                f"| {counts} | {'; '.join(notes(r, now))} |")
        lines.append("")
    return "\n".join(lines)


def json_row(r: dict, now: datetime) -> dict:
    def d(when):
        return day(when) if when else None
    return {
        "checked": day(now),
        "image": r["image"],
        "pinned": r["pinned"],
        "pinned_date": d(r["pinned_date"]),
        "pinned_date_source": r.get("pinned_date_source"),
        "newest": r["newest"],
        "newest_date": d(r["newest_date"]),
        "newest_date_source": r.get("newest_date_source"),
        "status": r["status"],
        "reason": r["reason"] or None,
        "repo": r.get("repo"),
        "archived": r.get("archived"),
        "last_release": d(r.get("last_release")),
        "quiet": quiet(r, now),
        "images": r["images"],
        "findings": r["findings"],
    }


def render_json(rows: list[dict], now: datetime, previous: dict | None = None) -> str:
    """The data file; with `previous`, the stacks not in `rows` are kept as they were."""
    stacks_out = dict((previous or {}).get("stacks") or {})
    for r in rows:
        stacks_out[r["stack"]] = json_row(r, now)
    payload = {"stacks": dict(sorted(stacks_out.items()))}
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path,
                    help="Trivy's per-image JSON reports; without it no findings are shown")
    ap.add_argument("--json", type=Path, help="write the data here")
    ap.add_argument("--markdown", type=Path, help="write the table here")
    ap.add_argument("--stack", action="append", default=[],
                    help="limit to this stack key (repeatable)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    rows = collect(args.stack, args.results_dir)
    scanned = scan_findings(args.results_dir) is not None
    markdown = render_markdown(rows, now, scanned)
    if args.json:
        previous = None
        if args.stack and args.json.is_file():
            previous = json.loads(args.json.read_text(encoding="utf-8"))
        args.json.write_text(render_json(rows, now, previous), encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown + "\n", encoding="utf-8")
    if not args.json and not args.markdown:
        print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
