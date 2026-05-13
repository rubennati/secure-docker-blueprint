# Beszel

**Status: ✅ Ready — v0.18.7 · 2026-05-11**

Lightweight server monitoring with a hub + agent architecture. Go-based, ~20 MB RAM per agent.

## Architecture

The **hub SSHes INTO each agent** — not the other way around.

| Service | Image | Role |
|---------|-------|------|
| `hub` | `henrygd/beszel:0.18.7` | Web UI + SQLite metric store + SSH client |
| `agent` | `henrygd/beszel-agent:0.18.7` | SSH server that serves host metrics |

On first start the hub generates an Ed25519 keypair. The **public key** goes into each agent's `KEY` env var — this is how the agent decides which hub is allowed to connect. The hub then SSHes to each registered agent on port 45876 to pull CPU / RAM / disk / network / container stats.

This compose runs the hub + one local agent on the **same host**. For additional hosts deploy [`monitoring/beszel-agent/`](../beszel-agent/) there.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p volumes/hub-data
```

### Phase 1 — Hub only

```bash
docker compose up -d hub
docker compose logs hub --follow
# Wait for: "Server started at http://0.0.0.0:8090"
```

Open `https://<APP_TRAEFIK_HOST>` and create the owner account.

### Phase 2 — Get the key and register the local agent

In the hub UI click **+ Add System** (top right). A dialog opens:

| Field | What to enter |
|---|---|
| **Name** | Display name for this host, e.g. `myserver` |
| **Host / IP** | The Tailscale IP (or LAN IP) of this host — not `localhost`. The hub SSHes to this address over the network, even for a local agent. |
| **Port** | `45876` (pre-filled) |
| **Public Key** | Pre-filled by the hub — this is the hub's SSH public key |

Copy the **full public key** from the dialog, including the `ssh-ed25519` type prefix. The base64 portion alone is not valid.

Set it in `.env`:

```bash
# .env
AGENT_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
```

### Phase 3 — Start the agent, then register

```bash
docker compose up -d agent
```

Go back to the "Add System" dialog (still open, or reopen via **+ Add System**), fill in **Name** and **Host / IP**, click **Add System**. The system appears with a green dot within ~10 seconds.

After this first setup, `docker compose up -d` starts both hub and agent together normally.

## Security Model

| Aspect | Detail |
|---|---|
| **Hub ↔ Agent auth** | Ed25519 SSH key — cryptographically strong. Agents reject any connection without the matching private key. |
| **Port 45876 on host network** | The agent binds on the host's network stack directly (not behind Traefik). This is required for accurate host network stats and is a deliberate exception — same pattern as `core/portainer-agent/` and `core/hawser/`. Protect with Tailscale ACLs or host firewall (accept 45876 from hub IP only). |
| **Hub web UI** | `acc-tailscale` + `sec-3` via Traefik — VPN-only access. |
| **Docker socket** | Agent mounts `/var/run/docker.sock:ro` — read-only, agent cannot control Docker. Accepted exception for monitoring agents; no Socket Proxy equivalent covers docker-stats reads. Remove if container metrics are not needed. |
| **Hub data** | SQLite + SSH private key in `volumes/hub-data/`. Back this up — losing it means re-keying all agents. |

## Adding more hosts

Deploy [`monitoring/beszel-agent/`](../beszel-agent/) on each additional host. Same hub public key, different host IP in the "Add System" dialog.

## Known Issues

- **Two-phase start on first install** — see [Setup](#setup). Subsequent starts need no manual steps.
- **`APP_TAG=0.18.7` is pinned** — Beszel is pre-1.0. Check [releases](https://github.com/henrygd/beszel/releases) before upgrading; update both hub and agent together.
- **Both images have no healthcheck** — hub is scratch-based (no shell/wget), agent provides no health endpoint. Both use `healthcheck: disable: true`; hub status in the UI is the reliable liveness signal for all agents.
- **`WARN HUB_URL not set`** in agent logs — harmless. This is for an optional WebSocket fallback mode; SSH mode is what we use.
- **Host network agent** — if you run multiple agents on the same host (rare), set different `PORT` values per agent.
