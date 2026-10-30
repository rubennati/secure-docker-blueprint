#!/usr/bin/env python3
"""core/traefik/ops/scripts/check-published-family.py — IPv6 is published only
where the client address survives the way to the container.

- the shipped compose files: the base binds the three ports to IPv4 only, the
  dual-stack overlay adds the same three on [::] and the IPv6 subnet (needs
  Docker; skipped without it)
- IPv4-only: a binding without a host address, or on an IPv6 address, is an
  error — from the base file or from any override
- dual-stack: the daemon's effective settings decide, for the daemon behind
  the endpoint Compose uses — DOCKER_HOST or the context's endpoint must be a
  Unix socket on which exactly one local dockerd listens, with the host name
  and data root `docker info` reports; a host name and data root that merely
  match, a forwarded socket, or an ssh/tcp context are NOT VERIFIED. Read are
  its arguments and the config file they name or the default one:
  userland-proxy false and ip6tables enabled pass; userland-proxy on (also by
  default, with no daemon.json) or ip6tables off is an error
- settings that cannot be read — no dockerd visible, a remote DOCKER_HOST, a
  rootless daemon without --config-file, a config changed after the daemon
  started — are an error of their own, which DOCKER_DAEMON_CHECK=manual turns
  into a warning
- an existing IPv4-only network under the overlay is an error; a running
  container published differently from the model is PENDING, exit 3, so the
  update that recreates it is not blocked and nothing reads as a security OK
- a docker-proxy listening on IPv6 for one of Traefik's ports is PENDING
- only Docker's own "not found" means the network or the container is absent;
  a refused or unanswered inspect is NOT VERIFIED, never "nothing there" —
  and so is any "not found" that does not name the object asked about, such
  as a Docker context that does not resolve
- the checks evaluate the files the deployment uses: validate.sh passes its
  -f files on, and a running container created from other files than the
  evaluated ones — or with no record of them — is NOT VERIFIED
- without docker-compose.yml in the directory nothing is checked, which is
  NOT VERIFIED, exit 3
- validate.sh: exit 3 from the checker never ends in a plain "OK."; it exits 0
  so the repair can proceed, and --strict turns it into a failure

Run:
    python3 scripts/ci/test_traefik_published_family.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import json
import socket
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from test_traefik_dashboard_cert import BASE_ENV, TRAEFIK

CHECKER = TRAEFIK / "ops" / "scripts" / "check-published-family.py"


def port(host_ip, published, target, protocol="tcp"):
    p = {"mode": "ingress", "target": int(target), "published": str(published), "protocol": protocol}
    if host_ip is not None:
        p["host_ip"] = host_ip
    return p


IPV4 = [port("0.0.0.0", 80, 80), port("0.0.0.0", 443, 443), port("0.0.0.0", 443, 443, "udp")]
IPV6 = [port("::", 80, 80), port("::", 443, 443), port("::", 443, 443, "udp")]


def model(ports, dual_stack=False):
    net = {"name": "proxy-public"}
    if dual_stack:
        net["enable_ipv6"] = True
    return {"services": {"traefik": {"ports": ports}}, "networks": {"public": net}}


class Checker(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.proc = self.tmp / "proc"
        self.proc.mkdir()
        (self.proc / "stat").write_text(f"cpu 0\nbtime {int(time.time())}\n", encoding="utf-8")

    def dockerd(self, *args, uid=0, pid="100", host="fd://"):
        d = self.proc / pid
        d.mkdir()
        (d / "comm").write_text("dockerd\n", encoding="utf-8")
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in ("/usr/bin/dockerd", "-H", host) + args) + b"\0")
        (d / "status").write_text(f"Name:\tdockerd\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n", encoding="utf-8")
        (d / "stat").write_text(f"{pid} (dockerd) S 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 0 0 0\n", encoding="utf-8")

    @staticmethod
    def local_info(root="/var/lib/docker"):
        return {"Name": socket.gethostname(), "DockerRootDir": root, "SecurityOptions": ["name=seccomp,profile=builtin"]}

    def docker_proxy(self, host_ip, host_port, pid="200"):
        d = self.proc / pid
        d.mkdir()
        (d / "comm").write_text("docker-proxy\n", encoding="utf-8")
        argv = ("/usr/bin/docker-proxy", "-proto", "tcp", "-host-ip", host_ip, "-host-port", str(host_port),
                "-container-ip", "172.18.0.3", "-container-port", str(host_port))
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")

    def daemon_json(self, content, age=1000):
        path = self.tmp / "daemon.json"
        path.write_text(json.dumps(content), encoding="utf-8")
        then = time.time() - age
        os.utime(path, (then, then))
        return str(path)

    def run_checker(self, m, *extra, env=None, runtime=None, info=None, endpoint="unix:///var/run/docker.sock"):
        mj = self.tmp / "model.json"
        mj.write_text(json.dumps(m), encoding="utf-8")
        ij = self.tmp / "info.json"
        ij.write_text(json.dumps(info if info is not None else self.local_info()), encoding="utf-8")
        args = ["python3", str(CHECKER), "--compose-json", str(mj), "--proc", str(self.proc), "--docker-info", str(ij),
                "--docker-endpoint", endpoint]
        if runtime is None:
            args.append("--no-runtime")
        else:
            net, ports, *labels = runtime
            pj = self.tmp / "ports.json"
            pj.write_text(json.dumps(ports), encoding="utf-8")
            args += ["--network-ipv6", net, "--running-ports", str(pj)]
            if labels:
                lj = self.tmp / "labels.json"
                lj.write_text(json.dumps(labels[0]), encoding="utf-8")
                args += ["--running-labels", str(lj)]
        full_env = {k: v for k, v in os.environ.items() if k != "DOCKER_HOST"}
        full_env.update(env or {})
        return subprocess.run(args + list(extra), capture_output=True, text=True, env=full_env)

    # --- IPv4-only ---------------------------------------------------------

    def test_ipv4_bindings_pass(self):
        r = self.run_checker(model(IPV4))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip(), "")

    def test_binding_without_host_address_is_refused_on_ipv4_only(self):
        r = self.run_checker(model(IPV4 + [port(None, 8443, 443)]))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("*:8443/tcp", r.stdout)
        self.assertIn("IPv4-only", r.stdout)

    def test_ipv6_binding_is_refused_on_ipv4_only(self):
        r = self.run_checker(model(IPV4 + [port("::", 443, 443, "udp")]))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(":::443/udp", r.stdout)

    def test_daemon_settings_are_irrelevant_on_ipv4_only(self):
        # no dockerd visible at all: nothing under IPv4-only depends on it
        self.assertEqual(self.run_checker(model(IPV4)).returncode, 0)

    # --- dual-stack: effective daemon settings -----------------------------

    def test_userland_proxy_false_in_daemon_json_passes(self):
        self.dockerd("--config-file", self.daemon_json({"userland-proxy": False, "ip6tables": True}))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_userland_proxy_false_as_argument_passes(self):
        self.dockerd("--userland-proxy=false", "--config-file", str(self.tmp / "absent.json"))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_docker_defaults_are_refused(self):
        self.dockerd("--config-file", str(self.tmp / "absent.json"))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("userland-proxy is enabled", r.stdout)
        self.assertIn("Docker defaults", r.stdout)

    def test_userland_proxy_true_is_refused(self):
        self.dockerd("--config-file", self.daemon_json({"userland-proxy": True}))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("userland-proxy is enabled", r.stdout)

    def test_ip6tables_disabled_is_refused(self):
        self.dockerd("--config-file", self.daemon_json({"userland-proxy": False, "ip6tables": False}))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ip6tables is disabled", r.stdout)

    # --- dual-stack: settings that cannot be checked ------------------------

    def assert_uncheckable(self, r, reason):
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("cannot be checked here", r.stdout)
        self.assertIn("not a finding that they are wrong", r.stdout)
        self.assertIn(reason, r.stdout)

    def test_no_dockerd_visible_is_uncheckable(self):
        self.assert_uncheckable(self.run_checker(model(IPV4 + IPV6, dual_stack=True)), "no dockerd process")

    def test_remote_docker_host_is_uncheckable(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), env={"DOCKER_HOST": "tcp://192.0.2.20:2376"})
        self.assert_uncheckable(r, "DOCKER_HOST")

    def test_rootless_daemon_without_config_file_is_uncheckable(self):
        self.dockerd(uid=1000)
        self.assert_uncheckable(self.run_checker(model(IPV4 + IPV6, dual_stack=True)), "rootless")

    def test_config_changed_after_start_is_uncheckable(self):
        (self.proc / "stat").write_text(f"cpu 0\nbtime {int(time.time()) - 100000}\n", encoding="utf-8")
        self.dockerd("--config-file", self.daemon_json({"userland-proxy": False}, age=0))
        self.assert_uncheckable(self.run_checker(model(IPV4 + IPV6, dual_stack=True)), "changed after the daemon started")

    def test_manual_declaration_turns_uncheckable_into_a_warning(self):
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), "--daemon-check", "manual")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WARNING: Docker daemon settings declared by DOCKER_DAEMON_CHECK=manual", r.stdout)

    def test_manual_declaration_does_not_hide_an_unsafe_setting(self):
        self.dockerd("--config-file", self.daemon_json({"userland-proxy": True}))
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), "--daemon-check", "manual")
        self.assertEqual(r.returncode, 1, r.stdout)

    # --- review finding 1: the daemon behind the endpoint Compose uses -------

    def two_daemons(self, first_safe):
        # pid 100: the system daemon, default data root; pid 101: a second
        # daemon with its own data root. Only one of them is safe.
        then = time.time() - 1000
        paths = {}
        for name, userland in (("safe", False), ("unsafe", True)):
            path = self.tmp / f"{name}.json"
            path.write_text(json.dumps({"userland-proxy": userland}), encoding="utf-8")
            os.utime(path, (then, then))
            paths[name] = str(path)
        first, second = ("safe", "unsafe") if first_safe else ("unsafe", "safe")
        self.dockerd("--config-file", paths[first], pid="100")
        self.dockerd("--config-file", paths[second], "--data-root", "/srv/docker-second",
                     pid="101", host="unix:///run/docker-second.sock")

    def test_the_daemon_on_the_endpoints_socket_is_read_not_the_first(self):
        self.two_daemons(first_safe=False)
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), info=self.local_info("/srv/docker-second"),
                             endpoint="unix:///run/docker-second.sock")
        self.assertEqual(r.returncode, 0, r.stdout)
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), info=self.local_info("/var/lib/docker"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("userland-proxy is enabled", r.stdout)

    def test_matching_name_and_data_root_on_a_foreign_socket_is_uncheckable(self):
        # Review 2, finding 2: a context whose socket is forwarded from another
        # daemon reports the same host name and data root as the local one.
        # That daemon is unsafe; the local one is safe; nothing may pass.
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), endpoint="unix:///tmp/forwarded-docker.sock")
        self.assert_uncheckable(r, "no dockerd on this host listens on /tmp/forwarded-docker.sock")

    def test_ssh_context_endpoint_is_uncheckable(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), endpoint="ssh://admin@docker-host")
        self.assert_uncheckable(r, "not the socket of a daemon on this host")

    def test_socket_daemon_with_another_data_root_is_uncheckable(self):
        self.two_daemons(first_safe=True)
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), info=self.local_info("/var/lib/docker"),
                             endpoint="unix:///run/docker-second.sock")
        self.assert_uncheckable(r, "they are not the same daemon")

    def test_endpoint_on_another_host_is_uncheckable(self):
        self.dockerd("--userland-proxy=false")
        info = dict(self.local_info(), Name="docker-desktop")
        self.assert_uncheckable(self.run_checker(model(IPV4 + IPV6, dual_stack=True), info=info), "not this host")

    def test_failed_docker_info_is_uncheckable(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True),
                             info={"__error__": "docker info failed: permission denied"})
        self.assert_uncheckable(r, "docker info failed")

    def test_no_daemon_with_the_endpoints_data_root_is_uncheckable(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), info=self.local_info("/srv/elsewhere"))
        self.assert_uncheckable(r, "keeps its data in /var/lib/docker, but the endpoint reports /srv/elsewhere")

    def test_docker_context_selects_the_endpoint(self):
        # The checker resolves the endpoint as the docker CLI does: DOCKER_CONTEXT,
        # else `docker context show`. The remote context reports this host's name
        # and data root — only its endpoint gives it away.
        self.dockerd("--userland-proxy=false")
        bindir = self.tmp / "bin"
        bindir.mkdir()
        local = json.dumps(self.local_info())
        ctx = lambda host: json.dumps([{"Name": "x", "Endpoints": {"docker": {"Host": host}}}])
        (bindir / "docker").write_text(
            "#!/bin/sh\n"
            'if [ "$1" = info ]; then echo \'' + local + '\'; exit 0; fi\n'
            'if [ "$1 $2" = "context show" ]; then echo default; exit 0; fi\n'
            'if [ "$1 $2 $3" = "context inspect default" ]; then echo \'' + ctx("unix:///var/run/docker.sock") + '\'; exit 0; fi\n'
            'if [ "$1 $2 $3" = "context inspect remote" ]; then echo \'' + ctx("ssh://admin@docker-host") + '\'; exit 0; fi\n'
            "exit 1\n", encoding="utf-8")
        (bindir / "docker").chmod(0o755)
        mj = self.tmp / "model.json"
        mj.write_text(json.dumps(model(IPV4 + IPV6, dual_stack=True)), encoding="utf-8")
        base_env = {k: v for k, v in os.environ.items() if k not in ("DOCKER_HOST", "DOCKER_CONTEXT")}
        base_env["PATH"] = f"{bindir}:{os.environ['PATH']}"
        cmd = ["python3", str(CHECKER), "--compose-json", str(mj), "--proc", str(self.proc), "--no-runtime"]
        r = subprocess.run(cmd, capture_output=True, text=True, env=base_env)
        self.assertEqual(r.returncode, 0, r.stdout)
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(base_env, DOCKER_CONTEXT="remote"))
        self.assert_uncheckable(r, "ssh://admin@docker-host")

    # --- running state -----------------------------------------------------

    @staticmethod
    def inspect_ports(*bindings):
        out = {}
        for ip, pub, target, proto in bindings:
            out.setdefault(f"{target}/{proto}", []).append({"HostIp": ip, "HostPort": str(pub)})
        return out

    def test_existing_ipv4_network_under_the_overlay_is_refused(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), runtime=("false", None))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("existing network proxy-public is IPv4-only", r.stdout)

    def test_old_container_is_pending_and_does_not_block_the_update(self):
        old = self.inspect_ports(("0.0.0.0", 80, 80, "tcp"), ("::", 80, 80, "tcp"),
                                 ("0.0.0.0", 443, 443, "tcp"), ("::", 443, 443, "tcp"),
                                 ("0.0.0.0", 443, 443, "udp"), ("::", 443, 443, "udp"))
        r = self.run_checker(model(IPV4), runtime=("false", old))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("PENDING: traefik-core runs with a different publication", r.stdout)
        self.assertIn("docker compose up -d", r.stdout)

    def test_recreated_container_matching_the_model_is_silent(self):
        new = self.inspect_ports(("0.0.0.0", 80, 80, "tcp"), ("0.0.0.0", 443, 443, "tcp"), ("0.0.0.0", 443, 443, "udp"))
        r = self.run_checker(model(IPV4), runtime=("false", new))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip(), "")

    def test_docker_proxy_on_ipv6_is_pending(self):
        self.docker_proxy("::", 443)
        new = self.inspect_ports(("0.0.0.0", 80, 80, "tcp"), ("0.0.0.0", 443, 443, "tcp"), ("0.0.0.0", 443, 443, "udp"))
        r = self.run_checker(model(IPV4), runtime=("false", new))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("PENDING: docker-proxy relays IPv6", r.stdout)

    # --- review finding 2: access errors are not "absent" -------------------

    def fake_docker(self, network_err=None, container_err=None):
        """A docker CLI on PATH that answers inspect with the given stderr."""
        bindir = self.tmp / "bin"
        bindir.mkdir(exist_ok=True)
        script = bindir / "docker"
        script.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = network ]; then echo "$NET_ERR" >&2; exit 1; fi\n'
            'if [ "$1" = inspect ]; then echo "$CTR_ERR" >&2; exit 1; fi\n'
            "exit 0\n", encoding="utf-8")
        script.chmod(0o755)
        return {"PATH": f"{bindir}:{os.environ['PATH']}", "NET_ERR": network_err or "", "CTR_ERR": container_err or ""}

    def run_with_fake_docker(self, m, env, *extra):
        mj = self.tmp / "model.json"
        mj.write_text(json.dumps(m), encoding="utf-8")
        full_env = {k: v for k, v in os.environ.items() if k != "DOCKER_HOST"}
        full_env.update(env)
        return subprocess.run(["python3", str(CHECKER), "--compose-json", str(mj), "--proc", str(self.proc), *extra],
                              capture_output=True, text=True, env=full_env)

    def test_refused_container_inspect_is_not_verified(self):
        env = self.fake_docker(network_err="Error response from daemon: network proxy-public not found",
                               container_err="permission denied while trying to connect to the docker API "
                                             "at unix:///var/run/docker.sock")
        r = self.run_with_fake_docker(model(IPV4), env)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("NOT VERIFIED: the container traefik-core could not be inspected: permission denied", r.stdout)

    def test_missing_container_and_network_are_absent_not_unverified(self):
        env = self.fake_docker(network_err="Error response from daemon: network proxy-public not found",
                               container_err="Error: No such object: traefik-core")
        r = self.run_with_fake_docker(model(IPV4), env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip(), "")

    def test_refused_network_inspect_under_dual_stack_is_not_verified(self):
        env = self.fake_docker(network_err="Cannot connect to the Docker daemon at unix:///var/run/docker.sock. "
                                           "Is the docker daemon running?",
                               container_err="Error: No such object: traefik-core")
        r = self.run_with_fake_docker(model(IPV4 + IPV6, dual_stack=True), env, "--daemon-check", "manual")
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("NOT VERIFIED: the network proxy-public could not be inspected: Cannot connect", r.stdout)
        self.assertNotIn("is IPv4-only", r.stdout)

    def test_context_error_saying_not_found_is_not_verified(self):
        # Review 2, finding 1: a context that does not resolve also says "not
        # found", and must not read as "no container".
        ctx = 'Failed to initialize: unable to resolve docker endpoint: context "remote": context not found'
        env = self.fake_docker(network_err=ctx, container_err=ctx)
        r = self.run_with_fake_docker(model(IPV4), env)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("NOT VERIFIED: the container traefik-core could not be inspected: Failed to initialize", r.stdout)

    def test_not_found_naming_another_object_is_not_verified(self):
        env = self.fake_docker(network_err="Error response from daemon: network proxy-public-old not found",
                               container_err="Error: No such object: traefik-core-old")
        r = self.run_with_fake_docker(model(IPV4 + IPV6, dual_stack=True), env, "--daemon-check", "manual")
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("network proxy-public could not be inspected", r.stdout)
        self.assertIn("container traefik-core could not be inspected", r.stdout)

    def test_seam_error_states_are_not_verified(self):
        self.dockerd("--userland-proxy=false")
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True),
                             runtime=("error", {"__error__": "permission denied"}))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("network proxy-public could not be inspected", r.stdout)
        self.assertIn("container traefik-core could not be inspected: permission denied", r.stdout)

    # --- review finding 3: the same compose files as the deployment ---------

    NEW = staticmethod(lambda: Checker.inspect_ports(("0.0.0.0", 80, 80, "tcp"), ("0.0.0.0", 443, 443, "tcp"),
                                                     ("0.0.0.0", 443, 443, "udp")))

    def deployed(self, *names):
        return {"com.docker.compose.project.config_files": ",".join(str(self.tmp / n) for n in names)}

    def test_container_from_the_evaluated_files_is_silent(self):
        r = self.run_checker(model(IPV4), "--project-dir", str(self.tmp),
                             runtime=("false", self.NEW(), self.deployed("docker-compose.yml")))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip(), "")

    def test_container_deployed_with_an_extra_f_file_is_not_verified(self):
        r = self.run_checker(model(IPV4), "--project-dir", str(self.tmp),
                             runtime=("false", self.NEW(), self.deployed("docker-compose.yml", "network-dual-stack.yml")))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("NOT VERIFIED: traefik-core was created from", r.stdout)
        self.assertIn("-f", r.stdout)

    def test_compose_file_from_env_is_what_is_compared(self):
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), "--project-dir", str(self.tmp),
                             "--daemon-check", "manual",
                             env={"COMPOSE_FILE": "docker-compose.yml:network-dual-stack.yml"},
                             runtime=("true", None))
        self.assertNotIn("was created from", r.stdout)
        labels = self.deployed("docker-compose.yml", "network-dual-stack.yml")
        dual = self.inspect_ports(*[(ip, p, p, proto) for ip in ("0.0.0.0", "::")
                                    for p, proto in ((80, "tcp"), (443, "tcp"), (443, "udp"))])
        r = self.run_checker(model(IPV4 + IPV6, dual_stack=True), "--project-dir", str(self.tmp),
                             "--daemon-check", "manual",
                             env={"COMPOSE_FILE": "docker-compose.yml:network-dual-stack.yml"},
                             runtime=("true", dual, labels))
        self.assertNotIn("was created from", r.stdout)
        self.assertNotIn("PENDING", r.stdout)

    def test_explicit_files_are_what_is_compared(self):
        base, overlay = str(self.tmp / "docker-compose.yml"), str(self.tmp / "network-dual-stack.yml")
        r = self.run_checker(model(IPV4), "--project-dir", str(self.tmp), "--compose-file", base,
                             runtime=("false", self.NEW(), self.deployed("docker-compose.yml", "network-dual-stack.yml")))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("was created from", r.stdout)
        r = self.run_checker(model(IPV4), "--project-dir", str(self.tmp), "--compose-file", base, "--compose-file", overlay,
                             runtime=("false", self.NEW(), self.deployed("docker-compose.yml", "network-dual-stack.yml")))
        self.assertNotIn("was created from", r.stdout)

    def test_container_without_a_record_of_its_files_is_not_verified(self):
        r = self.run_checker(model(IPV4), "--project-dir", str(self.tmp), runtime=("false", self.NEW(), {}))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("carries no record of the compose files", r.stdout)

    def test_without_compose_file_nothing_is_checked(self):
        r = subprocess.run(["python3", str(CHECKER), "--project-dir", str(self.tmp)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("NOT VERIFIED: no docker-compose.yml", r.stdout)


class ValidateOutcome(unittest.TestCase):
    """validate.sh never reads as a security OK while a check is open (review finding 4)."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "core" / "traefik"
        shutil.copytree(TRAEFIK / "ops", self.root / "ops")
        (tmp / "scripts" / "ci").mkdir(parents=True)
        shutil.copy(TRAEFIK.parents[1] / "scripts" / "ci" / "check-crowdsec-config.py",
                    tmp / "scripts" / "ci" / "check-crowdsec-config.py")
        env = dict(BASE_ENV, ACME_WILDCARD_DOMAIN="example.com")
        (self.root / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        r = subprocess.run(["bash", str(self.root / "ops/scripts/render.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def validate(self, *args):
        return subprocess.run(["bash", str(self.root / "ops/scripts/validate.sh"), *args], capture_output=True, text=True)

    def test_open_items_exit_0_without_a_plain_ok(self):
        # The copy has no docker-compose.yml, so the checks are NOT VERIFIED.
        r = self.validate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOT VERIFIED", r.stdout)
        self.assertIn("SECURITY NOT CONFIRMED", r.stdout)
        self.assertNotEqual(r.stdout.strip().splitlines()[-1], "OK.")
        self.assertNotIn("\nOK.\n", "\n" + r.stdout)

    def test_strict_fails_while_items_are_open(self):
        r = self.validate("--strict")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SECURITY NOT CONFIRMED", r.stdout)

    def test_f_file_must_exist(self):
        r = self.validate("-f", str(self.root / "missing.yml"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("compose file not found", r.stdout)
        r = self.validate("-f")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("needs a compose file", r.stdout)

    def test_f_files_reach_the_checker(self):
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            shutil.copy(TRAEFIK / name, self.root / name)
        r = self.validate("-f", str(self.root / "docker-compose.yml"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("unknown argument", r.stdout)
        if shutil.which("docker") is None:
            # without Docker the checker names the files it would have evaluated
            self.assertIn(str(self.root / "docker-compose.yml"), r.stdout)

    def test_unknown_argument_is_refused(self):
        r = self.validate("--fast")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unknown argument", r.stdout)


@unittest.skipUnless(shutil.which("docker"), "needs the docker CLI for docker compose config")
class ShippedComposeFiles(unittest.TestCase):
    def config(self, *overlay_env):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            shutil.copy(TRAEFIK / name, tmp / name)
        env = dict(BASE_ENV)
        env.update(dict(overlay_env))
        (tmp / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        r = subprocess.run(["docker", "compose", "config", "--format", "json"], cwd=tmp, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    @staticmethod
    def bindings(m):
        return sorted((p.get("host_ip", ""), str(p["published"]), p.get("protocol", "tcp"))
                      for p in m["services"]["traefik"]["ports"])

    def test_base_publishes_ipv4_only(self):
        m = self.config()
        self.assertEqual(self.bindings(m), [("0.0.0.0", "443", "tcp"), ("0.0.0.0", "443", "udp"), ("0.0.0.0", "80", "tcp")])
        self.assertFalse(m["networks"]["public"].get("enable_ipv6"))

    def test_checker_evaluates_explicit_f_files(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in ("docker-compose.yml", "network-dual-stack.yml"):
            shutil.copy(TRAEFIK / name, tmp / name)
        env = dict(BASE_ENV, PUBLIC_NETWORK_SUBNET_V4="172.30.0.0/16", PUBLIC_NETWORK_SUBNET_V6="fd00:db8:30::/64")
        (tmp / ".env").write_text("".join(f'{k}="{v}"\n' for k, v in env.items()), encoding="utf-8")
        run = lambda *files: subprocess.run(
            ["python3", str(CHECKER), "--project-dir", str(tmp), "--no-runtime", "--daemon-check", "manual",
             *[x for f in files for x in ("--compose-file", str(tmp / f))]], capture_output=True, text=True)
        base = run("docker-compose.yml")
        self.assertEqual(base.returncode, 0, base.stdout + base.stderr)
        both = run("docker-compose.yml", "network-dual-stack.yml")
        self.assertNotIn("IPv4-only", both.stdout)  # the overlay was evaluated: dual-stack, no P2 error

    def test_overlay_adds_ipv6_bindings_and_the_ipv6_subnet(self):
        m = self.config(("COMPOSE_FILE", "docker-compose.yml:network-dual-stack.yml"),
                        ("PUBLIC_NETWORK_SUBNET_V4", "172.30.0.0/16"),
                        ("PUBLIC_NETWORK_SUBNET_V6", "fd00:db8:30::/64"))
        self.assertEqual(self.bindings(m), [("0.0.0.0", "443", "tcp"), ("0.0.0.0", "443", "udp"), ("0.0.0.0", "80", "tcp"),
                                            ("::", "443", "tcp"), ("::", "443", "udp"), ("::", "80", "tcp")])
        self.assertTrue(m["networks"]["public"]["enable_ipv6"])


if __name__ == "__main__":
    unittest.main()
