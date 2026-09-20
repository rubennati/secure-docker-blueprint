#!/usr/bin/env python3
"""
Validate every opt-in compose overlay as its own deployment variant.

An overlay is a second file applied on top of a stack — an optional feature
(`activitypub.yml`) or an alternative to something the base file sets
(`network-host.yml`, `docker-compose.gpu.yml`). Overlays were checked by nothing:
stack discovery skips them on purpose, and check-baseline.py imports that
discovery.

What matters is not the overlay file but the deployment it produces. A block
carrying no image adds no service, yet it can still hand a service the Docker
socket, publish a datastore port, set `privileged: true`, or clear the memory
ceiling with `!reset`. Judging the overlay file alone misses all of that.

So each overlay is evaluated as:

    canonical production compose  +  that one overlay

`docker compose config` performs the merge, which is the only way to get the
semantics right — overlay merge rules differ per key, and `!reset` / `!override`
change them again. The same mechanism already validates stacks in ci.yml.
Reimplementing it in YAML here would be an approximation that disagrees with
what an operator actually runs.

Each overlay is a separate variant. They are not combined with each other: some
are mutually exclusive, and a stack's canonical service inventory is unchanged by
any of them.

Reported per variant:
  * a merge Compose refuses — including an overlay patching a service the stack
    does not define, which Compose rejects as a project with no image
  * a service the overlay adds that breaks a mandatory baseline rule
  * a service the overlay *changes* into breaking one — the regression case

Rules come from check-baseline.py (no-new-privileges, privileged, direct socket
mount, host namespaces) and from the runtime ceilings in this file. Services the
overlay leaves untouched are not re-reported: the canonical run already covers
them.

Usage:
  python3 scripts/ci/check-overlays.py [--require-docker] [github-summary-path]

Needs Docker. Without it the checker reports that it could not run and exits 0,
so a contributor without Docker is not blocked; CI passes --require-docker, which
turns that into a failure.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("check_structure", HERE / "check-structure.py")
_structure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_structure)

_spec_b = importlib.util.spec_from_file_location("check_baseline", HERE / "check-baseline.py")
_baseline = importlib.util.module_from_spec(_spec_b)
_spec_b.loader.exec_module(_baseline)

DATASTORE_NAMES = _structure.DATASTORE_NAMES
BAD_TAG = _structure.BAD_TAG


def docker_available() -> bool:
    try:
        return subprocess.run(["docker", "compose", "version"],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def overlay_env(app: Path, overlay: Path) -> Path | None:
    """A sibling env example belonging to this overlay, by the repository's naming.

    An overlay that carries its own variables names them alongside itself:
    `docker-compose.agent.yml` is started with `--env-file .env.agent`, so the
    committed example is `.env.agent.example`. Without staging it, the overlay's
    own tag resolves to nothing and the image silently reads as `image:` with an
    empty tag — coverage that looks present and is not.
    """
    stem = overlay.stem.removeprefix("docker-compose.").removeprefix("docker-compose")
    candidate = app / f".env.{stem}.example"
    return candidate if stem and candidate.exists() else None


COMMENTED = re.compile(r"^\s*#\s*([A-Z_][A-Z0-9_]*)=(.*)$")
MISSING = re.compile(r"required variable ([A-Z_][A-Z0-9_]*) is missing a value")


def env_sources(app: Path, extra: list[Path]) -> str:
    """The committed example values a variant resolves from."""
    parts = []
    if (app / ".env.example").exists():
        parts.append((app / ".env.example").read_text(encoding="utf-8", errors="replace"))
    for ov in extra:
        side = overlay_env(app, ov)
        if side:
            parts.append(side.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def enable_commented(text: str, var: str) -> str | None:
    """Uncomment `# VAR=value`, if the example ships one.

    An overlay routinely needs a variable the base example leaves commented:
    enabling IPv6 means uncommenting the two subnet lines, which is exactly what
    core/traefik/docs/ipv6-dual-stack.md tells the operator to do. Supplying the
    documented example value is what validating that variant means. A variable
    with no example anywhere still fails.
    """
    for line in text.splitlines():
        m = COMMENTED.match(line)
        if m and m.group(1) == var:
            return f"{text}\n{m.group(1)}={m.group(2)}"
    return None


def run_config(app: Path, files: list[Path], env_text: str) -> tuple[dict | None, str]:
    """One `docker compose config` against a staged environment.

    A pre-existing `.env` is left untouched and used as-is; it is gitignored and
    belongs to whoever created it.
    """
    args: list[str] = []
    for f in files:
        args += ["-f", f.name]

    env_file, staged = app / ".env", False
    if not env_file.exists():
        env_file.write_text(env_text)
        staged = True
    try:
        proc = subprocess.run(["docker", "compose", *args, "config", "--format", "json"],
                              cwd=app, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    finally:
        if staged:
            env_file.unlink(missing_ok=True)

    if proc.returncode != 0:
        detail = " ".join(line for line in proc.stderr.splitlines()
                          if line.strip() and not line.startswith("time="))
        return None, detail[:400]
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"config output is not JSON: {exc}"


def effective_config(app: Path, extra: list[Path],
                     env_text: str | None = None) -> tuple[dict | None, str, str]:
    """The configuration Compose produces, and the environment it resolved from.

    Variables an overlay needs but the example leaves commented are enabled one
    at a time, each only because the merge named it. The resolved environment is
    returned so the base can be rendered from the same values — otherwise the two
    sides differ by their environment rather than by the overlay, and every
    service reads as changed.
    """
    files = _structure.compose_files(app) + extra
    text = env_sources(app, extra) if env_text is None else env_text

    for _ in range(12):
        data, error = run_config(app, files, text)
        if data is not None:
            return data, "", text
        var = MISSING.search(error)
        if not var:
            return None, error, text
        enabled = enable_commented(text, var.group(1))
        if enabled is None:
            return None, error, text
        text = enabled
    return None, "environment did not converge", text


def runtime_findings(name: str, svc: dict, label: str) -> list[dict]:
    """Mandatory runtime rules, applied to an effective service definition.

    These mirror the FAIL rules check-structure.py applies to a canonical compose
    file. They are repeated against the merged result because an overlay can
    remove any of them — `deploy: {resources: !reset null}` leaves a service with
    no ceiling at all, and the canonical file still looks correct.
    """
    out: list[dict] = []

    image = str(svc.get("image") or "")
    tag = image.split(":")[-1].split("@")[0] if ":" in image else ""
    if image and not tag:
        # Either no tag at all, or a variable that resolved to nothing. Both mean
        # the running image is not the one the repository claims to pin.
        out.append({"level": "FAIL", "service": name, "rule": "unresolved-tag",
                    "detail": f"{label}: {image!r} carries no usable tag — the pin did not resolve"})
    elif tag and BAD_TAG.match(tag):
        out.append({"level": "FAIL", "service": name, "rule": "latest-tag",
                    "detail": f"{label}: {image} is not reproducible — pin a full version"})

    if svc.get("privileged"):
        out.append({"level": "FAIL", "service": name, "rule": "privileged",
                    "detail": f"{label}: privileged: true — full host access"})

    if name in DATASTORE_NAMES:
        nets = svc.get("networks") or {}
        netnames = list(nets) if isinstance(nets, dict) else list(nets)
        if "proxy-public" in netnames:
            out.append({"level": "FAIL", "service": name, "rule": "db-exposed",
                        "detail": f"{label}: datastore joins proxy-public"})
        if svc.get("ports"):
            out.append({"level": "FAIL", "service": name, "rule": "db-exposed",
                        "detail": f"{label}: datastore publishes a host port"})

    # `docker compose config` normalises deploy.resources.limits.memory to
    # `deploy.resources.limits.memory` in bytes, and mem_limit to `mem_limit`.
    deploy_limits = ((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}
    has_memory = bool(deploy_limits.get("memory") or svc.get("mem_limit"))
    has_pids = deploy_limits.get("pids") is not None or svc.get("pids_limit") is not None
    absent = [k for k, present in (("memory", has_memory), ("pids", has_pids)) if not present]
    if absent:
        out.append({"level": "FAIL", "service": name, "rule": "no-resources",
                    "detail": f"{label}: no {' and no '.join(absent)} limit — unbounded container"})

    if has_memory and svc.get("memswap_limit") is None:
        out.append({"level": "FAIL", "service": name, "rule": "no-swap-policy",
                    "detail": f"{label}: memory limit with no memswap_limit — swap left implicit"})

    return out


def check_variant(app: Path, overlay: Path) -> tuple[list[dict], bool]:
    """Findings for one stack + one overlay, and whether it touched any service.

    Every supported overlay is merge-validated. The service rules then apply to
    what the merge actually adds or changes, so a network-only overlay is proved
    to resolve without inventing service checks it could never fail.
    """
    merged, error, env_text = effective_config(app, [overlay])
    if merged is None:
        return [{"level": "FAIL", "service": "—", "rule": "overlay-invalid",
                 "detail": f"{overlay.name}: Compose refuses the merged project — {error}"}], False

    base, base_error, _ = effective_config(app, [], env_text=env_text)
    if base is None:
        return [{"level": "FAIL", "service": "—", "rule": "base-invalid",
                 "detail": f"the stack does not resolve for {overlay.name} — {base_error}"}], False

    base_services = base.get("services") or {}
    findings: list[dict] = []
    touched = False

    for name, svc in (merged.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        # Untouched by this overlay — the canonical run already judged it.
        if name in base_services and base_services[name] == svc:
            continue
        touched = True
        state = "adds" if name not in base_services else "changes"
        label = f"{overlay.name} {state} {name}"
        findings += runtime_findings(name, svc, label)
        # The security baseline, from its own checker, so the exception tables and
        # the wording stay in one place. `overlay` gives the stack directory the
        # exceptions are keyed on.
        for f in _baseline.check_compose(overlay, doc={"services": {name: svc}}):
            if f["level"] == "SKIP":
                continue
            findings.append({**f, "detail": f"{label}: {f['detail']}"})

    return findings, touched


def main() -> int:
    argv = sys.argv[1:]
    require_docker = "--require-docker" in argv
    summary_path = next((a for a in argv if not a.startswith("--")), None)

    if not docker_available():
        msg = ("Docker is not available — no overlay was validated. "
               "CI runs this with --require-docker.")
        print(f"\n  {'❌' if require_docker else '🟡'}  {msg}\n")
        return 1 if require_docker else 0

    apps = [app for app in _structure.find_apps() if _structure.overlay_files(app)]
    results: list[tuple[Path, list[dict]]] = []
    variants = service_variants = 0

    for app in apps:
        findings: list[dict] = []
        for overlay in _structure.overlay_files(app):
            variants += 1
            found, touched = check_variant(app, overlay)
            service_variants += touched
            findings += found
        if findings:
            results.append((app, findings))

    fails = sum(1 for _a, fs in results for f in fs if f["level"] == "FAIL")

    print("\n  Opt-in overlay variants\n")
    for app, findings in results:
        print(f"  {app}")
        for f in findings:
            mark = "🔴" if f["level"] == "FAIL" else "🟡"
            print(f"     {mark} {f['rule']}  [{f['service']}]  {f['detail']}")
    if not results:
        print("  ✓ every variant resolves and stays within the baseline\n")

    print(f"\n  {'❌' if fails else '✅'} {len(apps)} stack(s) with overlays  ·  "
          f"{variants} variant(s) merge-validated  ·  "
          f"{service_variants} with service-level checks  ·  {fails} failure(s)\n")

    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("## Overlay variants\n\n")
            fh.write(f"{variants} variant(s) across {len(apps)} stack(s), "
                     f"{service_variants} affecting services — {fails} failure(s).\n\n")
            for app, findings in results:
                for f in findings:
                    fh.write(f"- `{app}` **{f['rule']}** [{f['service']}] — {f['detail']}\n")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
