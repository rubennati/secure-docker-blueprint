# Upstream Reference

## Source

- **Project:** https://beszel.dev
- **GitHub:** https://github.com/henrygd/beszel
- **Docker Hub:** https://hub.docker.com/r/henrygd/beszel
- **License:** MIT
- **Origin:** US · Henry Gd (community) · non-EU
- **Domain:** Monitoring
- **Role:** Lightweight host and per-container metrics hub
- **Based on version:** `0.19.0`
- **Last verified:** 2026-09-08 (0.19.0) — v0.8.0 host session: hub and the local agent on one host, owner account from the UI, the system registered at the host's Tailscale address, live host and per-container figures (38 containers), a disk-usage alert crossed on purpose and delivered through ntfy to an iPhone. The standalone `monitoring/beszel-agent` stack was not part of it — no second host.

## What we use

- Official `henrygd/beszel` image (hub — the central dashboard + data store)
- Built-in SQLite database via PocketBase
- Traefik labels for HTTPS routing
- Agents on remote hosts connect back to the hub via SSH tunnel

## Architecture

Beszel has two components in this blueprint:

| Component | Directory | Purpose |
|---|---|---|
| **Hub** | `monitoring/beszel/` | Central dashboard, data storage, user management |
| **Agent** | `monitoring/beszel-agent/` | Lightweight collector on each monitored host |

Agents connect to the hub over an SSH key pair — no inbound ports needed on agent hosts.

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 8090:8090`** | Blueprint routing standard |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`acc-tailscale` default access** | Monitoring UI should not be public |
| **SSH key stored in `.secrets/`** | Blueprint secret management pattern |
| **Socket proxy instead of a direct socket mount on the local agent** | The agent's Docker client only calls `/containers/json`, `/containers/{id}/json`, `/containers/{id}/stats` and `/containers/{id}/logs` (`agent/docker.go` upstream) — `tecnativa/docker-socket-proxy` with `CONTAINERS=1` covers exactly that, `POST=0` blocks everything else. Same image and discovery-only shape as `core/traefik`; not the lifecycle-control shape `core/portainer` needs. The agent reaches it by service name on the stack's `internal: true` network — no published port, no fixed address. Verified against a live daemon: that permission set is exactly sufficient for discovery, per-container CPU, memory and network; `/version` and `/info` answer `403` and the agent treats both as non-fatal. |

## Upgrade checklist

1. Check [Beszel releases](https://github.com/henrygd/beszel/releases) — hub and agent should be kept on the same version
2. Back up hub data:

   ```bash
   cp -r volumes/data/ beszel-backup-$(date +%Y%m%d)/
   ```

3. Bump `APP_TAG` in `.env` for both hub and all agent deployments
4. Upgrade hub first, then agents
5. `docker compose pull && docker compose up -d`
6. Verify: all agent hosts reconnect and show metrics

## Useful commands

```bash
# View hub logs
docker compose logs hub --follow

# Generate SSH key pair for agent authentication
ssh-keygen -t ed25519 -f .secrets/beszel_key -N ""
# Public key goes into agent's BESZEL_HUB_URL config or the hub's system settings

# Inspect socket proxy permissions in effect
docker compose exec socket-proxy env | grep -v ^_
```
