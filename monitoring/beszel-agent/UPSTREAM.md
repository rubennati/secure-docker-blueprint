# Upstream Reference

## Source

- **Project:** https://beszel.dev
- **GitHub:** https://github.com/henrygd/beszel
- **Docker Hub:** https://hub.docker.com/r/henrygd/beszel-agent
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** US · Henry Gd (community) · non-EU
- **Domain:** Monitoring
- **Role:** Agent that reports a remote host's metrics to Beszel
- **Based on version:** `0.21.1`
- **Last checked:** 2026-05-03

## What we use

- Official `henrygd/beszel-agent` image
- Connects back to the Beszel hub via SSH — no inbound ports required
- Reads Docker socket (read-only) for container metrics

## Architecture note

This is the **agent** component. The hub lives in `monitoring/beszel/`. Keep both on the same version tag.

See `monitoring/beszel/UPSTREAM.md` for the full architecture overview.

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Socket proxy instead of a direct socket mount** | The agent's Docker client only calls `/containers/json`, `/containers/{id}/json`, `/containers/{id}/stats` and `/containers/{id}/logs` (`agent/docker.go` upstream) — `tecnativa/docker-socket-proxy` with `CONTAINERS=1` covers exactly that, `POST=0` blocks everything else. The agent reaches it by service name on the stack's `internal: true` network — no published port, no fixed address. Verified against a live daemon: that permission set is exactly sufficient for discovery, per-container CPU, memory and network; `/version` and `/info` answer `403` and the agent treats both as non-fatal. |
| **SSH public key in env, not baked in** | Blueprint: no credentials in image |
| **`DOCKER_IMAGE_CHECK=false` on the agent** | Since 0.20.0 the agent asks image registries every hour whether a running container's image has a newer digest. That sends the name of every image on the host to Docker Hub and other registries, and the socket proxy grants no `IMAGES` call to read the local digest anyway. Version tracking is the operator's job here |

## Version notes

- Moved to `0.21.1` on 2026-11-05 (released 2026-10-22), with the hub in
  `monitoring/beszel`, not run on a host at this tag. No breaking
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

1. Check [Beszel releases](https://github.com/henrygd/beszel/releases) — always keep agent version in sync with hub
2. Bump `APP_TAG` in `.env` to match `monitoring/beszel/.env` value
3. `docker compose pull && docker compose up -d`
4. Verify: agent reconnects to hub, metrics appear within ~30 seconds
