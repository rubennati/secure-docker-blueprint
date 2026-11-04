"""The environment for a unit test that runs validate.sh: no Docker daemon in reach.

validate.sh reads the daemon it finds — its networks, Traefik's container, the
published ports — so a unit test that let it would depend on the host it runs on:
on the step 8 lab host a network in 192.168.0.0/20 failed a TRUSTED_RANGES case
that passes everywhere else. DOCKER_HOST points at a socket that does not exist,
so the daemon checks report themselves as not run, while the client-only
`docker compose config` still works. HOST_NFTABLES_DIR does the same for the
installed host ruleset: on the step 8 lab host, with /etc/nftables.d/ingress.nft
installed, the layer report read the host's file instead of the fixture's state. A test about daemon state hands validate.sh
a stub that answers for it (test_traefik_edge_networks, test_traefik_model).
"""

import os

SOCKET = "unix:///nonexistent/no-docker-daemon-in-a-unit-test.sock"
NFTABLES_DIR = "/nonexistent/no-host-ruleset-in-a-unit-test"


def env(**extra):
    """os.environ with no Docker daemon in reach, plus `extra`."""
    out = {k: v for k, v in os.environ.items() if k != "DOCKER_CONTEXT"}
    out["DOCKER_HOST"] = SOCKET
    out["HOST_NFTABLES_DIR"] = NFTABLES_DIR
    out.update(extra)
    return out
