# obot

An MCP gateway and agent platform: it catalogues MCP servers, runs the ones it
hosts as containers, and puts an LLM gateway and a chat interface in front of
them. Upstream: [obot-platform/obot](https://github.com/obot-platform/obot).

It sits beside [`apps/agentgateway`](../agentgateway/), which routes to MCP
servers you run yourself. obot **starts them for you**, and that is the whole
difference — in what it can do, and in what it costs you to run it.

## The deviation this stack carries

**obot can create containers on this host. That is root on this host.**

A process that can call `ContainerCreate` can ask for a container that mounts
`/` and runs as root, and the daemon will build it. No setting in this compose
file changes that, and the socket proxy in front does not change it either.

The proxy is still here and still worth having: it denies `exec`, `swarm`,
`configs` and `secrets`, so the API surface obot reaches is the one it actually
uses — create, start, stop, remove, inspect, list and logs on containers, pull
and inspect on images, create and list on volumes. That is a narrower blast
radius, not a boundary.

What follows from it:

- **`acc-tailscale` is the floor, not a default to relax.** Anyone who reaches
  this interface and gets past the login is one bug away from the host.
- **Do not put this on a host that runs anything you would not hand over.**
  On this blueprint's shape — one Docker host, every stack beside every other —
  that means obot and your data on the same daemon.
- **Upstream is asked to make it optional.** Issue
  [7978](https://github.com/obot-platform/obot/issues/7978) asks for a start
  without a runtime backend when no MCP servers are hosted, which would let this
  stack drop the socket entirely. Open, no response as of 2026-09-23.

This is recorded as a deliberate exception in `scripts/ci/check-baseline.py`
rather than hidden, and the stack ships `scaffolded` regardless of how well it
runs, because "it works" is not the open question here.

## Architecture

```text
Traefik ──http──→ obot-app :8080
                     │
                     ├──→ obot-db :5432            (PostgreSQL, app-internal)
                     └──→ obot-socket-proxy :2375  (filtered Docker API)
                                  │
                                  └──→ /var/run/docker.sock ──→ MCP server containers
```

The MCP servers obot starts are **not** in this compose file. They are
containers on the host, created at runtime, with names like
`<id>obot-mcp-server`. Nothing here limits how many.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # secrets and volume directories
sudo chown -R 1000:1000 volumes/data
docker compose up -d
cat .secrets/obot_bootstrap_token.txt    # the first sign-in
```

Sign in with that token, then configure an authentication provider and give a
real account the owner role. The bootstrap user is a way in, not an account to
keep using.

**Read the token from the file, not from the log.** Leave
`OBOT_BOOTSTRAP_TOKEN` unset and obot generates one and prints it into the
container log, where it stays for anyone who can read logs.

### Ownership of the data volume

The image declares `USER 0` and this stack runs it as uid 1000 instead, because
with an external database it needs nothing root can do. That makes the `chown`
above load-bearing: without it the container cannot write `/data/cache` and
restart-loops.

Running it as root does not fix that — `cap_drop: ALL` takes away
`DAC_OVERRIDE`, which is the capability that lets root ignore file permissions
in the first place.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
sudo chown -R 1000:1000 volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — sign in with .secrets/obot_bootstrap_token.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The local variant carries the same socket proxy and the same consequence. It is
local in the sense of "not routed", not in the sense of "harmless".

## Security model

- **Authentication is off in upstream's default** and switched on here with
  `OBOT_SERVER_ENABLE_AUTHENTICATION=true`. Verified: every API path answers
  `401` without credentials.
- **The bundled PostgreSQL is not used.** The image starts its own with the
  user and password `obot`/`obot` baked in, on the same container, whenever
  `OBOT_SERVER_DSN` is unset. Setting it moves the data to a real database on an
  internal network with a generated password.
- **Non-root**, `cap_drop: ALL`, `no-new-privileges`, database with no published
  port. Note what this does and does not buy: it stops a bug in obot from being
  a root bug in obot's own container. It does not stop obot from asking the
  daemon for a privileged container.
- **The socket proxy's allow-list** is what `pkg/mcp/docker.go` actually calls,
  and no verb beyond them. `EXEC` is off.
- **Hosted MCP servers cannot reach this host's own services** by upstream's
  default: `--disallow-localhost-mcp`, `--disallow-private-ipmcp` and
  `--disallow-link-local-mcp` are all on. Worth keeping.

## What leaves the host

The update check is off. Four catalogue feeds remain, all on GitHub, all read at
start: the MCP catalogue, the system MCP catalogue, the skills repository and
the hosted-agents catalogue. They are content rather than telemetry — nothing
about this installation is sent — and each can be pointed at your own
repository. See `UPSTREAM.md` for the settings.

Anything you then ask an agent to do reaches whatever model provider and MCP
servers you configured — that is the work, not a side effect.

## Known limits

- **No `read_only`.** The entrypoint writes to `/data`, to `/tmp` and to the
  provider directory the image ships. Not attempted further.
- **No MCP server has been hosted end to end here.** The Docker path is proven —
  obot listed, stopped and deleted containers through the proxy — but starting a
  real MCP server, and what that container is then allowed to do, is a host
  question.
- **Nothing limits the containers obot creates.** No quota, no cap on how many,
  no limits inherited from this file.
- **`sec-2` is not measured against the interface.**
- **The release cadence is fast** — 0.7 to 0.26 in the life of this repository.
  Read the release notes before every upgrade.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`, and will stay that way longer than most.

## Backup

| | |
|---|---|
| **Everything** | `./volumes/postgres` — users, MCP server definitions, stored credentials, audit logs. Dump it: `docker compose exec obot-db sh -c 'pg_dump -U obot obot' > obot.sql` |
| **State** | `./volumes/data` — cache, provider files and audit logs written outside the database |
| **The keys** | `.secrets/obot_server_dsn.txt` and `.secrets/db_pwd.txt` hold the same password twice; restore both together. `.secrets/obot_bootstrap_token.txt` is a way in, not a key — regenerating it costs nothing |
| **Not yours to back up** | the MCP server containers obot creates. They are rebuilt from their definitions |
| **Quiescing** | `pg_dump` is consistent on its own |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/obot/volumes/data
```

Restore: put the volumes back with `volumes/data` owned by `1000:1000`, restore
the secrets, start the database, load the dump, then start obot. Stored
credentials come back encrypted with whatever encryption provider was
configured — `None` by default, which means they are readable in the database.
