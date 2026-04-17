# Upstream Reference

## Source

- **Immich project:** https://immich.app/
- **GitHub:** https://github.com/immich-app/immich
- **Stock compose:** https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml
- **License:** AGPL-3.0
- **Based on version:** `v2` (Immich 2.x line)
- **Last checked:** 2026-04-17

## What we use

- Upstream `ghcr.io/immich-app/immich-server` + `immich-machine-learning`
- Upstream `ghcr.io/immich-app/postgres` with pgvectors + vectorchord
- `valkey/valkey:8` (Redis-compatible, license-clean alternative)
- Docker Secrets for DB password (Postgres side) + duplicate inline for Immich
- Bind-mount `./volumes/postgres`, `./volumes/redis`, `./volumes/model-cache`
- Configurable `UPLOAD_LOCATION` (defaults to `./volumes/library`)

## What we changed and why

| Change | Reason |
|--------|--------|
| **Traefik labels instead of `ports: 8008:2283`** | Blueprint routes via Traefik |
| **`POSTGRES_PASSWORD_FILE` instead of inline `POSTGRES_PASSWORD`** | Docker Secrets pattern; inbox had `DB_PASSWORD=postgres` placeholder |
| **`DB_PWD_INLINE` added for immich-server** | Immich has no `_FILE` support for `DB_PASSWORD` — same pattern as BookStack / Vaultwarden |
| **`app-internal` network (`internal: true`)** | Isolate DB + Redis + ML from proxy and host |
| **`security_opt: no-new-privileges`** on all services | Baseline |
| **`read_only: true` + tmpfs on redis** | Hardening consistent with Paperless-ngx |
| **Container names standardized** — `immich-app/db/redis/ml` instead of `immich_server/immich_postgres/…` | Blueprint naming convention |
| **`DB_TAG` / `APP_TAG` / `REDIS_TAG` as variables** | Blueprint pinning convention |
| **Digest pinning dropped for the Postgres + Valkey images** | Inbox pinned by digest; blueprint pins by tag. Upgrade discipline handled via `APP_TAG` bump + documented in Upgrade checklist |
| **Access `acc-public` + security `sec-2` defaults** | Typical for photo-sharing; consider `acc-tailscale + sec-3` for family-only |

## Upgrade checklist

1. Check [Immich releases](https://github.com/immich-app/immich/releases) — breaking changes especially in v-major bumps (2.x → 3.x)
2. Back up:
   ```bash
   # DB dump
   docker compose exec -T db sh -c \
     'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > immich-db-$(date +%Y%m%d).sql
   # Upload volume
   tar czf immich-library-$(date +%Y%m%d).tgz volumes/library/
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch logs for DB migrations:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, browse timeline, upload a new photo, confirm thumbnail + ML tags appear

### Rollback

Restore DB dump and `volumes/library/`, revert `APP_TAG`.

## Related images

- `ghcr.io/immich-app/postgres` — follow Immich release notes; the `14-vectorchord…-pgvectors…` tag encodes extension versions. A major Postgres bump requires a `pg_dumpall`/restore cycle.
- `valkey/valkey` — safe within `8.x`.

## Hardware acceleration (not enabled by default)

Immich supports GPU/NPU transcoding and ML inference. Not configured here to keep the default portable. To enable:

- For ML: change `machine-learning.image` to one of `${APP_TAG}-cuda`, `-rocm`, `-openvino`, `-armnn`, `-rknn` and add the matching `extends:` block from Immich's `hwaccel.ml.yml`.
- For transcoding: add `extends:` from `hwaccel.transcoding.yml` on the `app` service.

See [Immich hwaccel docs](https://docs.immich.app/features/ml-hardware-acceleration).

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Manual DB backup (pg_dump)
docker compose exec -T db sh -c \
  'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# Immich CLI (inside the container)
docker compose exec app immich --help

# Clear ML model cache (force re-download)
docker compose down
rm -rf volumes/model-cache/*
docker compose up -d
```
