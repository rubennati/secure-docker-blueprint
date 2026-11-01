# Edge networks — one per stack, or the shared network

Which Docker network Traefik reaches a stack on, why a new installation gets one
network per stack, how an installation that shares `proxy-public` moves, and
what the shared network remains for. The decision is
[DEC-075](../../../.ai/decisions.md#dec-075); the measurement behind it is the
ingress audit of 2026-10-31
([`docs/audits/ingress-architecture-2026-10-31.md`](../../../docs/audits/ingress-architecture-2026-10-31.md)).

## What the two shapes are

Docker isolates networks from each other, not containers within one. On the
shared `proxy-public`, every web container reaches every other web container's
ports directly — past Traefik and its router positions (measured: T1, T2 in the
audit). On an edge network of its own, a stack's web container reaches Traefik
and its own `app-internal`, and nothing else.

| | Edge network per stack (default) | Shared `proxy-public` (choice) |
|---|---|---|
| The stack's `.env` | `TRAEFIK_NETWORK=${COMPOSE_PROJECT_NAME}-edge` | `TRAEFIK_NETWORK=proxy-public` |
| `core/traefik/.env` | the network listed in `EDGE_NETWORKS` | nothing |
| Who creates the network | Traefik, from the rendered `config/edge-networks.yml` | Traefik, from `docker-compose.yml` |
| A compromised web container reaches | Traefik, its own `app-internal` | every other member of the network |
| Stacks reach each other by service name | no | yes |

Both are the same mechanism — the stack's compose file names its proxy network
through `TRAEFIK_NETWORK` (`name: ${TRAEFIK_NETWORK}`, `external: true`) and the
label `traefik.docker.network=${TRAEFIK_NETWORK}` tells Traefik which network to
dial the backend on. One variable per stack decides.

The published ports stay on `proxy-public` in both shapes (`gw_priority`,
DEC-075.2). Edge networks are IPv4-only, like `app-internal`: Traefik dials a
backend over IPv4, and no client address is carried on the network behind the
proxy.

## A new installation

1. In every stack's `.env`, keep the example's `TRAEFIK_NETWORK=${COMPOSE_PROJECT_NAME}-edge`.
2. In `core/traefik/.env`, list the networks of the stacks you install:

   ```env
   EDGE_NETWORKS="nextcloud-edge vaultwarden-edge"
   COMPOSE_FILE=docker-compose.yml:network-dual-stack.yml:config/published-ports.yml:config/edge-networks.yml
   ```

3. `bash ops/scripts/render.sh` writes `config/edge-networks.yml`; `docker compose up -d`
   creates the networks and joins Traefik to them; then start the stacks.

Adding a stack later is the same three lines: list its network, render,
`docker compose up -d` in `core/traefik` — which recreates the Traefik container —
then `up -d` the stack. **A Traefik recreate interrupts every stack it routes, for
about seven seconds**: from the stop signal Traefik accepts no new connection, the
old container takes three to five seconds to exit and the new one about two to
start (measured on a host, 2026-11-01). The new stack is routed once its
healthcheck passes; Traefik skips a container that is still starting.

**A stack whose network is not listed is unreachable, and Traefik's log says
nothing.** `validate.sh` compares the `traefik.docker.network` label of every
running routed container with `EDGE_NETWORKS` and with the networks Traefik has
joined: a labelled network that `EDGE_NETWORKS` does not list is an error, also
while Traefik still joins it (the next `up -d` would remove it); a listed one
Traefik has not joined yet is pending until the next `up -d` (and an error under
`--strict`).

## Moving a shared installation to edge networks

Stack by stack. Step 1 recreates Traefik and interrupts every stack for about
seven seconds; step 3 interrupts the moved stack until its healthcheck passes:

1. `core/traefik/.env`: add the stack's network to `EDGE_NETWORKS`, then
   `bash ops/scripts/render.sh` and `docker compose up -d` in `core/traefik`.
   Traefik is recreated with the new network.
2. The stack's `.env`: `TRAEFIK_NETWORK=<project>-edge`.
3. `docker compose up -d` in the stack: the web container is recreated on the
   edge network. It leaves `proxy-public`; nothing else changes.
4. `bash ops/scripts/validate.sh --strict` in `core/traefik`.

`proxy-public` keeps existing — it carries the published ports — and keeps
every stack that still names it.

**Moving back runs in the other order**, so the stack is never on a network
Traefik has left: its `.env` to `TRAEFIK_NETWORK=proxy-public` and
`docker compose up -d` in the stack, then its network out of `EDGE_NETWORKS`,
`render.sh` and `docker compose up -d` in `core/traefik`, then
`validate.sh --strict`. With the list shortened first, the stack is unreachable
from Traefik's recreate until its own has passed its healthcheck — measured at
about fourteen seconds for a stack with one — and `validate.sh` refuses the state
in between. Traefik's project no longer names the removed network but does not
remove it either; `docker network rm <project>-edge` once no container uses it
returns its address pool.

An installation from before `EDGE_NETWORKS` existed runs
`scripts/migrate-traefik-env.sh --all` once: it adds `EDGE_NETWORKS=""` and
`COMPOSE_FILE` to `core/traefik/.env`, which changes nothing until a network is
listed.

## Stacks that reach each other

A stack that another stack calls by service name — a mail sink every stack sends
to, a model runtime a chat front end talks to, a document store an automation
reads — needs a network both are on. The shared network is that network: both
stacks set `TRAEFIK_NETWORK=proxy-public`, and the stack's README names the
consequence. `apps/mailpit` and `apps/greenmail` ship that way, because being
reached by every other stack is what they are for — and a stack that points its
SMTP settings at `mailpit:1025` or `greenmail:3025` sets `proxy-public` too:
on its own edge network the name does not resolve and the port is not reachable. An office server calling a
file host back does not need it: it calls the file host's public name through
Traefik (`apps/seafile/README.md`, "Access policy"; `apps/nextcloud/README.md`,
"Office servers behind a closed route").

## The address pool

A default daemon hands out 32 user networks (measured). Two per stack — edge and
`app-internal` — plus the three of `core/traefik` is fourteen stacks before the
pool is spent and `docker network create` fails with "all predefined address
pools have been fully subnetted". A host with more stacks sets a larger pool once
in `/etc/docker/daemon.json`:

```json
{
  "default-address-pools": [
    { "base": "172.16.0.0/12", "size": 24 }
  ]
}
```

The daemon restart that applies it is a restart of every container unless
`live-restore` is on
([`docs/standards/deployment-lifecycle.md`](../../../docs/standards/deployment-lifecycle.md)).
