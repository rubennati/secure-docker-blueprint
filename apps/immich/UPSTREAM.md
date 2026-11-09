# Upstream Reference

## Source

- **Immich project:** https://immich.app/
- **GitHub:** https://github.com/immich-app/immich
- **Stock compose:** https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml
- **License:** AGPL-3.0
- **Edition gating:** none — upstream states that "all features will be free, forever" and that nothing will be put behind a paywall; buying a product supports the developers and unlocks nothing — https://docs.immich.app/overview/support-the-project/ · checked 2026-09-21
- **Commercial model:** free self-hosted — https://docs.immich.app/overview/support-the-project/ · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** US · Alex Tran · non-EU
- **Domain:** Photos
- **Role:** Photo and video backup with mobile apps and machine-learning search
- **Last verified:** 2026-11-08 (v3.3.6) — lab host (VM), IPv4 LAN, fresh install with the PR #340 hardening (Postgres 14 with vectorchord, Valkey with cap_drop): the admin created through `admin-sign-up`, a second admin setup refused, an image uploaded and downloaded byte-identical after `down`/`up`, `/api/server/ping` 200, the refused client answered `403`; a restore through `docker exec` (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Upstream `ghcr.io/immich-app/immich-server` + `immich-machine-learning`
- Upstream `ghcr.io/immich-app/postgres` with VectorChord, digest-pinned
- `valkey/valkey:9` (Redis-compatible, license-clean alternative)
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
| **Postgres image on a newer VectorChord than upstream's compose** | `14-vectorchord1.1.1` instead of `14-vectorchord0.4.3-pgvectors0.2.0`, for the CVE fixes in its base image; digest-pinned like upstream. See Version notes |
| **`access-vpn`, `limit-standard` and `headers-standard` as shipped** | The first visitor creates the admin account; open the route (`access-public`) after that for sharing outside the VPN |

## Version notes

- Moved to `v3.3.6` on 2026-11-05, server and machine learning together, not run
  on a host at this tag; `Last verified` stays at `v3.2.0`. No breaking change,
  variable change or database image change in the range; migrations run on start.
  `v3.3.0` offers optimised models behind `MACHINE_LEARNING_MODEL_REVISION=v2`
  (opt-in, not set here). `v3.3.6` turns off onnxruntime telemetry, which had sent
  anonymous metrics to Microsoft from the machine-learning container. Advisories
  fixed: GHSA-q89f-h332-8q2h (high, SVG upload reaching ImageMagick, RCE;
  `v3.2.4`) and GHSA-72rm-x7xr-v679 (unauthenticated filesystem path injection;
  `v3.3.0`). `v3.3.5` carries the eMudhra CA removal and the Node.js October 2026
  security releases. https://github.com/immich-app/immich/releases
- Moved `valkey/valkey` from `8.1.6` to `9.1.3` on 2026-11-05, not run on a host
  at this tag. Immich's own release compose ships `valkey/valkey:9` since
  https://github.com/immich-app/immich/pull/24336
  (https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml).
  Valkey 9 loads the 8.x RDB file in `./volumes/redis` at start; the file it
  writes (RDB version 80) cannot be read by 8.x, so a return to 8.1 starts with
  an empty job queue. Let queued jobs finish before the move; jobs lost from the
  queue can be started again from the administration job page.
- `DB_TAG` moved from `14-vectorchord0.4.3-pgvectors0.2.0` to
  `14-vectorchord1.1.1`, digest
  `sha256:b38cad4a8bdb716d19b07e5afb4a6e2ed9e7f8a5a93f428aae35f495c72d3498`, on
  2026-11-05, not run on a host at this tag. The reason is the CVE fixes in the
  newer base image. Upstream's own compose at `v3.3.6` still ships
  `14-vectorchord0.4.3-pgvectors0.2.0`; Immich `v3.3.6` accepts VectorChord
  `>=0.3 <2` (`VECTORCHORD_VERSION_RANGE` in `server/src/constants.ts`). On
  start, Immich sees the newer extension version, drops the CLIP and face
  indexes, runs `ALTER EXTENSION vchord UPDATE` and rebuilds both indexes
  (`server/src/services/database.service.ts`); the stack's database user is the
  image's superuser, so this needs no manual step. The rebuild takes a while on
  a large library: do not restart in the middle. Once updated, Immich refuses
  the older image (no extension downgrade), so going back means restoring a
  dump. Take one before the tag changes:

  ```bash
  docker compose exec -T db sh -c \
    'pg_dumpall --clean --if-exists -U "$POSTGRES_USER"' \
    > immich-dumpall-$(date +%Y%m%d).sql
  ```

  The new image no longer contains pgvecto.rs. That matters only for an
  install still on pgvecto.rs, which Immich 3.x no longer supports anyway: it
  has to finish the migration to VectorChord on the old image and an Immich
  2.x release first. Sources: https://github.com/immich-app/immich/blob/v3.3.6/docker/docker-compose.yml,
  https://docs.immich.app/administration/postgres-standalone/

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

- `ghcr.io/immich-app/postgres` — follow Immich release notes; the `14-vectorchord…` tag encodes extension versions, and the range Immich accepts is `VECTORCHORD_VERSION_RANGE` in `server/src/constants.ts`. A major Postgres bump requires a `pg_dumpall`/restore cycle.
- `valkey/valkey` — safe within `9.x`.

## Hardware acceleration (not enabled by default)

Immich supports GPU/NPU transcoding and ML inference. Not configured here to keep the default portable. To enable:

- For ML: change `machine-learning.image` to one of `${APP_TAG}-cuda`, `-rocm`, `-openvino`, `-armnn`, `-rknn` and add the matching `extends:` block from Immich's `hwaccel.ml.yml`.
- For transcoding: add `extends:` from `hwaccel.transcoding.yml` on the `app` service.

See [Immich hwaccel docs](https://docs.immich.app/features/ml-hardware-acceleration).

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Manual DB backup — stop the server first, see README "Restore"
docker compose stop app
docker compose exec -T db sh -c \
  'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > dump.sql.gz
docker compose start app

# Restore is not the inverse of this command — see README "Restore"

# Immich CLI (inside the container)
docker compose exec app immich --help

# Clear ML model cache (force re-download)
docker compose down
rm -rf volumes/model-cache/*
docker compose up -d
```
