# Upstream Reference

## Source

- **BookStack project:** https://www.bookstackapp.com/
- **GitHub (BookStack):** https://github.com/BookStackApp/BookStack
- **LSIO image:** https://docs.linuxserver.io/images/docker-bookstack/
- **LSIO GitHub:** https://github.com/linuxserver/docker-bookstack
- **License:** MIT (BookStack) / GPL-3 (LSIO scripts)
- **Origin:** UK · Dan Brown (BookStack) · non-EU
- **Based on version:** `version-v25.02` (= BookStack 25.02)
- **Last verified:** 2026-05-03 (v25.02)

## What we use

- LSIO image for BookStack (Apache + PHP 8 pre-configured)
- Official `mariadb:11.4` as backend (consistent with rest of blueprint)
- Docker Secrets for DB password + DB root password
- Bind-mount `./volumes/config/` for LSIO `/config` (attachments, logs, PHP config, etc.)

## What we changed and why

| Change | Reason |
|--------|--------|
| **Real IP + real TZ removed** — inbox had a hardcoded RFC1918 address in `APP_URL` and a non-UTC timezone | Prevent leak; `APP_URL` now `https://${APP_TRAEFIK_HOST}`, `TZ` defaults to `UTC` |
| **Hardcoded passwords removed** — inbox source had placeholder DB user password and root password inline in the compose file | Now Docker Secrets (`.secrets/db_pwd.txt`, `.secrets/db_root_pwd.txt`) + `DB_PWD_INLINE` duplicate for BookStack |
| **Hardcoded `APP_KEY` removed** | Inbox example would have been a backdoor across copies. Now `__REPLACE_ME__` with generation command documented in Setup. |
| **MariaDB switched from LSIO to official** — inbox used `lscr.io/linuxserver/mariadb` | Blueprint consistency: other apps use `mariadb:<tag>`. BookStack app stays LSIO because that's the canonical deployment path. |
| **Traefik labels instead of port `:8011:80`** | Blueprint routes via Traefik |
| **`security_opt: no-new-privileges`** on both services | Baseline |
| **`cap_drop: ALL` + minimal `cap_add`** on MariaDB | Hardening consistent with Ghost, WordPress MariaDB services |
| **Access `acc-public` + security `sec-2` defaults** | Wikis are usually meant to be readable; fine-tune based on whether you want public read or team-only |

## Upgrade checklist

LSIO tags track BookStack semver as `version-vXX.XX`. Major bumps may require DB migrations.

1. Check BookStack [GitHub releases](https://github.com/BookStackApp/BookStack/releases) — breaking changes and required env-var updates
2. Back up:
   ```bash
   # DB dump
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" bookstack' \
     > bookstack-db-$(date +%Y%m%d).sql
   # Attachments / config
   tar czf bookstack-config-$(date +%Y%m%d).tgz volumes/config/
   ```
3. Bump `APP_TAG` in `.env` (keep `version-v` prefix)
4. `docker compose pull && docker compose up -d`
5. Watch logs for Laravel migration output:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, open an existing page, edit and save, upload image

### Rollback

Restore DB dump and `volumes/config/`, revert `APP_TAG`.

## Related images

- `mariadb` — safe to update within the 11.4 LTS line. Major upgrades need the standard MariaDB procedure.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Generate / rotate APP_KEY (inside container)
docker compose exec app php /app/www/artisan key:generate --show

# Run Laravel artisan commands
docker compose exec app php /app/www/artisan <command>

# Manual DB backup (mariadb-dump)
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" bookstack' > dump.sql

# Restore DB from dump
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" bookstack'

# Check Laravel queue / maintenance state
docker compose exec app php /app/www/artisan queue:work --once
```
