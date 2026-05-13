#!/usr/bin/env python3
"""
Security baseline checker for secure-docker-blueprint.

Validates every docker-compose.yml in core/, apps/, business/, monitoring/
against the mandatory rules defined in docs/standards/security-baseline.md.

Rules enforced (FAIL = blocks CI):
  FAIL  no-new-privileges:true must be in security_opt of every service
  FAIL  privileged: true is forbidden
  FAIL  direct /var/run/docker.sock mount on non-proxy services

Informational (WARN = reported, does not block CI):
  WARN  network_mode: host
  WARN  pid: host

──────────────────────────────────────────────────────────────────────────────
DOCUMENTED EXCEPTIONS
──────────────────────────────────────────────────────────────────────────────
Each exception entry must carry three fields:
  reason       — why the control cannot be applied here
  alternatives — other mitigations or approaches that were evaluated
  risk         — explicit risk acceptance statement

Add a new exception here only after reviewing the deviation. Never suppress a
finding without completing all three fields.
"""

import sys
import yaml
from pathlib import Path

# ── Exception type ─────────────────────────────────────────────────────────────
# Each value is a dict with keys: reason, alternatives, risk
Exception = dict[str, str]

# ── Documented exceptions ─────────────────────────────────────────────────────
# Format: { "relative/path": { "service-name": Exception } }

# Services allowed to mount the Docker socket directly.
# All other services must use a socket proxy (core/traefik/docker-socket-proxy).
SOCKET_EXCEPTIONS: dict[str, dict[str, Exception]] = {
    "core/traefik": {
        "docker-socket-proxy": {
            "reason":       "This service IS the socket proxy — it exists specifically to expose a "
                            "filtered Docker API to other services so they never need direct socket access.",
            "alternatives": "There is no upstream proxy to proxy through; this is the root of the "
                            "proxy chain. Read-only socket mount is not sufficient — the proxy needs "
                            "write access to manage containers.",
            "risk":         "Accepted and by design. The proxy filters the API surface to a minimal "
                            "allow-list. All other services use this proxy, not the raw socket.",
        },
    },
    "core/portainer": {
        "socket-proxy": {
            "reason":       "This service IS the socket proxy for the Portainer CE stack — it "
                            "exposes a filtered Docker API to the Portainer container so that "
                            "Portainer itself never touches the raw socket.",
            "alternatives": "There is no upstream proxy to route through; this is the proxy layer. "
                            "Read-only socket mount (:ro) is applied to limit write access.",
            "risk":         "Accepted and by design. Portainer CE is constrained to the filtered "
                            "API surface exposed by this proxy.",
        },
    },
    "core/dockhand": {
        "socket-proxy": {
            "reason":       "This service IS the socket proxy for the Dockhand stack — it exposes "
                            "a filtered Docker API to the Dockhand application so it never "
                            "touches the raw socket directly.",
            "alternatives": "There is no upstream proxy to route through; this is the proxy layer. "
                            "Read-only socket mount (:ro) is applied.",
            "risk":         "Accepted and by design. Dockhand is constrained to the filtered API "
                            "surface exposed by this proxy.",
        },
    },
    "core/hawser": {
        "hawser": {
            "reason":       "Hawser is a remote Docker agent that proxies Docker API access to "
                            "Dockhand over an encrypted outbound tunnel. It requires direct socket "
                            "access because it acts as the socket proxy itself for remote hosts.",
            "alternatives": "A socket proxy in front of Hawser was evaluated — tracked upstream as "
                            "PR #52 (https://github.com/Finsys/hawser/pull/52). Hawser does not yet "
                            "support connecting to a TCP socket proxy. Exception to be removed once "
                            "the upstream PR is merged and the image updated.",
            "risk":         "Accepted — medium risk, mitigated by design. Hawser does not expose "
                            "a port; it connects outbound only (works behind NAT/Tailscale). "
                            "The API surface exposed to Dockhand is what Dockhand requests, not "
                            "an open relay. Will be revisited when PR #52 lands.",
        },
    },
    "core/portainer-agent": {
        "agent": {
            "reason":       "Portainer Agent requires direct Docker socket access to manage containers, "
                            "images, and volumes on behalf of the Portainer Business server.",
            "alternatives": "Portainer does not support routing socket access through an API proxy. "
                            "The agent protocol speaks directly to the Docker daemon.",
            "risk":         "Accepted — low risk in a homelab context. The agent only runs when "
                            "Portainer Business is active. Network access to the agent port (9001) "
                            "is restricted to the internal proxy network.",
        },
    },
    "monitoring/beszel": {
        "agent": {
            "reason":       "Beszel agent needs Docker socket to enumerate containers and collect "
                            "per-container CPU/memory/network metrics.",
            "alternatives": "Beszel has no built-in support for a socket proxy. Read-only socket "
                            "mount (:ro) is used to reduce the attack surface.",
            "risk":         "Accepted — low risk. The socket is mounted read-only. The agent has "
                            "no write path to the Docker daemon.",
        },
    },
    "monitoring/beszel-agent": {
        "agent": {
            "reason":       "Beszel standalone agent needs Docker socket to enumerate containers and "
                            "collect per-container CPU/memory/network metrics.",
            "alternatives": "Beszel has no built-in support for a socket proxy. Read-only socket "
                            "mount (:ro) is used to reduce the attack surface.",
            "risk":         "Accepted — low risk. The socket is mounted read-only. The agent has "
                            "no write path to the Docker daemon.",
        },
    },
}

# Services allowed to skip no-new-privileges.
NO_NEW_PRIVILEGES_EXCEPTIONS: dict[str, dict[str, Exception]] = {
    "apps/nextcloud": {
        "app": {
            "reason":       "The Nextcloud Docker entrypoint runs as root on first boot to set "
                            "correct ownership on the data directory and write config.php. "
                            "no-new-privileges:true prevents the setuid/setgid calls this requires "
                            "and causes the container to fail at startup.",
            "alternatives": "Upstream issue tracked by the Nextcloud Docker project. A custom "
                            "entrypoint that pre-creates directories with correct permissions was "
                            "considered but rejected — it would need to be maintained across "
                            "Nextcloud image updates and is fragile.",
            "risk":         "Accepted — medium risk, mitigated by network isolation. The app "
                            "container sits on an internal network with no direct internet exposure. "
                            "Privilege escalation would require first compromising the PHP process "
                            "through a Nextcloud vulnerability.",
        },
        "cron": {
            "reason":       "The cron container uses the same Docker image and entrypoint as the "
                            "app container. The same first-run ownership logic applies.",
            "alternatives": "Same as app — no viable alternative without forking the upstream image.",
            "risk":         "Same as app — accepted, mitigated by network isolation.",
        },
    },
}

# Services allowed to use network_mode: host or pid: host.
HOST_MODE_EXCEPTIONS: dict[str, dict[str, Exception]] = {
    "core/dnsmasq": {
        "dnsmasq": {
            "reason":       "A DNS server must bind to port 53 on the host's physical network "
                            "interfaces. Docker bridge networking does not allow a container to "
                            "receive broadcast/multicast DNS queries from other hosts on the LAN.",
            "alternatives": "macvlan networking was evaluated — it would give the container its own "
                            "IP but adds routing complexity and breaks container-to-host "
                            "communication. host networking is simpler and standard for DNS daemons.",
            "risk":         "Accepted — the container process is dnsmasq with a minimal config. "
                            "The host network exposure is limited to port 53 (UDP/TCP) and the "
                            "dnsmasq admin interface, which is disabled.",
        },
    },
    "monitoring/beszel": {
        "agent": {
            "reason":       "Beszel agent must collect host-level network interface statistics "
                            "(bytes in/out per interface). These are only visible from inside the "
                            "host network namespace.",
            "alternatives": "Reading /proc/net/dev from a bind-mount was evaluated but Beszel's "
                            "metric collection library reads the network namespace directly, not "
                            "via /proc. No configuration option exists to change this.",
            "risk":         "Accepted — low risk. The agent is read-only and monitoring-only. "
                            "It does not listen on any port. host network exposure is one-directional "
                            "(outbound to the Beszel hub only).",
        },
    },
    "monitoring/beszel-agent": {
        "agent": {
            "reason":       "Same as monitoring/beszel — standalone agent variant with identical "
                            "requirements for host network namespace access.",
            "alternatives": "Same as monitoring/beszel.",
            "risk":         "Same as monitoring/beszel — accepted, low risk.",
        },
    },
}


def get_exception(table: dict[str, dict[str, Exception]], path: Path, svc: str) -> Exception | None:
    """Return the exception dict if (path, service) is in the exception table, else None."""
    key = str(path.parent)
    return table.get(key, {}).get(svc)


def fmt_exception(exc: Exception) -> str:
    """Format a multi-field exception into a single summary string for CI output."""
    return (
        f"reason: {exc['reason']} | "
        f"alternatives: {exc['alternatives']} | "
        f"risk: {exc['risk']}"
    )


def check_compose(path: Path) -> list[dict]:
    """Return a list of findings for a single compose file."""
    findings = []

    try:
        with open(path) as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [{"level": "FAIL", "service": "—", "rule": "YAML parse error", "detail": str(e)}]

    if not doc or "services" not in doc:
        return []

    services = doc.get("services") or {}

    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue

        # ── FAIL: no-new-privileges ──────────────────────────────────────────
        exc = get_exception(NO_NEW_PRIVILEGES_EXCEPTIONS, path, svc_name)
        if exc:
            findings.append({
                "level": "SKIP",
                "service": svc_name,
                "rule": "no-new-privileges",
                "detail": fmt_exception(exc),
            })
        else:
            security_opts = svc.get("security_opt") or []
            has_nnp = any("no-new-privileges" in str(opt) for opt in security_opts)
            if not has_nnp:
                findings.append({
                    "level": "FAIL",
                    "service": svc_name,
                    "rule": "no-new-privileges missing",
                    "detail": "Add 'security_opt: [no-new-privileges:true]' — required on every service",
                })

        # ── FAIL: privileged: true ───────────────────────────────────────────
        if svc.get("privileged") is True:
            findings.append({
                "level": "FAIL",
                "service": svc_name,
                "rule": "privileged: true",
                "detail": "Forbidden. Add a documented exception with reason/alternatives/risk if unavoidable.",
            })

        # ── FAIL: direct Docker socket mount ────────────────────────────────
        exc = get_exception(SOCKET_EXCEPTIONS, path, svc_name)
        if exc:
            findings.append({
                "level": "SKIP",
                "service": svc_name,
                "rule": "direct socket mount",
                "detail": fmt_exception(exc),
            })
        else:
            volumes = svc.get("volumes") or []
            for vol in volumes:
                if "/var/run/docker.sock" in str(vol):
                    findings.append({
                        "level": "FAIL",
                        "service": svc_name,
                        "rule": "direct socket mount",
                        "detail": "Use socket proxy instead. Add to SOCKET_EXCEPTIONS with reason/alternatives/risk if unavoidable.",
                    })

        # ── WARN: network_mode / pid host ────────────────────────────────────
        exc = get_exception(HOST_MODE_EXCEPTIONS, path, svc_name)
        if exc:
            findings.append({
                "level": "SKIP",
                "service": svc_name,
                "rule": "network_mode/pid: host",
                "detail": fmt_exception(exc),
            })
        else:
            if svc.get("network_mode") == "host":
                findings.append({
                    "level": "WARN",
                    "service": svc_name,
                    "rule": "network_mode: host",
                    "detail": "Bypasses network isolation — add to HOST_MODE_EXCEPTIONS with reason/alternatives/risk if intentional.",
                })
            if svc.get("pid") == "host":
                findings.append({
                    "level": "WARN",
                    "service": svc_name,
                    "rule": "pid: host",
                    "detail": "Shares host PID namespace — add to HOST_MODE_EXCEPTIONS with reason/alternatives/risk if intentional.",
                })

    return findings


def main() -> int:
    roots = ["core", "apps", "business", "monitoring"]
    compose_files = sorted(
        p for root in roots
        for p in Path(root).rglob("docker-compose.yml")
    )

    total_files = 0
    total_fails = 0
    total_warns = 0
    total_skips = 0
    all_findings: list[tuple[Path, list[dict]]] = []

    for path in compose_files:
        findings = check_compose(path)
        relevant = [f for f in findings if f["level"] != "SKIP"]
        if relevant:
            all_findings.append((path, findings))
        elif any(f["level"] == "SKIP" for f in findings):
            all_findings.append((path, findings))
        total_files += 1
        total_fails += sum(1 for f in findings if f["level"] == "FAIL")
        total_warns += sum(1 for f in findings if f["level"] == "WARN")
        total_skips += sum(1 for f in findings if f["level"] == "SKIP")

    # ── GitHub Actions Job Summary ────────────────────────────────────────────
    summary_lines = ["## Security Baseline\n"]
    if total_fails > 0:
        summary_lines.append(
            f"❌ {total_files} files checked — **{total_fails} failure(s)**, "
            f"{total_warns} warning(s), {total_skips} accepted exception(s)\n"
        )
    else:
        summary_lines.append(
            f"✅ {total_files} files checked — no violations "
            f"({total_warns} warning(s), {total_skips} accepted exception(s))\n"
        )

    violations = [(p, f) for p, findings in all_findings for f in findings if f["level"] != "SKIP"]
    if violations:
        summary_lines.append("### Violations\n")
        summary_lines.append("| Level | File | Service | Rule | Detail |")
        summary_lines.append("|---|---|---|---|---|")
        for path, f in violations:
            icon = {"FAIL": "🔴", "WARN": "🟡"}.get(f["level"], "ℹ️")
            summary_lines.append(
                f"| {icon} {f['level']} | `{path}` | `{f['service']}` "
                f"| {f['rule']} | {f['detail']} |"
            )

    skips = [(p, f) for p, findings in all_findings for f in findings if f["level"] == "SKIP"]
    if skips:
        summary_lines.append("\n### Accepted exceptions\n")
        summary_lines.append("| File | Service | Rule | Reason | Alternatives considered | Risk acceptance |")
        summary_lines.append("|---|---|---|---|---|---|")
        for path, f in skips:
            # detail is formatted as "reason: ... | alternatives: ... | risk: ..."
            parts = {k.strip(): v.strip() for part in f["detail"].split(" | ") for k, v in [part.split(": ", 1)]}
            summary_lines.append(
                f"| `{path}` | `{f['service']}` | {f['rule']} "
                f"| {parts.get('reason', '—')} "
                f"| {parts.get('alternatives', '—')} "
                f"| {parts.get('risk', '—')} |"
            )

    summary_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if summary_path:
        summary_path.write_text("\n".join(summary_lines))

    # ── CLI output ────────────────────────────────────────────────────────────
    printed_any = False
    for path, findings in all_findings:
        for f in findings:
            if f["level"] == "SKIP":
                continue
            icon = {"FAIL": "✖", "WARN": "⚠"}.get(f["level"], "·")
            print(f"  {icon} [{f['level']}] {path} » {f['service']} — {f['rule']}")
            print(f"         {f['detail']}")
            printed_any = True

    if not printed_any:
        print(f"  ✓ {total_files} files checked, no violations")

    print(f"\n  {total_files} files  ·  {total_fails} failures  ·  {total_warns} warnings  ·  {total_skips} skipped")
    return 1 if total_fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
