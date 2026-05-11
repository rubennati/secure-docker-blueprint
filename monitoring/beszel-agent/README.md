# Beszel Agent

**Status: ✅ Ready — v0.18.7 · 2026-05-11**

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

The hub SSHes INTO this agent — not the other way around. The agent only listens on port 45876. The hub needs to reach this host on that port (e.g. via Tailscale).

## Prerequisites

- A running Beszel hub ([`monitoring/beszel/`](../beszel/))
- The hub's SSH public key (from hub UI → **+ Add System**, top right)
- Network connectivity from the hub to this host on port 45876 (Tailscale recommended)

## Setup

```bash
cp .env.example .env
```

Set `AGENT_KEY` to the hub's full SSH public key including the type prefix:

```bash
# .env
AGENT_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
```

The same key works for all agents — one hub keypair, many agents.

```bash
docker compose up -d
docker compose logs -f
# Expected: "Starting SSH server on :45876"
```

Then in the hub UI: **+ Add System** (top right) → enter this host's Name, Tailscale IP, and port 45876 → **Add System**. The host appears with a green dot within ~10 seconds.

## Security Model

| Aspect | Detail |
|---|---|
| **Auth** | Ed25519 SSH key — only the hub with the matching private key can connect. |
| **Port 45876 on host network** | The agent binds directly on the host's network stack (not behind Traefik). This is not an HTTP service — SSH/TCP only. Restrict port 45876 to the hub's IP via Tailscale ACLs or host firewall (`ufw allow from <hub-tailscale-ip> to any port 45876`). |
| **Docker socket** | Mounted read-only (`:ro`). Agent reads stats but cannot control Docker. Remove the volume if container-level metrics are not needed. |
| **network_mode: host** | Required for accurate host network interface stats (eth0, tailscale0 etc.). Without it, the agent reports only the container's veth interface. CPU / RAM / disk work fine with bridge networking if you prefer isolation over accurate network stats. |

## Known Issues

- **`APP_TAG=0.18.7` is pinned** — keep in sync with the hub version. Check [releases](https://github.com/henrygd/beszel/releases) before upgrading.
- **`WARN HUB_URL not set`** in logs — harmless. Optional WebSocket fallback mode; SSH mode is what we use.
- **Multiple agents on the same host** — change `PORT` per agent to avoid conflicts.
