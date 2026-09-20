# Beszel

Lightweight server monitoring with a hub + agent architecture. Go-based, ~20 MB RAM per agent.

## Architecture

The **agent connects out to the hub**. Nothing connects in: the agent opens no
port, and no host port is published for it.

| Service | Image | Role |
|---------|-------|------|
| `beszel-hub` | `henrygd/beszel:0.19.0` | Web UI + SQLite metric store |
| `agent` | `henrygd/beszel-agent:0.19.0` | Collects host and container metrics |
| `socket-proxy` | `tecnativa/docker-socket-proxy:v0.5.0` | The only container that holds the Docker socket |

```text
operator browser ──HTTPS──▶ Traefik ──▶ beszel-hub          (app-internal + proxy-public)
                                           ▲
                                           │ agent dials out, private network
                                        agent ──▶ socket-proxy ──▶ /var/run/docker.sock
                                                  (app-internal, internal: true)
```

The agent registers itself with a token and the hub's public key, over the stack's
private `app-internal` network — no host port, and no round trip through Traefik
for traffic that never leaves the host.

This compose runs the hub + one local agent on the **same host**. For additional
hosts deploy [`monitoring/beszel-agent/`](../beszel-agent/) there.

## What this provides

Running the agent as an ordinary container — no host networking — it reports:

| | |
|---|---|
| **Host** | CPU (total and per core), memory and swap, root-filesystem usage, disk I/O, load average |
| **Containers** | discovery, per-container CPU, per-container memory, per-container network |

**What it does not provide: host NIC / interface bandwidth statistics.** A container
cannot see the host's network namespace. Rather than report this container's own
interface counters as if they were the host's, the stack ships `NICS=-*`, which
selects no interface and omits the field. The number you would otherwise see is real
traffic — just not the host's.

**Consequently Beszel's system *Bandwidth* alert cannot be used in this mode.** It has
nothing to evaluate and will never fire. Every other alert — CPU, memory, disk,
temperature, system down — works normally. Per-container network statistics come from
the Docker API and are unaffected.

If host interface bandwidth matters more to you than container isolation, that is a
deliberate trade you make yourself; this stack does not make it for you.

## Try it locally

Runs on `http://localhost:8090` without Traefik, DNS or a certificate. Same security
model as the production stack — the agent holds no Docker socket and opens no port, and
the socket proxy sits on its own `internal: true` network with no route out — with the
UI bound to loopback instead of a domain.

```bash
cp .env.local.example .env.local
mkdir -p volumes/local/hub-data
docker compose -f docker-compose.local.yml --env-file .env.local up -d hub
# http://localhost:8090 — create the owner account, then put two values in .env.local:
#   AGENT_TOKEN  from Settings -> Tokens & Fingerprints
#   AGENT_KEY    from "+ Add System"
docker compose -f docker-compose.local.yml --env-file .env.local up -d
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p volumes/hub-data
```

### Phase 1 — Hub only

```bash
docker compose up -d beszel-hub
docker compose logs beszel-hub --follow
# Wait for: "Server started at http://0.0.0.0:8090"
```

Open `https://<APP_TRAEFIK_HOST>` and create the owner account.

### Phase 2 — Collect the token and the key

Two values from the hub UI, both into `.env`:

| Value | Where | Into |
|---|---|---|
| **Registration token** | **Settings → Tokens & Fingerprints** — enable it and copy the value | `AGENT_TOKEN` |
| **Hub public key** | **+ Add System** (top right) — copy the key shown | `AGENT_KEY` |

Copy the **full public key**, including the `ssh-ed25519` type prefix; the base64
portion alone is not valid. It can also be derived on the host, which spares the
copy: `ssh-keygen -y -f volumes/hub-data/id_ed25519` (root-owned, so with `sudo`).

Give the system a stable name while you are here — without `AGENT_SYSTEM_NAME` the
agent registers under its container ID, which changes on every recreate:

```bash
# .env
AGENT_TOKEN=...
AGENT_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
AGENT_SYSTEM_NAME=myserver
```

### Phase 3 — Start the agent

```bash
docker compose up -d agent
```

The agent dials the hub itself and registers — there is no host or port to fill in,
because nothing connects to the agent. It appears in the UI with a green dot within
about ten seconds.

After this first setup, `docker compose up -d` starts everything together normally.

## Upgrading from the SSH-registered agent

Earlier versions ran the agent with host networking and an inbound listener on
`45876`, and the hub connected in. That model is gone — the agent now connects out.

An existing `.env` still resolves, but **the agent will not report until you
reconfigure it**:

1. Add `AGENT_TOKEN` from the hub UI (**Settings → Tokens & Fingerprints**).
2. Keep `AGENT_KEY`, and set `AGENT_SYSTEM_NAME` — without it the agent registers
   under its container ID, which changes on every recreate.
3. `docker compose up -d`.

The agent registers as a **new** system. The old SSH-registered entry stops reporting
and can be deleted once the new one shows up. Details in
[`CHANGELOG.md`](../../CHANGELOG.md).

## Security Model

| Aspect | Detail |
|---|---|
| **Hub ↔ Agent auth** | Registration token plus the hub's Ed25519 public key. The agent opens the connection; the hub never dials in. |
| **No inbound port** | The agent opens no listener and publishes nothing. There is no host port to restrict, so no firewall rule or VPN ACL is needed to make this stack safe. |
| **Hub web UI** | `acc-tailscale` + `sec-3` via Traefik — VPN-only access. |
| **Docker socket** | The agent never touches `/var/run/docker.sock`. `socket-proxy` holds it read-only and is the only container that does; the agent reaches it by service name on `app-internal`, which is `internal: true` and has no route out. Permissions are `CONTAINERS=1` and `PING=1` — nothing else, `POST=0`. Verified against a live daemon: that set is exactly sufficient for discovery, per-container CPU, memory and network. The proxy answers `403` to `/version` and `/info`, which the agent treats as non-fatal. A compromise of the agent gets that same narrow read-only API, not root on the host. |
| **Hub data** | SQLite + SSH private key in `volumes/hub-data/`. Back this up — losing it means re-keying all agents. |

## Alerting

Configured in the hub UI, per system — there is no config file for it. Beszel alerts
on thresholds rather than on failure: CPU, memory, disk usage, temperature, and
whether a system is reporting at all.

Two settings worth deciding deliberately:

- **Disk usage** — the one threshold that reliably prevents an incident rather than
  reporting one. Set it low enough to leave time to act.
- **System down** — Beszel notices when an agent stops reporting, but only while the
  hub itself is running. A hub that dies reports nothing, including its own death.
  That gap is covered by the dead-man's-switch pattern in
  [`../README.md`](../README.md#alerting).

A threshold that has never fired is untested. Cross one deliberately once and confirm
the notification arrives.

## Adding more hosts

Deploy [`monitoring/beszel-agent/`](../beszel-agent/) on each additional host. Each
agent connects out to the hub over HTTPS, so the monitored host needs no inbound port
— only a route to the hub's address. How that address is reachable (VPN, private
network, or otherwise) is your deployment decision.

## Backup

| | |
|---|---|
| **State** | `./volumes/hub-data` — SQLite metric store **and the hub's SSH private key** |
| **Critical** | The SSH key. Losing it means re-keying every registered agent by hand. |
| **Reproducible** | Historical metrics — useful, not irreplaceable |
| **Quiescing** | Stop the hub briefly, or use the SQLite dump hook — the store is live |

```yaml
sqlite_databases:
    - name: beszel
      path: /srv/docker/monitoring/beszel/volumes/hub-data/data.db
```

Confirm the database filename on the running instance before relying on that path.
Back up the whole `hub-data` directory regardless — the SSH key is not in the
database.

**Restore order:** restore the directory, start the hub, confirm the agents
reconnect without re-registration.

## Known Issues

- **Two-phase start on first install** — see [Setup](#setup). Subsequent starts need no manual steps.
- **The hub runs as root** (measured on 0.19.0: no `USER` in the image, none set here) and owns everything under `volumes/hub-data/`, including the SSH key. Read the directory with `sudo`.
- **`APP_TAG=0.19.0` is pinned** — Beszel is pre-1.0. Check [releases](https://github.com/henrygd/beszel/releases) before upgrading; update both hub and agent together.
- **Both images have no healthcheck** — hub is scratch-based (no shell/wget), agent provides no health endpoint. Both use `healthcheck: disable: true`; hub status in the UI is the reliable liveness signal for all agents.
- **`403 Forbidden` for `/version` and `/info`** in agent debug logs — expected. The socket proxy grants neither; the agent logs both at debug level and carries on. Granting `INFO=1` was measured to change nothing.
- **Host NIC bandwidth is unavailable** and the system Bandwidth alert cannot fire — see [What this provides](#what-this-provides).
