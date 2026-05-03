# Upstream Reference

## Source

- **Project:** https://beszel.dev
- **GitHub:** https://github.com/henrygd/beszel
- **Docker Hub:** https://hub.docker.com/r/henrygd/beszel-agent
- **License:** MIT
- **Based on version:** `0.18.7`
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
| **Docker socket mounted read-only** | Agent only needs read access for container stats |
| **SSH public key in env, not baked in** | Blueprint: no credentials in image |

## Upgrade checklist

1. Check [Beszel releases](https://github.com/henrygd/beszel/releases) — always keep agent version in sync with hub
2. Bump `APP_TAG` in `.env` to match `monitoring/beszel/.env` value
3. `docker compose pull && docker compose up -d`
4. Verify: agent reconnects to hub, metrics appear within ~30 seconds
