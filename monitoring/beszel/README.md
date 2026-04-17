# Beszel

> **Status: Draft — not yet live-tested.**

Lightweight server monitoring with a hub + agent architecture. Go-based, ~20 MB RAM per agent. Modern alternative to Zabbix / Netdata for homelab + small-fleet use cases.

## Architecture

Hub + Agents model. Agents push CPU / RAM / disk / network / per-container docker stats to the hub over SSH.

| Service | Image | Purpose |
|---------|-------|---------|
| `hub` | `henrygd/beszel:0` | Web UI + SQLite metric store + auth |
| `agent` | `henrygd/beszel-agent:0` | Local host metrics collector |

This compose deploys the hub + one local agent together. For additional hosts, install the agent separately on each and point it at the hub URL with the same SSH key.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p volumes/hub-data

# First-time two-phase start (agent key comes from the hub UI)
docker compose up -d hub
docker compose logs hub --follow
# Watch for: "Server started at http://0.0.0.0:8090"

# 1. Open https://<APP_TRAEFIK_HOST> and create the owner account
# 2. Settings → "Add agent" → copy the SSH public key
# 3. Paste into AGENT_KEY= in .env

docker compose up -d agent
# Agent appears in the hub after ~10 seconds
```

## Adding more hosts

On any remote host (Tailnet, LAN, or via SSH tunnel):

```yaml
# /opt/beszel-agent/docker-compose.yml
services:
  agent:
    image: henrygd/beszel-agent:0
    restart: unless-stopped
    network_mode: host
    environment:
      PORT: 45876
      KEY: "<same SSH pubkey as hub-generated>"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Then add the host in the hub UI with its IP / Tailscale name and port 45876.

## Security Model

- **Hub stores all historical metrics + auth state** in `volumes/hub-data/`. Back this up.
- **Agent auth is SSH-key based** — the hub generates an Ed25519 keypair on first start; agents need only the public key.
- **Default access `acc-tailscale` + `sec-3`** — host metrics reveal CPU, RAM, disk layout, running containers. VPN-only by default.
- **Agent runs with `network_mode: host`** by default to report accurate network interface stats. If you don't need that, switch to the `beszel-internal` bridge network.
- **Docker socket is read-only** — agent reads `docker stats`-equivalent data but cannot control the daemon.

## Known Issues

- **Live-tested: no.**
- **Two-phase start required on first setup** — the agent key is only available from the hub UI after the hub is running.
- **`APP_TAG=0` tracks pre-1.0** — Beszel is young (2024+). Breaking changes are still possible. Pin to a specific version for stability.
- **Host-network agent** — if you run multiple agents on the same host (rare), adjust `PORT` per agent.
- **No PagerDuty / Opsgenie-native alerts yet** — webhook-based alerting works; route via n8n for richer routing.
