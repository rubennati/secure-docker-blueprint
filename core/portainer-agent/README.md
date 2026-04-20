# Portainer Agent

> **Status: Draft — not yet live-tested.**

Remote Docker agent for [Portainer](../portainer/). Runs on each additional host that a central Portainer should manage.

**When you need it:**
- Portainer runs on Host A, you want to manage Docker on Host B, C, D from the same UI
- Multi-host homelab / small-fleet setup

**When you don't need it:**
- Portainer and Docker are on the same host → [`core/portainer/`](../portainer/) alone is enough

## Counterpart

Parallel to [`core/hawser/`](../hawser/) (the Dockhand agent). Pick whichever UI stack you use:

| Central UI | Agent on remote hosts |
|---|---|
| `core/dockhand/` | `core/hawser/` |
| `core/portainer/` | `core/portainer-agent/` ← this |

## Modes

Two connection modes; pick one.

### Edge Mode (default, recommended)

Agent opens an outbound WebSocket to the central Portainer server. **No inbound port required on the agent host** — works behind NAT, firewalls, Tailscale / WireGuard.

**On the central Portainer host** port 8000 must be reachable from the agent. In this blueprint, that means uncommenting the `ports:` block in [`core/portainer/docker-compose.yml`](../portainer/docker-compose.yml) and setting `PORTAINER_EDGE_BIND` to the central host's Tailscale IP. Do NOT bind 0.0.0.0 — port 8000 has no TLS, authentication is `EDGE_KEY` only.

**About the URL:** `EDGE_KEY` is a base64 bundle that already contains the Portainer server URL + auth. No separate URL env var is needed. To verify what's inside:

```bash
echo '<EDGE_KEY-value>' | base64 -d
```

Setup flow:

1. In the **central Portainer UI:** Environments → Add environment → Docker Standalone → **Edge Agent Standard**
2. Wizard shows `EDGE_ID` and `EDGE_KEY` — copy both
3. On the remote host:
   ```bash
   cp .env.example .env
   # Paste the two values from the wizard:
   sed -i "s|^EDGE_ID=.*|EDGE_ID=<id-from-wizard>|" .env
   sed -i "s|^EDGE_KEY=.*|EDGE_KEY=<key-from-wizard>|" .env

   docker compose up -d
   docker compose logs -f
   ```
4. Back in Portainer UI: environment shows as connected within ~30 s

### Classic Mode (inbound TCP 9001)

Only if Edge Mode doesn't fit — e.g. central Portainer has no internet egress. Agent listens on port 9001, central Portainer connects inbound with a shared secret.

See the `docker-compose.yml` comments for the switch. You'll need to:
- Swap environment variables to `AGENT_SECRET` + port 9001 mapping
- Expose port 9001 only on a trusted interface (Tailscale, private LAN)

## Security Model

- **`EDGE_KEY` (or `AGENT_SECRET`)** is the only authentication — treat it like a root password for Docker on this host.
- **Direct `/var/run/docker.sock` mount** — Portainer Agent needs broad Docker API access (containers, volumes, networks, images, swarm, tasks, secrets, configs, exec, build). A filtered socket-proxy would have to allow nearly all endpoints, so the security gain is marginal. Same trade-off as [`core/hawser/`](../hawser/).
- **`/host:ro` mount** — Portainer uses this to show host volumes / paths. Read-only. Drop if host-path browsing isn't needed.
- **`no-new-privileges:true`** on the container.

## Known Issues

- **Live-tested: no.**
- **`APP_TAG=2.39.1`** — keep in sync with the central Portainer major version.
- **Edge Mode needs outbound HTTPS to the central Portainer** — typically 443. Check egress firewall if the agent never shows as connected.

## Details

- Docker Hub: https://hub.docker.com/r/portainer/agent
- Edge Agent docs: https://docs.portainer.io/admin/environments/add/docker-standalone#edge-agent-standard
