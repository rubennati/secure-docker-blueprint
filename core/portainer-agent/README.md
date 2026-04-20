# Portainer Agent

> **Status: Draft — not yet live-tested.**

Remote Docker agent for [Portainer](../portainer/). Runs on each additional host that a central Portainer should manage.

> ⚠️ **Requires an extra port on the central Portainer host.** Unlike the Dockhand + Hawser pair (which stays on standard HTTPS 443 through Traefik), Portainer Edge Agents connect back on TCP 8000 — a separate port that has no TLS and only `EDGE_KEY` as authentication.
>
> The blueprint's default `core/portainer/` compose does NOT publish that port. If you deploy Agents, you have to enable it manually and bind it to a private interface (Tailscale / WireGuard). See [Setup](#setup) below.
>
> If you don't want that extra exposure, use [Dockhand + Hawser](../hawser/) instead — equivalent multi-host capability without opening additional ports.

**When you need this:**
- Portainer runs on Host A, you want to manage Docker on Host B, C, D from the same UI
- You already picked Portainer as your UI and need to scale beyond one host

**When you don't need this:**
- Portainer and Docker are on the same host → [`core/portainer/`](../portainer/) alone is enough
- You haven't committed to Portainer yet → Dockhand + Hawser is the cleaner multi-host path

## Counterpart

Parallel to [`core/hawser/`](../hawser/) (the Dockhand agent). Pick whichever UI stack you use:

| Central UI | Agent on remote hosts | Extra port on central? |
|---|---|---|
| `core/dockhand/` | `core/hawser/` | No — 443 only |
| `core/portainer/` | `core/portainer-agent/` ← this | Yes — TCP 8000 on Tailscale-bound address |

## Setup

### Step 1 — Expose port 8000 on the central Portainer host

In `core/portainer/docker-compose.yml` on the host where central Portainer runs, add under the `app` service `# --- Networking ---` block:

```yaml
    ports:
      - "<your-tailscale-ip>:8000:8000/tcp"
```

Bind to the Tailscale / WireGuard interface only — never `0.0.0.0`. Port 8000 has no TLS and only `EDGE_KEY` as authentication, so public exposure is not an option.

Apply and verify:

```bash
docker compose up -d --force-recreate app
ss -tlnp | grep 8000
# Expected: LISTEN ... <your-tailscale-ip>:8000 ...
```

### Step 2 — Register the environment in the central Portainer UI

1. Open the central Portainer UI
2. Environments → **Add environment** → Docker Standalone → **Edge Agent Standard**
3. Give it a name
4. **Click `Add` to save** — the environment record must exist before the agent can connect. Generating `EDGE_ID` / `EDGE_KEY` without saving causes the agent to loop with a failed handshake.
5. After saving, the wizard shows `EDGE_ID` and `EDGE_KEY` — copy both

> **About the URL:** `EDGE_KEY` is a base64 bundle that already contains the Portainer server URL + auth. No separate URL env var is needed. Decode to inspect: `echo '<EDGE_KEY-value>' | base64 -d`

### Step 3 — Deploy the agent on the remote host

```bash
cd core/portainer-agent
cp .env.example .env
# Paste the two values from Step 2:
sed -i "s|^EDGE_ID=.*|EDGE_ID=<id-from-wizard>|" .env
sed -i "s|^EDGE_KEY=.*|EDGE_KEY=<key-from-wizard>|" .env

docker compose up -d
docker compose logs -f
```

### Step 4 — Verify

- Agent log shows `Connected` — no `connection refused` loop
- Central Portainer UI → Environments: the new environment shows as `Connected` within ~30 seconds
- From another host on the same Tailnet:
  ```bash
  # Tailscale interface reachable
  curl --connect-timeout 3 http://<central-tailscale-ip>:8000
  # Public interface NOT reachable
  curl --connect-timeout 3 https://<central-public-ip>:8000
  # Expected: timeout / refused
  ```

## Alternative: Classic Mode (inbound TCP 9001 on the agent)

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
