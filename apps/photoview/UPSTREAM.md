# Upstream Reference

## Source

- **Photoview project:** https://photoview.github.io/
- **GitHub:** https://github.com/photoview/photoview
- **Docker Hub:** https://hub.docker.com/r/photoview/photoview
- **License:** GPL-3.0
- **Origin:** Denmark · community · EU
- **Based on version:** `2` (tracks 2.x line)
- **Last checked:** 2026-04-17

## What we use

- Upstream `photoview/photoview:2`
- Official `mariadb:lts`
- Docker Secrets for MariaDB password + root password
- Bind-mount `./volumes/media-cache`, `./volumes/mariadb`
- Configurable `MEDIA_ROOT` (read-only bind into `/photos`)

## What we changed and why

| Change | Reason |
|--------|--------|
| **Default DB passwords replaced** — inbox had `MARIADB_PASSWORD=photosecret`, `MARIADB_ROOT_PASSWORD=superphotosecret` | Now Docker Secrets (`.secrets/db_pwd.txt`, `.secrets/db_root_pwd.txt`) + `DB_PWD_INLINE` duplicate for Photoview |
| **Traefik labels instead of `ports: 8025:80`** | Blueprint routes via Traefik |
| **`photoview-prepare` init service dropped** | Ran `chown` on the media-cache folder once. Simpler: `chown` in setup step 4 |
| **Watchtower service dropped** | Blueprint policy: explicit `APP_TAG` bumps, no auto-updates |
| **`security_opt: seccomp:unconfined + apparmor:unconfined` on app** → `no-new-privileges:true` | Upstream unconfined profile targets an old MariaDB issue, not Photoview. Kept as commented fallback on DB service |
| **`cap_drop: ALL` + minimal `cap_add` on MariaDB** | Baseline hardening |
| **`app-internal` network (`internal: true`)** | Isolate DB from host |
| **`/etc/localtime` bind mount removed** | Replaced with explicit `TZ` env var (blueprint convention) |
| **SQLite + PostgreSQL drivers dropped** | Upstream supported three backends via commented service blocks. Only MySQL/MariaDB is wired up here for simplicity |
| **Container / hostnames standardized** | `photoview-app / photoview-db` instead of bare `photoview / photoview-mariadb` |
| **DSN-safe password requirement documented** | Photoview's `PHOTOVIEW_MYSQL_URL` parses special characters (`@`, `:`, `/`, `?`, `#`). Inbox called this out in a comment; setup script now uses `openssl rand -hex` which is safe |
| **`HOST_PHOTOVIEW_LOCATION` / `HOST_PHOTOVIEW_MEDIA_ROOT` / `HOST_PHOTOVIEW_BACKUP` renamed** to `MEDIA_ROOT` and `./volumes/` bind paths | Blueprint convention + drops unused backup variable |
| **Access `acc-public` + security `sec-2` defaults** | Typical for public galleries |

## Upgrade checklist

1. Check [Photoview releases](https://github.com/photoview/photoview/releases)
2. Back up:
   ```bash
   # DB dump
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoview' \
     > photoview-db-$(date +%Y%m%d).sql
   # Media cache (thumbnails)
   tar czf photoview-cache-$(date +%Y%m%d).tgz volumes/media-cache/
   ```
3. Bump `APP_TAG` in `.env` (pin to a dated tag for reproducibility)
4. `docker compose pull && docker compose up -d`
5. Watch logs:
   ```bash
   docker compose logs --follow
   ```
6. Verify: log in, browse albums, trigger a rescan

### Rollback

Restore DB dump. Media cache can be rebuilt; no need to restore.

## Useful commands

```bash
# Shell into the app
docker compose exec app sh

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoview' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoview'

# Force full rescan (via UI: Settings → Scan all users, or via API)
```

## Not imported from inbox

- **`postgres` + `postgres-autoupgrade` service blocks** — upstream supports PostgreSQL as an alternative backend. Re-add from the upstream compose if preferred.
- **`sqlite` driver** — available upstream; requires a persistent `/home/photoview/database` volume.
- **Multi-folder media mounts** — upstream example showed how to mount several media roots under `/photos/Family`, `/photos/Archive`, etc. Add additional `${VAR}:/photos/Name:ro` lines as needed.
