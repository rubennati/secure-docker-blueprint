# Upstream Reference

## Source

- **Image:** https://github.com/goauthentik/authentik/pkgs/container/server
- **GitHub:** https://github.com/goauthentik/authentik
- **Docs:** https://docs.goauthentik.io/
- **Release notes:** https://docs.goauthentik.io/docs/releases/
- **Reference compose:** https://docs.goauthentik.io/docs/installation/docker-compose
- **License:** MIT
- **Origin:** Netherlands · Authentik Security · EU
- **Based on version:** `2026.2.2`
- **Last verified:** 2026-05-03 (v2026.2.2)

## What we use

- Official `ghcr.io/goauthentik/server` image, same image for `server` and `worker` (different `command`)
- `postgres:16-alpine` as primary database
- `redis:7.4-alpine` as session cache + Celery broker
- Native `file://` secret loading (no entrypoint wrapper needed)

## What we changed and why

| Change | Reason |
|--------|--------|
| Four-service layout with `server` and `worker` on the same image | Matches Authentik's documented production architecture — UI/API and background workers are split so worker load doesn't block the user-facing server |
| `server` exposed through Traefik, `worker` isolated | Worker has no HTTP entry point; keeping it off `proxy-public` is pure defence-in-depth |
| `file://` secrets instead of plain env vars | Passwords/secret key never land in `.env` or in `docker inspect` output |
| Redis with `read_only: true` + `tmpfs: /tmp` | No writable root filesystem, Redis only writes to the persistent data volume |
| `AUTHENTIK_ERROR_REPORTING__ENABLED: "false"` | No telemetry leaving the box |
| Internal hostnames via Docker service names (`db`, `redis`) | Survives renaming of `COMPOSE_PROJECT_NAME` without edits; service-name resolution is guaranteed on `app-internal` |
| `app-internal` with `internal: true` | Blueprint baseline — db/redis/worker have no route to the outside |
| `no-new-privileges:true` everywhere | Blueprint baseline |

## Version / tag notes

- Authentik releases use date-based versioning: `YYYY.MM.patch`. Majors (`2024.x` → `2025.x`) can include schema migrations.
- `postgres:16-alpine` — safe to update within Postgres 16. Postgres 16 → 17 is not automatic (dump/restore or `pg_upgrade` required).
- `redis:7.4-alpine` — safe to update within 7.x.

## Upgrade checklist

1. Read the release notes for every intermediate version you skip: https://docs.goauthentik.io/docs/releases/
   - Pay special attention to "Breaking changes" and "Manual action required" sections.
2. Back up database + media volumes:
   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > authentik-db-$(date +%Y%m%d).sql
   tar czf authentik-media-$(date +%Y%m%d).tgz ./volumes/media
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch the server container; schema migrations run on first start:
   ```bash
   docker compose logs server --follow
   ```
   Expect `Applying migration ...` lines and finally `Startup complete`.
6. Verify:
   - Login still works
   - `Admin Interface → System → Tasks` — all worker tasks `Successful`
   - `Admin Interface → System → Configuration` — DB and Redis green

### Rollback

Authentik's migrations are forward-only. Downgrading requires restoring the SQL dump and reverting `APP_TAG`.

## Related images to keep in sync

- `postgres` — same tag for `db`; update within the major version
- `redis` — independent; update within 7.x

## Useful commands

```bash
# Shell into the server
docker compose exec server bash

# Check Authentik's effective config (after file:// resolution)
docker compose exec server ak dump_config

# Manually run a migration check
docker compose exec server ak migrate --check

# Create an admin user (if you missed the initial-setup flow)
docker compose exec server ak create_admin_group akadmins
docker compose exec server ak create_admin_user admin admin@example.com

# Run an arbitrary Django management command
docker compose exec server ak <command>

# PostgreSQL dump / restore
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql
cat dump.sql | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# Live log across server + worker
docker compose logs server worker --follow
```
