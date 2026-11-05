# Upstream Reference

## Source

- **Project:** https://beszel.dev
- **GitHub:** https://github.com/henrygd/beszel
- **Docker Hub:** https://hub.docker.com/r/henrygd/beszel
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** US · Henry Gd (community) · non-EU
- **Domain:** Monitoring
- **Role:** Lightweight host and per-container metrics hub
- **Based on version:** `0.21.1`
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
| **`access-vpn` default access** | Monitoring UI should not be public |
| **SSH key stored in `.secrets/`** | Blueprint secret management pattern |
| **Socket proxy instead of a direct socket mount on the local agent** | The agent's Docker client only calls `/containers/json`, `/containers/{id}/json`, `/containers/{id}/stats` and `/containers/{id}/logs` (`agent/docker.go` upstream) — `tecnativa/docker-socket-proxy` with `CONTAINERS=1` covers exactly that, `POST=0` blocks everything else. Same image and discovery-only shape as `core/traefik`; not the lifecycle-control shape `core/portainer` needs. The agent reaches it by service name on the stack's `internal: true` network — no published port, no fixed address. Verified against a live daemon: that permission set is exactly sufficient for discovery, per-container CPU, memory and network; `/version` and `/info` answer `403` and the agent treats both as non-fatal. |
| **`DOCKER_IMAGE_CHECK=false` on the agent** | Since 0.20.0 the agent asks image registries every hour whether a running container's image has a newer digest. That sends the name of every image on the host to Docker Hub and other registries, and the socket proxy grants no `IMAGES` call to read the local digest anyway. Version tracking is the operator's job here |

## Version notes

- Moved hub and agent to `0.21.1` on 2026-11-05 (released 2026-10-22), together,
  not run on a host at this tag; `Last verified` stays at 0.19.0. No breaking
  change for a Docker deployment between 0.19.0 and 0.21.1 (0.21.1's
  `Agent.Start` signature change concerns only Go code that embeds the agent).
  New, from the release notes (https://github.com/henrygd/beszel/releases):
  - 0.20.0: the agent checks image registries hourly for newer image digests.
    Turned off here with `DOCKER_IMAGE_CHECK: "false"` (added in 0.21.0, see
    the table above; https://beszel.dev/guide/environment-variables).
    `TRUSTED_PROXY_IPS` restricts `TRUSTED_AUTH_HEADER`, not used here.
  - 0.21.0: `DISABLE_SSH` on the hub (agents must then connect over WebSocket,
    as the agent here already does), `SYNC_SYSTEM_NAMES`.
  - 0.21.1: a user created from `USER_EMAIL` becomes an admin (not set here);
    the memory fields other than the percentage are deprecated in the API in
    favour of byte values, which matters only to integrations reading it;
    `HUB_HEADERS`, `CONTAINER_NAME_LABEL`, `OAUTH_DEFAULT_USER_ROLE`.
  - Security fixes, no advisory IDs: session state cleared after token expiry
    (0.20.0); alert subscriptions and delivery require access to the system,
    SSH request cancellation honoured, unknown frontend routes no longer answer
    `200` (0.21.0); record ownership can no longer be reassigned through an
    update, universal tokens no longer appear in request URLs, agent tokens are
    masked until revealed (0.21.1).

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
