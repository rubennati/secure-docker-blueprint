# Upstream Reference

## Source

- **Dolibarr project:** https://www.dolibarr.org/
- **GitHub:** https://github.com/Dolibarr/dolibarr
- **Docker image:** https://hub.docker.com/r/tuxgasy/dolibarr (community-maintained, widely used)
- **License:** GPL-3.0
- **Decision facts checked:** not yet
- **Origin:** France · Dolibarr Association · EU
- **Domain:** Business operations
- **Role:** ERP and CRM: contacts, quotes, invoices, stock and accounting
- **Last verified:** 2026-11-08 (24.0.2) — over IPv4, at the closed default: the first-run install with the administrator from the secret files, a login landing on the setup completion page before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Community `tuxgasy/dolibarr`
- Official `mariadb:12.3.3`
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
| **Access `access-vpn` by default, with `limit-standard` and `headers-standard`** | ERP = business data; VPN-only is safer than public |

## Version / tag notes

- **Stayed on the 23.x line: `23.0.3` → `23.0.4`.** Dolibarr 24 is out and `24.0.0` is
  published, but a Dolibarr major is a database migration rather than a tag change.
  `23.0.4` is the newest 23.x image (2026-08-29). CVE-2026-23500 (critical, OS command
  injection via `MAIN_ODT_AS_PDF`) is fixed on this line. Moved on 2026-09-13; schedule 24.x as
  its own piece of work.
- Moved `mariadb` from `11.4` to `12.3.3`, the current LTS line, on 2026-11-05. Support: Dolibarr requires MariaDB 10.3 or
  newer with no upper bound
  (https://wiki.dolibarr.org/index.php?title=Prerequisites).
  `MARIADB_AUTO_UPGRADE: "1"`, already set in both compose files, runs
  `mariadb-upgrade` at the first start on 12.3 after a backup of the system
  tables; the data directory `./volumes/mysql` is reused. Take the
  `mariadb-dump` before the tag changes: going back to 11.4 is only a restore of
  that dump. Changed on the way (11.8 and 12.x): `innodb_snapshot_isolation` is
  on by default, so a transaction that writes a row another transaction changed
  after its snapshot fails with error 1020 instead of overwriting it; the new
  default collation `utf8mb4_uca1400_ai_ci` does not apply, as the stack sets
  `utf8mb4_unicode_ci` explicitly.
- Moved to `24.0.2` on 2026-11-05 (image published 2026-10-31), the major the
  note above deferred. Dolibarr 24 is a schema
  migration: per the image README
  (https://github.com/Dolibarr/dolibarr-docker), remove
  `volumes/documents/install.lock`, then pull and start; with
  `DOLI_INSTALL_AUTO` at its image default `1` (not set here) the entrypoint
  migrates the database, otherwise the `/install/` wizard does. Take the
  `mariadb-dump` and the `volumes/documents/` archive first: a schema downgrade
  is not supported, so going back to 23.0.4 is a restore. The unsuffixed
  `24.0.2` tag is published together with `24.0.2-php8.5`, so PHP moves from
  the 8.4 of `23.0.4` to 8.5. Changes in 24.0.0 that may break setups
  (https://github.com/Dolibarr/dolibarr/blob/24.0.2/ChangeLog): the login API
  is off unless `API_ENABLE_LOGIN_API` is enabled; online-signature secure keys
  use a default salt, so links issued without one stop working; the
  `PAYMENT_SECURITY_TOKEN_UNIQUE` option and the Paybox and Deplacement modules
  are removed; `DEPOSIT_AS_CREDIT_AVAILABLE_EVEN_UNPAID` is renamed; contact
  titles need `MAIN_USE_TITLE_FOR_CONTACT`; filter parameters of functions
  require Universal Search Syntax and the `info_admin` hook is renamed, which
  matters for modules in `volumes/custom/`. Advisories: 24.0.1 enforces website
  write rights in the legacy file manager and stops non-admins deleting admin
  accounts; 24.0.2 fixes authorisation bypasses (leave API, project and task
  comments, salary documents, supplier-invoice and VAT payment pages,
  `core/ajax/mailtemplate.php`, ownership checks in several API endpoints) and
  an SSRF through DNS rebinding in the external-calendar import. No CVE IDs
  are given. Compose and `DOLI_*` variables are unchanged.

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
