# Upstream Reference

## Source

- **Lychee project:** https://lycheeorg.dev/
- **GitHub:** https://github.com/LycheeOrg/Lychee
- **Docker repo:** https://github.com/LycheeOrg/Lychee-Docker
- **Docker Hub:** https://hub.docker.com/r/lycheeorg/lychee
- **License:** MIT
- **Based on version:** `v6`
- **Last checked:** 2026-04-17

## What we use

- `lycheeorg/lychee` as the Laravel app
- Official `mariadb:11.4` as backend
- Official `redis:7-alpine` for cache and sessions
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
| **Access `acc-public` + security `sec-2` defaults** | Typical for a public gallery |

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
