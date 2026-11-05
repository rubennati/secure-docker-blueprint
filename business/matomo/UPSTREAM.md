# Upstream Reference

## Source

- **Matomo project:** https://matomo.org/
- **GitHub:** https://github.com/matomo-org/matomo
- **Docker Hub:** https://hub.docker.com/_/matomo (official image)
- **License:** GPL-3.0
- **Edition gating:** SAML single sign-on is the separate LoginSaml plugin, sold under the InnoCraft EULA rather than shipped under the GPL core — https://plugins.matomo.org/LoginSaml · checked 2026-09-21
- **Commercial model:** paid add-on; the self-hosted core itself is free — https://plugins.matomo.org/LoginSaml · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** New Zealand · InnoCraft Ltd · non-EU
- **Domain:** Business operations
- **Role:** Web analytics under your control
- **Based on version:** `5.14.2-apache`
- **Last checked:** 2026-04-17

## What we use

- Official `matomo:5.14.2-apache` (Apache + PHP; the floating `5-apache` tag was replaced by the exact pin in 2026-07)
- Official `mariadb:11.4`
- Docker Secrets for DB password + DB root password
- Bind-mount `./volumes/config`, `./volumes/logs`, `./volumes/matomo`, `./volumes/mysql`

## What we changed and why

| Change | Reason |
|--------|--------|
| **Author slug removed from network names** — inbox embedded a personal identifier in the internal and external network names | Leaked the author's identifier. Now `${COMPOSE_PROJECT_NAME}-internal` (auto-derived) and standard `proxy-public` |
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
| **Access `access-public`; `limit-standard`; `headers-application-owned` with `header-nosniff` and `header-permissions` before it** | Tracking pixel must be reachable by any browser that visits your sites, so public access is required; Matomo sends its own frame and referrer headers, which the proxy leaves alone, and the two blocks add what it lacks |

## Version notes

- Moved to `5.14.2-apache` on 2026-11-05, not run on a host at this tag. 5.14.0,
  5.14.1 and 5.14.2 each state that they contain no major database upgrade; the
  image repository changed only `MATOMO_VERSION`. 5.14.0 adds aggregated real-time
  counters for when the Visits Log is disabled and a refreshed login page; 5.14.1
  fixes a race condition in nonce validation (#25300) and redesigns the Marketplace;
  5.14.2 updates `composer/ca-bundle` to 1.6.0 (#25563) and warns on PHP versions
  affected by CVE-2026-109618 and CVE-2026-109619, which the rebuilt image's PHP
  carries the fix for — updating Matomo alone does not. On an existing install the
  tag bump moves PHP and the OS but not Matomo's own code until checklist step 4 is
  run; this applied to every earlier bump of this stack as well.

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
4. Pull, then let the new image replace the application files and start it.
   `./volumes/matomo` is `/var/www/html`, and the image's entrypoint copies its
   Matomo into it only when `matomo.php` is missing — without removing it an
   existing install keeps its old Matomo code and only PHP and the OS move.
   `matomo.php` is also the tracking endpoint, so remove it right before the start:

   ```bash
   docker compose pull
   rm volumes/matomo/matomo.php
   docker compose up -d
   ```

5. The entrypoint unpacks the image's files over the directory. It overwrites, it
   does not delete: `config/`, marketplace plugins and `misc/` stay, and files the
   new release dropped stay behind — the system check lists them.
6. Run the database upgrade, from the console or by visiting the UI, which
   prompts for it:

   ```bash
   docker compose exec -u www-data matomo-app php /var/www/html/console core:update --yes
   ```

7. Verify: open a tracked site's report, confirm data is still present, and check
   Administration → System → System check for the version and leftover files

### Rollback

Restore the DB dump, `volumes/config/` and `volumes/matomo/` (both in the step 2 archive), revert `APP_TAG`.

## Useful commands

```bash
# Shell into the app
docker compose exec matomo-app bash

# Matomo console
docker compose exec matomo-app php /var/www/html/console <command>

# Force-archive reports (useful as a cron)
docker compose exec matomo-app php /var/www/html/console core:archive

# List users
docker compose exec matomo-app php /var/www/html/console user:list

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
