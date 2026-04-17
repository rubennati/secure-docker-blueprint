# Upstream Reference

## Source

- **Matomo project:** https://matomo.org/
- **GitHub:** https://github.com/matomo-org/matomo
- **Docker Hub:** https://hub.docker.com/_/matomo (official image)
- **License:** GPL-3.0
- **Based on version:** `5-apache`
- **Last checked:** 2026-04-17

## What we use

- Official `matomo:5-apache` (Apache + PHP)
- Official `mariadb:11.4`
- Docker Secrets for DB password + DB root password
- Bind-mount `./volumes/config`, `./volumes/logs`, `./volumes/matomo`, `./volumes/mysql`

## What we changed and why

| Change | Reason |
|--------|--------|
| **Author slug removed from network names** — inbox used `intern-matomornati` and `npm-matomornati` | Leaked the author's identifier. Now `${COMPOSE_PROJECT_NAME}-internal` (auto-derived) and standard `proxy-public` |
| **`image: matomo` → `matomo:${APP_TAG}`** | Pinned tag (blueprint convention) |
| **Traefik labels added** — inbox had `#ports: 8080:80` commented + no Traefik labels | Blueprint routes via Traefik; proxy-headers middleware added for https URL generation |
| **`MATOMO_DATABASE_PASSWORD_FILE` added** | Matomo supports `_FILE` suffix since 4.x — no need for `DB_PWD_INLINE` duplication |
| **Named volume `db: name: ${VOLUME_NAME_DB}` → bind mount `./volumes/mysql`** | Blueprint uses bind mounts for predictable backup paths |
| **SELinux `:Z` / `:z` mount labels dropped** | Not relevant on Debian-based hosts; re-add if deploying on SELinux-enforced RHEL/Fedora |
| **`MARIADB_DISABLE_UPGRADE_BACKUP: 1` kept** | Inbox had it; skips the automatic backup dump during major-version upgrades (saves disk during upgrade) |
| **`MARIADB_INITDB_SKIP_TZINFO: 1` moved from .env → compose** (not set) | Current MariaDB images no longer need this flag for reasonable start times |
| **`app-internal` network (`internal: true`)** | Isolate DB from host |
| **`cap_drop: ALL` + minimal `cap_add` on MariaDB** + `no-new-privileges` on both services | Baseline hardening |
| **`TZ` env var added** on both services | Blueprint convention; inbox relied on UTC |
| **Access `acc-public` + security `sec-3` defaults** | Tracking pixel must be reachable by any browser that visits your sites, so public access is required; `sec-3` adds strict headers for the admin UI |

## Upgrade checklist

Matomo's major-version bumps usually include DB schema changes that the web UI performs on first visit.

1. Check [Matomo release notes](https://matomo.org/changelog/) — note any plugin breakage
2. Back up:
   ```bash
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" matomo' \
     > matomo-db-$(date +%Y%m%d).sql
   tar czf matomo-config-$(date +%Y%m%d).tgz volumes/config/ volumes/matomo/
   ```
3. Bump `APP_TAG` and/or `DB_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Visit the UI — Matomo prompts to run DB upgrades, click through
6. Verify: open a tracked site's report, confirm data is still present

### Rollback

Restore DB dump and `volumes/config/`, revert `APP_TAG`.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Matomo console
docker compose exec app php /var/www/html/console <command>

# Force-archive reports (useful as a cron)
docker compose exec app php /var/www/html/console core:archive

# List users
docker compose exec app php /var/www/html/console user:list

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" matomo' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" matomo'
```

## Recommended follow-up

- Schedule hourly `core:archive` via a cron container or host cron (docs: https://matomo.org/docs/setup-auto-archiving/)
- Download MaxMind GeoLite2-City.mmdb for location reports
- Enable `[Tracker] force_ssl = 1` in `config/config.ini.php` to reject non-HTTPS tracking requests
