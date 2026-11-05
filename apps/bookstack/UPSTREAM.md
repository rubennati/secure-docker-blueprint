# Upstream Reference

## Source

- **BookStack project:** https://www.bookstackapp.com/
- **GitHub (BookStack):** https://github.com/BookStackApp/BookStack
- **LSIO image:** https://docs.linuxserver.io/images/docker-bookstack/
- **LSIO GitHub:** https://github.com/linuxserver/docker-bookstack
- **License:** MIT (BookStack) / GPL-3 (LSIO scripts)
- **Decision facts checked:** not yet
- **Origin:** UK · Dan Brown (BookStack) · non-EU
- **Domain:** Files, wiki and collaboration
- **Role:** Wiki with structure: shelves, books, chapters and pages
- **Based on version:** `version-v26.09.2` (= BookStack 26.09.2), digest-pinned
- **Last verified:** 2026-05-03 (v25.02)

## What we use

- LSIO image for BookStack (Apache + PHP 8 pre-configured)
- Official `mariadb:12.3.3` as backend (consistent with rest of blueprint)
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
| **Access `access-public`, `limit-standard` and `headers-standard` defaults** | Wikis are usually meant to be readable; fine-tune based on whether you want public read or team-only |

## Version notes

- Moved from `version-v26.05.4` to `version-v26.09.2` on 2026-11-05, not run
  on a host at this tag. `APP_TAG` now carries the digest
  `sha256:33f61a72d9aaa021f7e687987b9fcb992673d9ca3fc08f63f5ddaddf59e94efc`,
  so a re-pushed LSIO tag cannot change the image. Upgrade notice from v26.09:
  `APP_KEY` is now required, BookStack no longer falls back to a built-in key
  and shows an error instead; this stack already requires it. Also from v26.09:
  changing a password asks for the current one. v26.09.1 and v26.09.2 are
  security fixes: ZIP import checks the total uncompressed size, comments on
  pages in the recycle bin no longer show through the API, attachments on draft
  pages are no longer open to every user with attachment permissions, a
  password change drops remember-me cookies, and SAML2 routes refuse
  cross-site logout requests. Laravel migrations run on start; take the
  backup from the checklist first. Sources:
  https://github.com/BookStackApp/BookStack/releases and
  https://www.bookstackapp.com/blog/bookstack-release-v26-09/
- Moved `mariadb` from `11.4` to `12.3`, the current LTS line, on 2026-11-05,
  not run on a host at this tag. Support: BookStack requires "MySQL >= 8.0 or
  MariaDB >= 10.6" with no upper bound
  (https://www.bookstackapp.com/docs/admin/installation/).
  `MARIADB_AUTO_UPGRADE: "1"`, already set in both compose files, runs
  `mariadb-upgrade` at the first start on 12.3 after a backup of the system
  tables; the data directory `./volumes/mysql` is reused. Take the
  `mariadb-dump` before the tag changes: going back to 11.4 is only a restore of
  that dump. Changed on the way (11.8 and 12.x): `innodb_snapshot_isolation` is
  on by default, so a transaction that writes a row another transaction changed
  after its snapshot fails with error 1020 instead of overwriting it; the new
  default collation `utf8mb4_uca1400_ai_ci` does not apply, as the stack sets
  `utf8mb4_unicode_ci` explicitly.

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

3. Bump `APP_TAG` in `.env` and `.env.local.example` (keep the `version-v`
   prefix; pin the new digest with `@sha256:`)
4. `docker compose pull && docker compose up -d`
5. Watch logs for Laravel migration output:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, open an existing page, edit and save, upload image

### Rollback

Restore DB dump and `volumes/config/`, revert `APP_TAG`.

## Related images

- `mariadb` — safe to update within the 12.3 LTS line. Major upgrades need the standard MariaDB procedure.

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
