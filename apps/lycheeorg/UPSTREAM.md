# Upstream Reference

## Source

- **Lychee project:** https://lycheeorg.dev/
- **GitHub:** https://github.com/LycheeOrg/Lychee
- **Docker repo:** https://github.com/LycheeOrg/Lychee-Docker
- **Docker Hub:** https://hub.docker.com/r/lycheeorg/lychee
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** Community · LycheeOrg · EU contributors
- **Domain:** Photos
- **Role:** Photo gallery
- **Based on version:** `v7.12.1`
- **Last checked:** 2026-04-17

## What we use

- `lycheeorg/lychee` as the Laravel app
- Official `mariadb:12.3` as backend
- Official `redis:8.10-alpine` for cache and sessions
- Docker Secrets for DB password, DB root password — natively consumed by both services
- Bind-mounts under `./volumes/` for `/conf`, `/uploads`, `/sym`, `/logs`, `/lychee-tmp`

## What we changed and why

| Change | Reason |
|--------|--------|
| **Hardcoded `APP_KEY` removed** — inbox had a plaintext Laravel key | Shared key = backdoor across copies. Now `__REPLACE_ME__` with `artisan key:generate --show` documented in Setup |
| **Default passwords replaced** — inbox had `DB_ROOT_PASSWORD=rootpassword`, `DB_PASSWORD=lychee`, `REDIS_PASSWORD=defaultdefault` | All now secrets or removed |
| **`DB_PASSWORD_FILE` used natively** — inbox commented the option out and passed the password inline | Lychee reads `DB_PASSWORD_FILE` directly; using Docker Secrets avoids the `DB_PWD_INLINE` duplication pattern |
| **Redis password removed** | Redis is on `app-internal` only; password was `defaultdefault` placeholder anyway. Add a password if exposing redis externally |
| **Redis port `6379:6379` exposure removed** | Inbox bound Redis to host; blueprint keeps it internal-only |
| **Odd `user: 1026:100` on redis removed** | Synology-specific hack from the upstream example; not needed for a generic deployment |
| **Traefik labels instead of `ports: 8026:80`** | Blueprint routes via Traefik |
| **`APP_URL` changed** — inbox defaulted to `http://localhost` | Now `https://${APP_TRAEFIK_HOST}` |
| **`app-internal` network (`internal: true`)** | Isolate DB + Redis from host and proxy |
| **`security_opt: no-new-privileges`** + MariaDB `cap_drop: ALL` | Baseline hardening, consistent with BookStack / Ghost / WordPress MariaDB services |
| **`read_only: true` + tmpfs on redis** | Hardening consistent with Paperless-ngx |
| **Named volumes `lychee_prod_mysql`, `lychee_prod_redis` → bind mounts** | Blueprint uses `./volumes/` bind mounts for predictable backup paths |
| **`TRUSTED_PROXIES: "*"`** added | Required so Laravel honours `X-Forwarded-Proto=https` from Traefik (otherwise Lychee generates `http://` absolute URLs → Mixed Content warnings) |
| **Container names standardized** — `lychee-app/db/redis` instead of `lychee/lychee_db/lychee_redis` | Project-scoped naming |
| **100+ lines of commented env-var examples trimmed** | Moved to upstream docs reference; `.env.example` is lean. Every dropped option remains available via standard env vars if needed |
| **Access `access-public`, `limit-standard` and `headers-standard` defaults** | Typical for a public gallery |

## Version notes

- Moved to `v7.12.1` on 2026-11-05, not run on a host at this tag. No breaking change
  and no manual step in the notes. The standard image moves to FrankenPHP 1.13.3
  and builds its own ImageMagick 7.1.2 with JPEG XL support, and turns off PHP's `session.upload_progress`; entrypoint,
  `PUID`/`PGID`, the volume paths and the healthcheck on `:2019/metrics` are
  unchanged. The move from debian-slim to a PHP base image in v7.12.0 (#4915)
  concerns only the `-legacy` image. Upstream's `.env.example` renames
  `CACHE_DRIVER` to `CACHE_STORE`; `CACHE_DRIVER`, which this stack sets, is still
  read while `CACHE_STORE` is unset. v7.12.0 adds email login. Security fixes:
  CVE-2026-109618 and CVE-2026-109619 (PHP, in the Docker image, v7.12.0), a sprintf
  vulnerability (v7.11.0), complete stripping against XSS and blocking of
  IPv6-transition spellings of internal IPv4 addresses (v7.10.0), dependency CVEs
  (v7.8.4).
- Moved `mariadb` from `11.4` to `12.3`, the current LTS line, on 2026-11-05,
  not run on a host at this tag. Support: Lychee requires "MariaDB (version >
  10.2)" with no upper bound
  (https://lycheeorg.dev/docs/getting-started/manual-installation/); upstream's
  compose uses `mariadb:11`. `MARIADB_AUTO_UPGRADE: "1"`, already set in both
  compose files, runs `mariadb-upgrade` at the first start on 12.3 after a
  backup of the system tables; the data directory `./volumes/mysql` is reused.
  Take the `mariadb-dump` before the tag changes: going back to 11.4 is only a
  restore of that dump. Changed on the way (11.8 and 12.x):
  `innodb_snapshot_isolation` is on by default, so a transaction that writes a
  row another transaction changed after its snapshot fails with error 1020
  instead of overwriting it; the new default collation `utf8mb4_uca1400_ai_ci`
  does not apply, as the stack sets `utf8mb4_unicode_ci` explicitly.
- Moved `redis` from `7.4-alpine` to `8.10-alpine` on 2026-11-05, a new major, not
  run on a host at this tag; the tag follows the 8.10 patch releases (8.10.3,
  2026-10-26). Redis 8 is offered under RSALv2, SSPLv1 or AGPLv3 at the user's
  choice (7.4: RSALv2 or SSPLv1). The image bundles the Query Engine, JSON, time
  series and probabilistic data types as modules, which the image's entrypoint loads
  at start on amd64 and arm64; this stack uses none of them. 8.x reads the 7.4 data
  files in place, but Redis does not load files written by a newer version, so a
  rollback needs the backup of the Redis data. The one potentially breaking change
  upstream lists: `GETRANGE` with an out-of-range negative end returns an empty
  string. Security fixes in the 8.10 line: CVE-2026-62356 (8.10.1, heap write when
  loading a Count-min sketch from an RDB file), queued `MULTI` commands keeping
  access to keys whose ACL permission was revoked (8.10.2), and a cluster-bus
  overflow that needs cluster mode (8.10.3). The 7.4 line still receives fixes
  (7.4.12, 2026-10-26); the move is to the newest stable line, not away from an
  unmaintained one. No Redis version requirement was found for Lychee. The image's
  entrypoint now drops to the `redis` user only when SETUID and SETGID are in the
  capability bounding set, empties that set while dropping, and fixes ownership only
  of `*.rdb` files and `appendonlydir` in `/data`. This service starts as root with
  Docker's default capabilities, so it drops to UID 999 as before; no compose
  change. Sources: https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh

## Upgrade checklist

1. Check [Lychee releases](https://github.com/LycheeOrg/Lychee/releases)
2. Back up:

   ```bash
   # DB dump
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" lychee' \
     > lychee-db-$(date +%Y%m%d).sql
   # Uploads + conf
   tar czf lychee-data-$(date +%Y%m%d).tgz volumes/uploads/ volumes/conf/
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch logs for Laravel migrations:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, browse an album, upload a new photo

### Rollback

Restore DB dump and `volumes/uploads/`, revert `APP_TAG`.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Run artisan commands
docker compose exec app php artisan <command>

# Regenerate thumbnails
docker compose exec app php artisan lychee:regenerate-thumbs

# Rotate APP_KEY (invalidates all sessions)
docker compose exec app php artisan key:generate --show

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" lychee' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" lychee'
```
