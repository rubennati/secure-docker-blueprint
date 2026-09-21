# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/fnsys/dockhand
- **GitHub:** https://github.com/Finsys/dockhand
- **Docs:** Project-internal (see image description on Docker Hub)
- **License:** BSL 1.1 — source-available, **not** open source. Each version converts to Apache-2.0 four years after Licensor first distributes it publicly, so the date differs per version rather than being one fixed day
- **Use restrictions:** production use is granted free only for personal non-commercial use, recognised non-profit and charitable organisations, and schools or non-commercial research institutions. **Production use by or on behalf of a company, sole trader, public body or any other organisation requires a Commercial Licence**, and offering it to third parties as a hosted, managed or SaaS container-management service requires a separate written agreement — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Edition gating:** Enterprise Features are gated by a License Key, which the licence forbids sharing, publishing or circumventing — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/Finsys/dockhand/blob/main/LICENSE.md · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Finsys · **no country or legal entity stated** — no imprint on fnsys.pro or dockhand.pro
- **Domain:** Infrastructure
- **Role:** Docker management with Git-based stacks: deploy and update by pushing to Git
- **Based on version:** `v1.0.47`
- **Last checked:** 2026-04-16

## What we use

- Official `fnsys/dockhand` image, pinned tag
- `postgres:16-alpine` as backend database
- `tecnativa/docker-socket-proxy` with a restricted permission set for Docker API access

## What we changed and why

| Change | Reason |
|--------|--------|
| Custom entrypoint wrapper (`config/entrypoint.sh`) | Reads `DB_PWD` and `ENCRYPTION_KEY` from Docker Secrets at runtime; Dockhand itself does not support `_FILE` env vars |
| Socket proxy instead of direct socket mount | Dockhand requires Docker API access but must not get the raw socket; the proxy filters to only the required endpoints |
| `POSTGRES_INITDB_ARGS: --data-checksums` | Extra integrity checks on the PostgreSQL data files |
| `read_only: true` + `tmpfs` on socket proxy | Defense in depth — the proxy container has no writable root filesystem |
| TLS profile `tls-modern` + `acc-tailscale` + `sec-4` | Admin tool, VPN-only, strict rate limiting |

## Version / tag notes

- `v1.0.39` → `v1.0.47` on 2026-09-13, eight patches. No published advisory against either.

## Upgrade checklist

1. Check the new Dockhand release for breaking changes and migration notes: https://hub.docker.com/r/fnsys/dockhand/tags
2. Back up the Postgres volume (`./volumes/postgres/`) — Dockhand stores stack definitions here
3. Back up `./volumes/data/` — Git repo clones and encryption state
4. Bump `APP_TAG` in `.env`
5. `docker compose pull && docker compose up -d`
6. Check: `docker compose logs app --tail 100` for DB migration messages or startup errors
7. Verify the web UI loads, existing stacks are still listed and can be reconciled

## Related images to keep in sync

- `postgres:16-alpine` — upgrade within minor versions is safe; major upgrades (15 → 16) require a manual `pg_upgrade` procedure, not covered here
- `tecnativa/docker-socket-proxy` — safe to update within the same major version

## Useful commands

```bash
# Shell into the app container
docker compose exec app sh

# Show Dockhand's effective DATABASE_URL (after entrypoint assembled it)
docker compose exec app env | grep DATABASE_URL

# Inspect socket proxy permissions in effect
docker compose exec socket-proxy env | grep -v ^_

# Backup Postgres dump
docker compose exec db pg_dump -U dockhand dockhand > dump.sql

# Restore Postgres dump (into a fresh DB — see upgrade checklist)
cat dump.sql | docker compose exec -T db psql -U dockhand -d dockhand
```
