# Upstream Reference

## Source

- **Project:** https://beszel.dev
- **GitHub:** https://github.com/henrygd/beszel
- **Docker Hub:** https://hub.docker.com/r/henrygd/beszel
- **License:** MIT
- **Origin:** US · Henry Gd (community) · non-EU
- **Based on version:** `0.18.7`
- **Last checked:** 2026-05-03

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
```
