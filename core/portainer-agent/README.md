# Portainer Agent

> **Status: Draft — not yet live-tested.**

Remote Docker agent for [Portainer](../portainer/). Runs on each additional host you want to manage from a central Portainer UI.

**When you need it:**
- You have Portainer running on Host A and want to manage Docker on Host B, C, D from the same UI
- Multi-host homelab / small-fleet setup

**When you don't need it:**
- Portainer and your Docker daemon are on the same host → use [`core/portainer/`](../portainer/) alone, the Agent is unnecessary

## Counterpart

This is the Portainer equivalent of [`core/hawser/`](../hawser/) (which is the Dockhand agent). If you chose Dockhand as your Docker UI, use Hawser on remote hosts. If you chose Portainer, use this Agent.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `agent` | `portainer/agent:2.x` | Exposes Docker API on port 9001 with shared-secret auth |

## Setup

Run this on each **remote** host that the central Portainer should manage.

```bash
cp .env.example .env
# Generate a strong shared secret
openssl rand -hex 32 > /tmp/agent-secret
sed -i "s|^AGENT_SECRET=.*|AGENT_SECRET=$(cat /tmp/agent-secret)|" .env
# Save the secret — you'll paste it into the central Portainer UI
cat /tmp/agent-secret
rm /tmp/agent-secret

docker compose up -d
```

Then in the central Portainer UI:

1. Settings → Environments → Add environment
2. Connection type: **Agent**
3. Environment URL: `<remote-host-ip-or-tailscale>:9001`
4. Paste the shared secret
5. Test connection → Add

## Security Model

- **Port 9001 must only be reachable from the central Portainer server.** Typical options:
  - Tailscale / WireGuard private network (recommended)
  - LAN-only with firewall rule pinning the source to the Portainer host
  - Public exposure behind additional TLS / Authentik is possible but not shipped here
- **`AGENT_SECRET`** is the only authentication — treat it like a root password for Docker on this host.
- **Direct `/var/run/docker.sock` mount** — Portainer Agent needs broad Docker API access. A filtered socket-proxy is technically possible but the allow-list has to be so wide that the security gain is marginal. Upstream recommends direct socket.
- **`/host:ro` mount** — Portainer uses this to show host volumes / paths in the UI. Read-only. Can be dropped if you don't need host-path browsing.
- **`no-new-privileges:true`** on the container.

## Known Issues

- **Live-tested: no.**
- **`APP_TAG=2.39.1`** — keep in sync with the central Portainer version. Version mismatch between server and agent usually works but can cause UI quirks.
- **No Traefik integration** — the agent speaks TCP (not HTTP), so it bypasses Traefik. Port 9001 is bound directly on the host.

## Details

- Docker Hub: https://hub.docker.com/r/portainer/agent
- Docs: https://docs.portainer.io/admin/environments/add/docker-standalone
