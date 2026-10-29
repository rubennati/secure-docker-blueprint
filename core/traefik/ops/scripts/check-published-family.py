#!/usr/bin/env python3
"""Which address families Traefik is published on, and whether each one keeps
the client address on its way to the container.

Called by validate.sh. A port published without a host address, or on an IPv6
address, accepts IPv6 clients. On an IPv4-only public network Docker relays
such a connection from the bridge gateway, and every access policy, rate limit
and CrowdSec decision then sees the gateway instead of the client. IPv6 is
therefore published only by network-dual-stack.yml, and only where the Docker
daemon forwards IPv6 by NAT rather than through docker-proxy.

Checks, against the effective Compose model (overrides and COMPOSE_FILE
included) and, when Traefik exists, against the running state:

  ERROR    a port accepts IPv6 while the public network has no IPv6
  ERROR    dual-stack, and the daemon's effective settings keep docker-proxy
           (userland-proxy not false) or disable ip6tables
  ERROR    dual-stack, and the daemon's settings cannot be read — unless
           DOCKER_DAEMON_CHECK=manual records that they were checked by hand
  ERROR    dual-stack, and the existing public network is IPv4-only
  WARNING  the running container is published differently from the model —
           `docker compose up -d` recreates it
  WARNING  a docker-proxy process relays an IPv6 port of Traefik

Without docker-compose.yml in the directory, or without the docker CLI, it
says so and checks nothing: no deployment can start there either.

Exit 0 when nothing is an ERROR, 1 otherwise. Standard library only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_DAEMON_JSON = "/etc/docker/daemon.json"


def accepts_ipv6(host_ip):
    """A binding without a host address listens on [::] as well."""
    return not host_ip or ":" in host_ip


def load_model(args):
    if args.compose_json:
        return json.loads(Path(args.compose_json).read_text(encoding="utf-8")), None
    project = Path(args.project_dir)
    if not (project / "docker-compose.yml").is_file():
        return None, f"NOTE: no docker-compose.yml in {project} — published-address checks skipped."
    if shutil.which("docker") is None:
        return None, "WARNING: docker not found — the published-address checks did not run."
    r = subprocess.run(["docker", "compose", "config", "--format", "json"],
                       cwd=project, capture_output=True, text=True)
    if r.returncode != 0:
        detail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
        raise SystemExit(f"ERROR: docker compose config failed in {project}: {detail[0]}")
    return json.loads(r.stdout), None


def configured_bindings(model):
    out = set()
    for p in (model.get("services", {}).get("traefik", {}).get("ports") or []):
        out.add((p.get("host_ip") or "", str(p.get("published")), str(p.get("target")), p.get("protocol") or "tcp"))
    return out


# --- the Docker daemon's effective settings ---------------------------------

def find_dockerd(proc):
    for entry in sorted(proc.iterdir(), key=lambda p: p.name):
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text(encoding="utf-8").strip() != "dockerd":
                continue
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        return entry, [a.decode("utf-8", "replace") for a in argv if a]
    return None, None


def flag_value(argv, name):
    """--name=value, --name value, or a bare boolean --name."""
    for i, a in enumerate(argv):
        if a == f"--{name}":
            nxt = argv[i + 1] if i + 1 < len(argv) else ""
            return nxt if nxt and not nxt.startswith("-") and name == "config-file" else "true"
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return None


def as_bool(value):
    return str(value).strip().lower() not in ("false", "0", "no")


def process_uid(pid_dir):
    for line in (pid_dir / "status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Uid:"):
            return int(line.split()[1])
    return None


def started_after(pid_dir, proc, path):
    """True when the file changed after the daemon started (it reads it once)."""
    try:
        start_ticks = int((pid_dir / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[19])
        btime = next(int(l.split()[1]) for l in (proc / "stat").read_text(encoding="utf-8").splitlines()
                     if l.startswith("btime "))
        started = btime + start_ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError, StopIteration):
        return False
    return Path(path).stat().st_mtime > started


def daemon_settings(proc, env):
    """('safe'|'unsafe'|'unknown', reason)."""
    host = env.get("DOCKER_HOST", "")
    if host and not host.startswith("unix://"):
        return "unknown", f"DOCKER_HOST={host} points to a daemon whose process is not on this host"
    pid_dir, argv = find_dockerd(proc)
    if pid_dir is None:
        return "unknown", "no dockerd process is visible here (remote context, Docker Desktop, or /proc with hidepid)"

    userland = flag_value(argv, "userland-proxy")
    ip6tables = flag_value(argv, "ip6tables")
    config_path = flag_value(argv, "config-file")
    source = "dockerd arguments"
    if config_path is None:
        try:
            uid = process_uid(pid_dir)
        except OSError:
            uid = None
        if uid != 0:
            return "unknown", "dockerd runs without root and without --config-file (rootless); its daemon.json is not located"
        config_path = DEFAULT_DAEMON_JSON

    config = {}
    if userland is None or ip6tables is None:
        path = Path(config_path)
        if path.exists():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except OSError:
                return "unknown", f"{config_path} is not readable"
            except ValueError:
                return "unknown", f"{config_path} is not valid JSON"
            if started_after(pid_dir, proc, path):
                return "unknown", f"{config_path} changed after the daemon started — restart Docker to apply it"
            source = config_path if userland is None and ip6tables is None else f"{config_path} and dockerd arguments"
        else:
            source = f"Docker defaults ({config_path} does not exist)"

    eff_userland = as_bool(userland) if userland is not None else as_bool(config.get("userland-proxy", True))
    eff_ip6tables = as_bool(ip6tables) if ip6tables is not None else as_bool(config.get("ip6tables", True))
    if eff_userland:
        return "unsafe", f"userland-proxy is enabled ({source}) — IPv6 clients still arrive through docker-proxy"
    if not eff_ip6tables:
        return "unsafe", f"ip6tables is disabled ({source}) — published IPv6 ports are not forwarded to the container"
    return "safe", source


# --- the running state ------------------------------------------------------

def network_ipv6(args):
    if args.network_ipv6 is not None:
        return None if args.network_ipv6 == "absent" else args.network_ipv6 == "true"
    r = subprocess.run(["docker", "network", "inspect", "-f", "{{.EnableIPv6}}", args.public_network],
                       capture_output=True, text=True)
    return None if r.returncode != 0 else r.stdout.strip() == "true"


def running_ports(args):
    """The container's NetworkSettings.Ports, or None when it is not running."""
    if args.running_ports:
        return json.loads(Path(args.running_ports).read_text(encoding="utf-8"))
    r = subprocess.run(["docker", "inspect", "-f", "{{json .State.Running}} {{json .NetworkSettings.Ports}}",
                        args.container], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    running, ports = r.stdout.strip().split(" ", 1)
    return json.loads(ports) if running == "true" else None


def running_bindings(ports):
    out = set()
    for key, binds in (ports or {}).items():
        target, proto = key.split("/")
        for b in binds or []:
            out.add((b.get("HostIp") or "", str(b.get("HostPort")), target, proto))
    return out


def expand(bindings):
    """A binding without a host address is both 0.0.0.0 and ::."""
    out = set()
    for ip, pub, target, proto in bindings:
        for each in (("0.0.0.0", "::") if not ip else (ip.strip("[]"),)):
            out.add((each, pub, target, proto))
    return out


def ipv6_relays(proc, published):
    """docker-proxy processes that listen on an IPv6 host address for one of these ports."""
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text(encoding="utf-8").strip() != "docker-proxy":
                continue
            argv = [a.decode("utf-8", "replace") for a in (entry / "cmdline").read_bytes().split(b"\0") if a]
        except OSError:
            continue
        opts = {argv[i]: argv[i + 1] for i in range(len(argv) - 1) if argv[i].startswith("-")}
        if ":" in opts.get("-host-ip", "") and opts.get("-host-port") in published:
            found.append(f"{opts.get('-proto', 'tcp')} [{opts['-host-ip']}]:{opts['-host-port']}")
    return sorted(set(found))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--public-network", default="proxy-public")
    ap.add_argument("--container", default="traefik-core")
    ap.add_argument("--daemon-check", default="", help="'manual' when the daemon settings were checked by hand")
    ap.add_argument("--compose-json", help="read the Compose model from this file (tests)")
    ap.add_argument("--proc", default="/proc", help="proc filesystem root (tests)")
    ap.add_argument("--network-ipv6", choices=["true", "false", "absent"], help="network state (tests)")
    ap.add_argument("--running-ports", help="NetworkSettings.Ports as JSON, or 'null' when not running (tests)")
    ap.add_argument("--no-runtime", action="store_true", help="skip the running-state checks")
    args = ap.parse_args()

    model, note = load_model(args)
    if model is None:
        print(note)
        return 0

    errors, warnings = [], []
    proc = Path(args.proc)
    configured = configured_bindings(model)
    dual_stack = bool(model.get("networks", {}).get("public", {}).get("enable_ipv6"))

    v6 = sorted(f"{ip or '*'}:{pub}/{proto}" for ip, pub, _, proto in configured if accepts_ipv6(ip))
    if v6 and not dual_stack:
        errors.append(
            f"Traefik is published on IPv6 ({', '.join(v6)}), but the public network is IPv4-only.\n"
            "       IPv6 clients would reach it as the Docker bridge gateway, a private address.\n"
            "       Bind to IPv4 (TRAEFIK_BIND_V4) or apply network-dual-stack.yml with its prerequisites.")

    if dual_stack:
        state, reason = daemon_settings(proc, os.environ)
        if state == "unsafe":
            errors.append(f"dual-stack needs userland-proxy false and ip6tables enabled: {reason}.\n"
                          "       Set both in the daemon configuration and restart Docker (docs/ipv6-dual-stack.md).")
        elif state == "unknown" and args.daemon_check == "manual":
            warnings.append(f"Docker daemon settings declared by DOCKER_DAEMON_CHECK=manual, not verified: {reason}.")
        elif state == "unknown":
            errors.append(
                f"the Docker daemon's settings cannot be checked here: {reason}.\n"
                "       This is not a finding that they are wrong. Confirm on the daemon's host that\n"
                "       userland-proxy is false and ip6tables is not disabled, then set\n"
                "       DOCKER_DAEMON_CHECK=manual in .env to record it.")

    if not args.no_runtime:
        net = network_ipv6(args)
        if dual_stack and net is False:
            errors.append(f"network-dual-stack.yml is applied, but the existing network {args.public_network} "
                          "is IPv4-only.\n       Docker cannot add IPv6 to it — docs/ipv6-dual-stack.md, migration guide.")
        ports = running_ports(args)
        if ports is not None:
            want, have = expand(configured), expand(running_bindings(ports))
            if want != have:
                extra = sorted(f"{ip}:{pub}/{proto}" for ip, pub, _, proto in have - want)
                missing = sorted(f"{ip}:{pub}/{proto}" for ip, pub, _, proto in want - have)
                warnings.append(
                    f"{args.container} runs with a different publication than configured"
                    f"{' — not in the configuration: ' + ', '.join(extra) if extra else ''}"
                    f"{' — not yet published: ' + ', '.join(missing) if missing else ''}.\n"
                    "         Recreate it: docker compose up -d")
            relays = ipv6_relays(proc, {pub for _, pub, _, _ in configured})
            if relays:
                warnings.append(f"docker-proxy relays IPv6 for Traefik ({', '.join(relays)}); "
                                "the client address of those connections is replaced.")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
