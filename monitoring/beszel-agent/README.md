# Beszel Agent

Standalone Beszel agent for remote hosts. Deploy this on each additional host that a central [Beszel hub](../beszel/) should monitor.

## When you need this

- Beszel hub runs on Host A, you want to monitor Host B, C, D
- Any Linux host — bare metal, VM, or Docker host

When you don't need this: if hub and agent are on the **same host**, the agent is already included in [`monitoring/beszel/`](../beszel/).

## Counterpart

| Hub | Agent on hub host | Agent on remote hosts |
|---|---|---|
| `monitoring/beszel/` | included in beszel/ compose | `monitoring/beszel-agent/` ← this |

Same pattern as `core/portainer/` + `core/portainer-agent/`.

## Connection direction

```text
agent ──outbound WSS/HTTPS 443──▶ hub address
```

**The agent connects out to the hub.** It opens no listener and publishes no port, so
this host needs no inbound rule, no port forward and no firewall exception. The hub
never dials back.

How the hub's address is reachable from this host — VPN, private network, or another
deliberate policy — is your deployment decision. The agent only has to be able to
reach it.

## What this provides

Running as an ordinary container — no host networking — the agent reports:

| | |
|---|---|
| **Host** | CPU (total and per core), memory and swap, root-filesystem usage, disk I/O, load average |
| **Containers** | discovery, per-container CPU, per-container memory, per-container network |

**What it does not provide: host NIC / interface bandwidth statistics.** A container
cannot see the host's network namespace. Rather than report this container's own
interface counters as if they were the host's, the stack ships `NICS=-*`, which
selects no interface and omits the field.

**Consequently Beszel's system *Bandwidth* alert cannot be used for this host.** Every
other alert — CPU, memory, disk, temperature, system down — works normally, and
per-container network statistics are unaffected.

## Prerequisites

- A running Beszel hub ([`monitoring/beszel/`](../beszel/))
- Its address, reachable from this host
- A registration token and the hub's public key, both from the hub UI

## Setup

```bash
cp .env.example .env
```

Four values in `.env`:

```bash
HUB_URL=https://beszel.example.com        # required — the agent refuses to start without it
AGENT_TOKEN=...                            # hub UI → Settings → Tokens & Fingerprints
AGENT_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...   # hub UI → + Add System
AGENT_SYSTEM_NAME=hostb                    # without it the agent registers under its container ID
```

The same token and key work for every agent — one hub, many agents.

```bash
docker compose up -d
docker compose logs -f
# Expected: "WebSocket connected"
```

The host registers itself and appears in the hub UI with a green dot within about ten
seconds. There is nothing to enter in **+ Add System** — the agent does not wait to be
found.

## Upgrading from the SSH-registered agent

Earlier versions ran this agent with host networking and an inbound listener on
`45876`. That model is gone — the agent now connects out, and this host opens no port.

An existing `.env` still resolves, but **this stack will not start until you set
`HUB_URL`**, and will not report until you also set `AGENT_TOKEN` and
`AGENT_SYSTEM_NAME`. `AGENT_PORT` no longer exists; there is no listener to configure.

The agent registers as a **new** system. The old SSH-registered entry stops reporting
and can be deleted once the new one shows up. Details in
[`CHANGELOG.md`](../../CHANGELOG.md).

## Security Model

| Aspect | Detail |
|---|---|
| **Auth** | Registration token plus the hub's Ed25519 public key. The agent opens the connection over TLS. |
| **No inbound port** | The agent opens no listener and publishes nothing. There is no port on this host to restrict, so no firewall rule or VPN ACL is required to make it safe. |
| **Outbound only** | The agent sits on two networks: `app-internal` (`internal: true`) to reach the socket proxy, and `app-egress` for the one outbound path it needs — dialling the hub. The socket proxy stays on `app-internal` alone and has no route out. |
| **Docker socket** | The agent never touches `/var/run/docker.sock`. `socket-proxy` holds it read-only and is the only container that does; the agent reaches it by service name. Permissions are `CONTAINERS=1` and `PING=1` — nothing else, `POST=0`. Verified against a live daemon: exactly sufficient for discovery, per-container CPU, memory and network. A compromise of the agent gets that same narrow read-only API, not root on the host. |

## Backup

Nothing to back up. The agent holds no state — it reads host and container metrics
and reports them to the hub. After a loss, redeploy and register it against the same
hub key.

The state that matters lives in [`monitoring/beszel/`](../beszel/) — see its
`## Backup` section.

## Known Issues

- **`APP_TAG` is pinned** — keep in sync with the hub version. Check [releases](https://github.com/henrygd/beszel/releases) before upgrading.
- **`403 Forbidden` for `/version` and `/info`** in debug logs — expected. The socket proxy grants neither; the agent treats both as non-fatal.
- **Host NIC bandwidth is unavailable** and the system Bandwidth alert cannot fire — see [What this provides](#what-this-provides).
