#!/usr/bin/env python3
"""Which address families Traefik is published on, and whether each one keeps
the client address on its way to the container.

Called by validate.sh. A port published without a host address, or on an IPv6
address, accepts IPv6 clients. On an IPv4-only public network Docker relays
such a connection from the bridge gateway, and every access policy, rate limit
and CrowdSec decision then sees the gateway instead of the client. IPv6 is
therefore published only through TRAEFIK_BIND_V6 — rendered into
config/published-ports.yml — with network-dual-stack.yml applied, and only
where the Docker daemon forwards IPv6 by NAT rather than through docker-proxy.

Checks, against the effective Compose model — the -f files validate.sh was
given, else COMPOSE_FILE, else docker-compose.yml with its override — and,
when Traefik exists, against the running state:

  ERROR    a port accepts IPv6 while the public network has no IPv6
  ERROR    the model gives the public network no gw_priority above every
           other network of the service — the published ports are then mapped
           to Traefik's address on whichever network Docker picks (Compose
           order, alphabetical: crowdsec-security), not to the one whose
           address family is checked here
  ERROR    dual-stack, and the daemon's effective settings keep docker-proxy
           (userland-proxy not false) or disable ip6tables. The daemon is the
           one behind the endpoint Compose uses — resolved as the Docker CLI
           does: the context DOCKER_CONTEXT names, else DOCKER_HOST, else the
           current context; the context "default" is DOCKER_HOST when it is
           set. The endpoint must be a Unix socket on which exactly one local
           dockerd listens, and that dockerd's host name and data root must be
           the ones `docker info` reports for the endpoint; only then are its
           arguments and config file read
  ERROR    dual-stack, and the daemon's settings cannot be read — unless
           DOCKER_DAEMON_CHECK=manual records that they were checked by hand
  ERROR    dual-stack, and the existing public network is IPv4-only
  PENDING  the running container is published differently from the model —
           `docker compose up -d` recreates it
  PENDING  the running container's public endpoint does not carry the highest
           gateway priority — created before gw_priority; `docker compose up -d`
           recreates it
  NOT VERIFIED  the running container reports no gateway priority per endpoint
           (Docker Engine before 28.0)
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
import re
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
    """Same files in the same order — a later file overrides an earlier one, so
    the same set in another order is another configuration."""
    return [os.path.realpath(str(x)) for x in a] == [os.path.realpath(str(x)) for x in b]


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


def gateway_priorities(model):
    """The gw_priority of every network of the traefik service, 0 where none
    is given; None when the service lists no networks (a fixture without
    them, or a model Compose could not normalise)."""
    nets = model.get("services", {}).get("traefik", {}).get("networks")
    if nets is None:
        return None
    if isinstance(nets, list):
        return {str(n): 0 for n in nets}
    return {name: int((cfg or {}).get("gw_priority") or 0) for name, cfg in nets.items()}


def gateway_endpoint_problem(priorities, public_key="public"):
    """None when `public_key` carries a priority strictly above every other
    network, else the reason."""
    if public_key not in priorities:
        return f"the traefik service does not join the network '{public_key}'"
    own = priorities[public_key]
    higher = sorted(n for n, p in priorities.items() if n != public_key and p >= own)
    if higher:
        return (f"'{public_key}' has gw_priority {own}, not above "
                + ", ".join(f"'{n}' ({priorities[n]})" for n in higher))
    return None


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


DEFAULT_SOCKETS = ("/var/run/docker.sock", "/run/docker.sock")


def docker_endpoint(args, env):
    """The endpoint Compose uses, in the Docker CLI's order: the context named by
    DOCKER_CONTEXT, else DOCKER_HOST, else the context `docker context show`
    names. The context "default" is DOCKER_HOST when that is set.
    ('ok', url) | ('unknown', reason)."""
    if args.docker_endpoint:
        return "ok", args.docker_endpoint
    name = env.get("DOCKER_CONTEXT", "")
    if (not name or name == "default") and env.get("DOCKER_HOST"):
        return "ok", env["DOCKER_HOST"]
    if not name:
        state, out = docker_query(["docker", "context", "show"])
        if state != "ok":
            return "unknown", f"docker context show failed: {out}"
        name = out.strip()
    state, out = docker_query(["docker", "context", "inspect", name])
    if state != "ok":
        return "unknown", f"docker context inspect {name} failed: {out}"
    try:
        return "ok", json.loads(out)[0]["Endpoints"]["docker"]["Host"]
    except (ValueError, LookupError, TypeError):
        return "unknown", f"the context {name} names no Docker endpoint"


def host_values(argv):
    """Every -H/--host value in a dockerd command line."""
    out = []
    for i, a in enumerate(argv):
        if a in ("-H", "--host") and i + 1 < len(argv):
            out.append(argv[i + 1])
        elif a.startswith(("-H=", "--host=")):
            out.append(a.split("=", 1)[1])
    return out


def dockerd_sockets(pid_dir, argv):
    """The Unix sockets this dockerd listens on: its -H values, else "hosts" in
    its config file, else Docker's default. fd:// is systemd's docker.socket,
    whose default is /run/docker.sock."""
    hosts = host_values(argv)
    if not hosts:
        path = config_location(pid_dir, argv)
        config = read_config(path)[0] if path else None
        hosts = (config or {}).get("hosts") or ["unix:///var/run/docker.sock"]
    paths = []
    for h in hosts:
        if h.startswith("fd://"):
            paths.extend(DEFAULT_SOCKETS)
        elif h.startswith("unix://"):
            paths.append(h[len("unix://"):])
    return {os.path.realpath(p) for p in paths}


def serving_dockerd(proc, info, endpoint_path):
    """The local dockerd behind the endpoint: the one process that listens on
    the endpoint's socket, on this host, with the data root the endpoint
    reports. ((pid_dir, argv), None) | (None, reason)."""
    name, root = info.get("Name", ""), info.get("DockerRootDir", "")
    if name != socket.gethostname():
        return None, (f"the endpoint Compose uses is the daemon on {name or 'an unnamed host'}, not this host "
                      f"({socket.gethostname()}) — a remote context, DOCKER_HOST or a VM")
    daemons = find_dockerds(proc)
    if not daemons:
        return None, "no dockerd process is visible here (/proc with hidepid, or the daemon runs elsewhere)"
    want = os.path.realpath(endpoint_path)
    listening = [d for d in daemons if want in dockerd_sockets(*d)]
    if not listening:
        return None, (f"no dockerd on this host listens on {endpoint_path} — a forwarded or foreign socket, "
                      "or a daemon started differently than its command line shows")
    if len(listening) > 1:
        return None, f"{len(listening)} dockerd processes claim the socket {endpoint_path}"
    found = listening[0]
    own_root = data_root(*found)
    if own_root is None:
        return None, ("the dockerd on that socket runs without root and without --config-file or --data-root "
                      "(rootless); its data root is not determined")
    if os.path.realpath(own_root) != os.path.realpath(root):
        return None, (f"the dockerd listening on {endpoint_path} keeps its data in {own_root}, "
                      f"but the endpoint reports {root} — they are not the same daemon")
    return found, None


def daemon_settings(proc, env, args):
    """('safe'|'unsafe'|'unknown', reason) for the daemon Compose talks to."""
    state, endpoint = docker_endpoint(args, env)
    if state != "ok":
        return "unknown", endpoint
    if not endpoint.startswith("unix://"):
        return "unknown", f"the endpoint Compose uses is {endpoint}, not the socket of a daemon on this host"
    state, info = docker_info(args)
    if state != "ok":
        return "unknown", info
    found, reason = serving_dockerd(proc, info, endpoint[len("unix://"):])
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

def network_absent(name):
    """Docker's answers that this network does not exist, and nothing else."""
    n = re.escape(name)
    return [rf"(error response from daemon: )?network {n} not found", rf"error: no such network: {n}"]


def container_absent(name):
    """Docker's answers that this container does not exist, and nothing else."""
    n = re.escape(name)
    return [rf"error: no such object: {n}", rf"(error response from daemon: )?no such container: {n}"]


def docker_query(cmd, absent=()):
    """('ok', stdout) | ('absent', None) | ('unknown', reason).

    Absent only when every line of the error is one of the given answers for
    the object asked about. Any other failure — a context or endpoint error
    that also says "not found", no permission on the socket, a daemon that
    does not answer — is unknown, never read as "nothing there".
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "unknown", str(exc)
    if r.returncode == 0:
        return "ok", r.stdout
    detail = (r.stderr or r.stdout).strip()
    lines = [l.strip() for l in detail.splitlines() if l.strip()]
    if absent and lines and all(any(re.fullmatch(p, l, re.IGNORECASE) for p in absent) for l in lines):
        return "absent", None
    return "unknown", (lines or [f"exit {r.returncode}"])[-1]


def network_state(args):
    """('ok', enable_ipv6) | ('absent', None) | ('unknown', reason)."""
    if args.network_ipv6 is not None:
        if args.network_ipv6 in ("true", "false"):
            return "ok", args.network_ipv6 == "true"
        return ("absent", None) if args.network_ipv6 == "absent" else ("unknown", "test: network inspect failed")
    state, out = docker_query(["docker", "network", "inspect", "-f", "{{.EnableIPv6}}", args.public_network],
                              network_absent(args.public_network))
    return (state, out.strip() == "true") if state == "ok" else (state, out)


def container_state(args):
    """('ok', (ports, labels, networks)) | ('absent', None) | ('unknown', reason);
    a stopped container is absent. `networks` maps each endpoint's network name
    to its GwPriority (None where the daemon reports none — Engine before
    28.0), or is None when a fixture gives no networks."""
    if args.running_ports:
        data = json.loads(Path(args.running_ports).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "__error__" in data:
            return "unknown", data["__error__"]
        labels = json.loads(Path(args.running_labels).read_text(encoding="utf-8")) if args.running_labels else None
        networks = json.loads(Path(args.running_networks).read_text(encoding="utf-8")) if args.running_networks else None
        return ("absent", None) if data is None else ("ok", (data, labels, networks))
    state, out = docker_query(["docker", "inspect", args.container], container_absent(args.container))
    if state != "ok":
        return state, out
    obj = json.loads(out)[0]
    if not (obj.get("State") or {}).get("Running"):
        return "absent", None
    settings = obj.get("NetworkSettings") or {}
    networks = {name: ep.get("GwPriority") for name, ep in (settings.get("Networks") or {}).items()}
    return "ok", (settings.get("Ports") or {}, (obj.get("Config") or {}).get("Labels") or {}, networks)


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
    ap.add_argument("--docker-endpoint", help="the endpoint Compose uses, such as unix:///var/run/docker.sock (tests)")
    ap.add_argument("--docker-info", help="the endpoint's docker info as JSON, or {\"__error__\": reason} (tests)")
    ap.add_argument("--network-ipv6", choices=["true", "false", "absent", "error"], help="network state (tests)")
    ap.add_argument("--running-ports", help="NetworkSettings.Ports as JSON, 'null' when not running, "
                                            "or {\"__error__\": reason} (tests)")
    ap.add_argument("--running-labels", help="Config.Labels of the running container as JSON (tests)")
    ap.add_argument("--running-networks", help="network name -> GwPriority of the running container as JSON (tests)")
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
            "       Leave TRAEFIK_BIND_V6 empty, or apply network-dual-stack.yml with its prerequisites.")

    priorities = gateway_priorities(model)
    if priorities is not None:
        problem = gateway_endpoint_problem(priorities)
        if problem:
            errors.append(
                f"the published ports are not pinned to the public network: {problem}.\n"
                "       Docker maps them to Traefik's address on the network with the highest gw_priority,\n"
                "       and without one to the first in Compose order (crowdsec-security). Give 'public' a\n"
                "       gw_priority above every other network of the service (docker-compose.yml).")

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
            ports, labels, networks = ports
            if networks is not None and priorities is not None and not gateway_endpoint_problem(priorities):
                if any(p is None for p in networks.values()):
                    unverified.append(f"{args.container} reports no gateway priority for its networks — "
                                      "Docker Engine 28.0 or later is needed to pin the published ports to "
                                      f"{args.public_network}.")
                else:
                    problem = gateway_endpoint_problem({n: int(p) for n, p in networks.items()},
                                                       public_key=args.public_network)
                    if problem:
                        pending.append(f"{args.container} runs with its published ports on another network than "
                                       f"{args.public_network}: {problem}.\n         Recreate it: docker compose up -d")
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
