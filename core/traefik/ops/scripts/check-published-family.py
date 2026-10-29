#!/usr/bin/env python3
"""Which address families Traefik is published on, and whether each one keeps
the client address on its way to the container.

Called by validate.sh. A port published without a host address, or on an IPv6
address, accepts IPv6 clients. On an IPv4-only public network Docker relays
such a connection from the bridge gateway, and every access policy, rate limit
and CrowdSec decision then sees the gateway instead of the client. IPv6 is
therefore published only by network-dual-stack.yml, and only where the Docker
daemon forwards IPv6 by NAT rather than through docker-proxy.

Checks, against the effective Compose model — the -f files validate.sh was
given, else COMPOSE_FILE, else docker-compose.yml with its override — and,
when Traefik exists, against the running state:

  ERROR    a port accepts IPv6 while the public network has no IPv6
  ERROR    dual-stack, and the daemon's effective settings keep docker-proxy
           (userland-proxy not false) or disable ip6tables. The daemon is the
           one behind the endpoint Compose uses: `docker info` in the same
           environment (DOCKER_HOST, DOCKER_CONTEXT, current context) names the
           host and the data root, and the local dockerd with that data root is
           the one whose arguments and config file are read
  ERROR    dual-stack, and the daemon's settings cannot be read — unless
           DOCKER_DAEMON_CHECK=manual records that they were checked by hand
  ERROR    dual-stack, and the existing public network is IPv4-only
  PENDING  the running container is published differently from the model —
           `docker compose up -d` recreates it
  PENDING  a docker-proxy process relays an IPv6 port of Traefik
  NOT VERIFIED  the running container was created from other compose files
           than the ones checked, or carries no record of them
  NOT VERIFIED  a check that could not run — no docker-compose.yml in the
           directory, no docker CLI, or Docker refused or did not answer when
           the network or the container was inspected (only Docker's own
           "not found" means absent)

Exit 0 when every check ran and found nothing, 1 on any ERROR, 3 when there is
no ERROR but something is PENDING or NOT VERIFIED. validate.sh reports 3 as a
valid configuration whose security state is not confirmed, and does not block
the update that resolves it. Standard library only.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

DEFAULT_DAEMON_JSON = "/etc/docker/daemon.json"
EXIT_OPEN = 3  # no ERROR, but something PENDING or NOT VERIFIED


def accepts_ipv6(host_ip):
    """A binding without a host address listens on [::] as well."""
    return not host_ip or ":" in host_ip


def evaluated_files(args):
    """The compose files the model comes from, as Compose resolves them:
    explicit -f files, else COMPOSE_FILE, else docker-compose.yml and its
    override file. Compared with the files the running container was created
    from."""
    project = Path(args.project_dir)
    if args.compose_file:
        return [Path(f) for f in args.compose_file]
    listed = os.environ.get("COMPOSE_FILE", "")
    if listed:
        sep = os.environ.get("COMPOSE_PATH_SEPARATOR", ":")
        return [project / f for f in listed.split(sep) if f]
    files = [project / "docker-compose.yml"]
    if (project / "docker-compose.override.yml").is_file():
        files.append(project / "docker-compose.override.yml")
    return files


def same_files(a, b):
    return {os.path.realpath(str(x)) for x in a} == {os.path.realpath(str(x)) for x in b}


def load_model(args):
    if args.compose_json:
        return json.loads(Path(args.compose_json).read_text(encoding="utf-8")), None
    project = Path(args.project_dir)
    files = evaluated_files(args)
    if not args.compose_file and not (project / "docker-compose.yml").is_file():
        return None, f"NOT VERIFIED: no docker-compose.yml in {project} — the published-address checks did not run."
    missing = [str(f) for f in files if not Path(f).is_file()]
    if missing:
        raise SystemExit(f"ERROR: compose file not found: {', '.join(missing)}")
    if shutil.which("docker") is None:
        return None, ("NOT VERIFIED: docker not found — the published-address checks did not run "
                      f"(files: {', '.join(str(f) for f in files)}).")
    cmd = ["docker", "compose"]
    if args.compose_file:
        for f in files:
            cmd += ["-f", str(f)]
    r = subprocess.run(cmd + ["config", "--format", "json"], cwd=project, capture_output=True, text=True)
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

def find_dockerds(proc):
    """Every dockerd process visible here: (pid directory, argv)."""
    found = []
    for entry in sorted(proc.iterdir(), key=lambda p: p.name):
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text(encoding="utf-8").strip() != "dockerd":
                continue
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        found.append((entry, [a.decode("utf-8", "replace") for a in argv if a]))
    return found


VALUE_FLAGS = ("config-file", "data-root")


def flag_value(argv, name):
    """--name=value, --name value (for options that take a value), or a bare boolean --name."""
    for i, a in enumerate(argv):
        if a == f"--{name}":
            nxt = argv[i + 1] if i + 1 < len(argv) else ""
            if name in VALUE_FLAGS:
                return nxt if nxt and not nxt.startswith("-") else None
            return "true"
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


def docker_info(args):
    """The /info of the endpoint Compose uses — DOCKER_HOST, DOCKER_CONTEXT and
    the current context apply to `docker info` exactly as to `docker compose`.
    ('ok', dict) | ('unknown', reason)."""
    if args.docker_info:
        data = json.loads(Path(args.docker_info).read_text(encoding="utf-8"))
        return ("unknown", data["__error__"]) if "__error__" in data else ("ok", data)
    state, out = docker_query(["docker", "info", "--format", "{{json .}}"])
    if state != "ok":
        return "unknown", f"docker info failed: {out}"
    try:
        return "ok", json.loads(out)
    except ValueError:
        return "unknown", "docker info returned no JSON"


def config_location(pid_dir, argv):
    """The daemon.json this dockerd reads, or None when it cannot be located (rootless)."""
    path = flag_value(argv, "config-file")
    if path is not None:
        return path
    try:
        uid = process_uid(pid_dir)
    except OSError:
        uid = None
    return DEFAULT_DAEMON_JSON if uid == 0 else None


def read_config(path):
    """(dict, None) | (None, reason); a file that does not exist is an empty config."""
    p = Path(path)
    if not p.exists():
        return {}, None
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except OSError:
        return None, f"{path} is not readable"
    except ValueError:
        return None, f"{path} is not valid JSON"


def data_root(pid_dir, argv):
    """Where this dockerd keeps its data — unique per daemon on a host — or None."""
    root = flag_value(argv, "data-root")
    if root:
        return root
    path = config_location(pid_dir, argv)
    if path is not None:
        config, _ = read_config(path)
        if config and config.get("data-root"):
            return config["data-root"]
    try:
        uid = process_uid(pid_dir)
    except OSError:
        uid = None
    # Docker's default for a daemon running as root; a rootless daemon's
    # default lies in its user's home and is not derived here.
    return "/var/lib/docker" if uid == 0 else None


def serving_dockerd(proc, info):
    """The local dockerd behind the endpoint, matched by host name and data root.
    ((pid_dir, argv), None) | (None, reason)."""
    name, root = info.get("Name", ""), info.get("DockerRootDir", "")
    if name != socket.gethostname():
        return None, (f"the endpoint Compose uses is the daemon on {name or 'an unnamed host'}, not this host "
                      f"({socket.gethostname()}) — a remote context, DOCKER_HOST or a VM")
    daemons = find_dockerds(proc)
    if not daemons:
        return None, "no dockerd process is visible here (/proc with hidepid, or the daemon runs elsewhere)"
    unresolved = [d for d in daemons if data_root(*d) is None]
    matches = [d for d in daemons if data_root(*d) and os.path.realpath(data_root(*d)) == os.path.realpath(root)]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, f"{len(matches)} dockerd processes name the data root {root}"
    if unresolved:
        return None, ("a dockerd runs without root and without --config-file or --data-root (rootless); "
                      "which daemon serves the endpoint is not determined")
    return None, f"no dockerd on this host has the endpoint's data root {root}"


def daemon_settings(proc, env, args):
    """('safe'|'unsafe'|'unknown', reason) for the daemon Compose talks to."""
    host = env.get("DOCKER_HOST", "")
    if host and not host.startswith("unix://"):
        return "unknown", f"DOCKER_HOST={host} points to a daemon whose process is not on this host"
    state, info = docker_info(args)
    if state != "ok":
        return "unknown", info
    found, reason = serving_dockerd(proc, info)
    if found is None:
        return "unknown", reason
    pid_dir, argv = found

    userland = flag_value(argv, "userland-proxy")
    ip6tables = flag_value(argv, "ip6tables")
    config_path = config_location(pid_dir, argv)
    source = "dockerd arguments"
    config = {}
    if userland is None or ip6tables is None:
        if config_path is None:
            return "unknown", "dockerd runs without root and without --config-file (rootless); its daemon.json is not located"
        config, problem = read_config(config_path)
        if problem:
            return "unknown", problem
        if Path(config_path).exists():
            if started_after(pid_dir, proc, config_path):
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

NOT_FOUND = ("no such network", "no such object", "no such container", "not found")


def docker_query(cmd):
    """('ok', stdout) | ('absent', None) | ('unknown', reason).

    Only Docker's own "does not exist" answer counts as absent. Any other
    failure — no permission on the socket, a daemon that does not answer — is
    unknown, never read as "nothing there".
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "unknown", str(exc)
    if r.returncode == 0:
        return "ok", r.stdout
    detail = (r.stderr or r.stdout).strip()
    if any(marker in detail.lower() for marker in NOT_FOUND):
        return "absent", None
    return "unknown", (detail.splitlines() or [f"exit {r.returncode}"])[-1]


def network_state(args):
    """('ok', enable_ipv6) | ('absent', None) | ('unknown', reason)."""
    if args.network_ipv6 is not None:
        if args.network_ipv6 in ("true", "false"):
            return "ok", args.network_ipv6 == "true"
        return ("absent", None) if args.network_ipv6 == "absent" else ("unknown", "test: network inspect failed")
    state, out = docker_query(["docker", "network", "inspect", "-f", "{{.EnableIPv6}}", args.public_network])
    return (state, out.strip() == "true") if state == "ok" else (state, out)


def container_state(args):
    """('ok', (ports, labels)) | ('absent', None) | ('unknown', reason); a stopped container is absent."""
    if args.running_ports:
        data = json.loads(Path(args.running_ports).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "__error__" in data:
            return "unknown", data["__error__"]
        labels = json.loads(Path(args.running_labels).read_text(encoding="utf-8")) if args.running_labels else None
        return ("absent", None) if data is None else ("ok", (data, labels))
    state, out = docker_query(["docker", "inspect", args.container])
    if state != "ok":
        return state, out
    obj = json.loads(out)[0]
    if not (obj.get("State") or {}).get("Running"):
        return "absent", None
    return "ok", ((obj.get("NetworkSettings") or {}).get("Ports") or {}, (obj.get("Config") or {}).get("Labels") or {})


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
    ap.add_argument("--compose-file", action="append", default=[],
                    help="a compose file as passed to docker compose -f; repeatable")
    ap.add_argument("--public-network", default="proxy-public")
    ap.add_argument("--container", default="traefik-core")
    ap.add_argument("--daemon-check", default="", help="'manual' when the daemon settings were checked by hand")
    ap.add_argument("--compose-json", help="read the Compose model from this file (tests)")
    ap.add_argument("--proc", default="/proc", help="proc filesystem root (tests)")
    ap.add_argument("--docker-info", help="the endpoint's docker info as JSON, or {\"__error__\": reason} (tests)")
    ap.add_argument("--network-ipv6", choices=["true", "false", "absent", "error"], help="network state (tests)")
    ap.add_argument("--running-ports", help="NetworkSettings.Ports as JSON, 'null' when not running, "
                                            "or {\"__error__\": reason} (tests)")
    ap.add_argument("--running-labels", help="Config.Labels of the running container as JSON (tests)")
    ap.add_argument("--no-runtime", action="store_true", help="skip the running-state checks")
    args = ap.parse_args()

    model, note = load_model(args)
    if model is None:
        print(note)
        return EXIT_OPEN

    errors, warnings, pending, unverified = [], [], [], []
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
        state, reason = daemon_settings(proc, os.environ, args)
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
        net_state, net = network_state(args)
        if dual_stack and net_state == "ok" and net is False:
            errors.append(f"network-dual-stack.yml is applied, but the existing network {args.public_network} "
                          "is IPv4-only.\n       Docker cannot add IPv6 to it — docs/ipv6-dual-stack.md, migration guide.")
        elif dual_stack and net_state == "unknown":
            unverified.append(f"the network {args.public_network} could not be inspected: {net}. "
                              "Whether it carries IPv6 is not confirmed.")
        ctr_state, ports = container_state(args)
        if ctr_state == "unknown":
            unverified.append(f"the container {args.container} could not be inspected: {ports}. "
                              "What it is published on is not confirmed.")
        if ctr_state == "ok":
            ports, labels = ports
            deployed = (labels or {}).get("com.docker.compose.project.config_files", "")
            files = evaluated_files(args)
            if labels is not None and not deployed:
                unverified.append(f"{args.container} carries no record of the compose files it was created from; "
                                  "the deployed configuration is not the one checked here.")
            elif labels is not None and not same_files(deployed.split(","), files):
                unverified.append(
                    f"{args.container} was created from {deployed}, but validate.sh evaluated "
                    f"{','.join(str(f) for f in files)}.\n"
                    "         Run validate.sh with the deployment's files (-f ...), or set COMPOSE_FILE in .env\n"
                    "         so that deployment and validation use the same files.")
            want, have = expand(configured), expand(running_bindings(ports))
            if want != have:
                extra = sorted(f"{ip}:{pub}/{proto}" for ip, pub, _, proto in have - want)
                missing = sorted(f"{ip}:{pub}/{proto}" for ip, pub, _, proto in want - have)
                pending.append(
                    f"{args.container} runs with a different publication than configured"
                    f"{' — not in the configuration: ' + ', '.join(extra) if extra else ''}"
                    f"{' — not yet published: ' + ', '.join(missing) if missing else ''}.\n"
                    "         Recreate it: docker compose up -d")
            relays = ipv6_relays(proc, {pub for _, pub, _, _ in configured})
            if relays:
                pending.append(f"docker-proxy relays IPv6 for Traefik ({', '.join(relays)}); "
                               "the client address of those connections is replaced.")

    for w in warnings:
        print(f"WARNING: {w}")
    for p in pending:
        print(f"PENDING: {p}")
    for u in unverified:
        print(f"NOT VERIFIED: {u}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    return EXIT_OPEN if pending or unverified else 0


if __name__ == "__main__":
    sys.exit(main())
