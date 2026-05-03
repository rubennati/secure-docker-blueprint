# Upstream Reference

## Source

- **Dolibarr project:** https://www.dolibarr.org/
- **GitHub:** https://github.com/Dolibarr/dolibarr
- **Docker image:** https://hub.docker.com/r/tuxgasy/dolibarr (community-maintained, widely used)
- **License:** GPL-3.0
- **Origin:** France · Dolibarr Association · EU
- **Based on version:** `latest` (tracks Dolibarr's stable line)
- **Last checked:** 2026-04-17

## What we use

- Community `tuxgasy/dolibarr`
- Official `mariadb:11.4`
- Docker Secrets for every credential (DB user, DB root, admin login, admin password)
- Bind-mount `./volumes/mysql`, `./volumes/documents`, `./volumes/custom`

## What we changed and why

| Change | Reason |
|--------|--------|
| **Hardcoded non-UTC timezone replaced with `${TZ}`** | Prevent leaking author's timezone; `TZ` defaults to `UTC` |
| **Hardcoded country-code TLD in example domain replaced with `example.com`** | Prevent leaking a regional TLD that correlates with the author |
| **`image: tuxgasy/dolibarr` → `tuxgasy/dolibarr:${APP_TAG}`** | Pinned tag (blueprint convention) |
| **Traefik labels added** — inbox had a comment "Traefik-Labels hier ergaenzen fuer HTTPS" but no labels | Blueprint routes via Traefik |
| **`DB_TAG` variable added** | Blueprint pinning convention |
| **Service names standardized** — inbox used `database` + `web`, kept container names `dolibarr-db/app` | Now `db` + `app` as services (blueprint convention), container names derived from `CONTAINER_NAME_*` |
| **`app-internal` network naming** — inbox used `dolibarr_isolated` | Now `${COMPOSE_PROJECT_NAME}-internal` (auto-derived) |
| **External network `traefik` → `proxy-public`** | Blueprint standard name |
| **`security_opt: no-new-privileges` + `cap_drop: ALL` + minimal `cap_add`** on MariaDB | Baseline hardening |
| **Healthcheck added on MariaDB + `depends_on.condition: service_healthy`** | Prevents Dolibarr from trying to install before DB is ready |
| **`TZ` env var on both services** | Replaces a hardcoded non-UTC `PHP_INI_DATE_TIMEZONE` |
| **Access `acc-tailscale` + security `sec-3` defaults** | ERP = business data; VPN-only is safer than public |

## Upgrade checklist

1. Check [Dolibarr changelog](https://wiki.dolibarr.org/index.php/Releases) — especially point 3 of each major release for schema migrations
2. Back up:
   ```bash
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" dolibarr' \
     > dolibarr-db-$(date +%Y%m%d).sql
   tar czf dolibarr-data-$(date +%Y%m%d).tgz volumes/documents/ volumes/custom/
   ```
3. Bump `APP_TAG` in `.env` (pin to a specific Dolibarr version)
4. `docker compose pull && docker compose up -d`
5. Open the UI — Dolibarr detects the new version and redirects to the migration wizard
6. Step through the wizard; watch for plugin-specific warnings
7. Verify: log in, open a customer, open an invoice, confirm PDF templates render

### Rollback

Restore DB dump and `volumes/documents/`, revert `APP_TAG`. Schema downgrades are not supported — the SQL dump is the only path back.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# Dolibarr CLI is at /var/www/html/scripts/
docker compose exec app php /var/www/html/scripts/cron/cron_run_jobs.php

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" dolibarr' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" dolibarr'
```
