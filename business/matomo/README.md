# Matomo

Self-hosted web analytics platform — privacy-respecting, GDPR-compatible alternative to Google Analytics. Two-service stack: PHP/Apache app + MariaDB.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `matomo-app` | `matomo:5.14.2-apache` | Tracking endpoint + reporting UI |
| `db` | `mariadb:12.3.3` | Raw visits, aggregated reports, users, settings |

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local # fill the __REPLACE_ME__ values
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 3. Create volumes
mkdir -p volumes/mysql volumes/config volumes/logs volumes/matomo

# 4. Start
docker compose up -d
docker compose logs matomo-app --follow
# Watch for: "apache2 -D FOREGROUND"

# 5. Open UI and run the 8-step installation wizard
# https://<APP_TRAEFIK_HOST>
# - System Check: all mandatory checks should pass
# - Database: host=db, port=3306, user+name+prefix from .env, password from .secrets/db_pwd.txt
# - Super user: pick any username and a strong password
# - Add your first website

# 6. Verify config.ini.php was written
ls -la volumes/config/
# Should show config.ini.php — Matomo writes here during setup
```

## Verify

```bash
docker compose ps                              # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **Setup wizard is the first-run gate** — whoever completes it owns the super-user account, which is why the route ships at `access-vpn`: run it over the VPN, then open it.
- **`MATOMO_DATABASE_PASSWORD_FILE` is supported natively** — Matomo reads the password from `/run/secrets/DB_PWD` directly. No inline duplication needed.
- **`MYSQL_PASSWORD_FILE` + `MYSQL_ROOT_PASSWORD_FILE`** — MariaDB also reads secrets from files.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **`X-Forwarded-Proto=https`** header injected by Traefik middleware so Matomo generates `https://` tracking URLs (avoids Mixed Content on tracked pages).
- **Shipped access `access-vpn`, `access-public` once the wizard has run, with `limit-standard` and `headers-application-owned`** — the tracking endpoint must be reachable from every page you track.
- **The proxy sends no `X-Frame-Options`; Matomo sets it itself.** `headers-application-owned` sets the HSTS base only, and the compose file places `header-nosniff@file` and `header-permissions@file` before it for the two headers Matomo lacks. Matomo varies the frame header per endpoint — `deny` on the reporting UI, absent on the [Widgetize](https://matomo.org/guide/reporting-tools/embedding-matomo/) endpoints, which exist to be embedded in another page. A header from the proxy would reach the widget responses as a second, conflicting value, and the embedded reports would stop loading.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `matomo-db` · database `matomo` · user `matomo` · table prefix `mtm_` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/mysql` (database) · `./volumes/config` (`config.ini.php`, holds the salt) |
| **Reproducible** | `./volumes/logs` · `./volumes/matomo` — the application directory, restored from the image |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
mariadb_databases:
    - name: matomo
      container: matomo-db
      username: matomo
      password: "{credential file /srv/docker/business/matomo/.secrets/db_pwd.txt}"
```

**`config/config.ini.php` carries the instance salt.** Restoring the database
against a freshly generated config invalidates existing sessions and API tokens,
and any value derived from that salt. It is one small file — back it up.

The database grows with traffic. Check the archive size against the retention
policy before assuming the defaults in `backup/borgmatic/` fit this stack.

**Restore order:** database first, then the app.

## Known Issues

- **Console warnings during installation wizard** — the Congratulations step shows a CSP `unsafe-eval` report-only violation (report-only, no action needed), a `Mousetrap is not defined` JS error, and `.map` file 403s from Apache. All cosmetic; they disappear after installation completes.
- **"Add User" page shows Oops error** — Matomo fires `UsersManager.getSitesAccessForUser` with an empty `userLogin=` when you open the Add User form, which returns a 400 and triggers the red error banner. Known UI bug; dismiss and fill in the form normally — saving works fine.
- **Database table prefix** — change `DB_TABLES_PREFIX=mtm_` before the first setup. The default `matomo_` collides with other Matomo installs sharing a DB, and can be scanned for.
- **Archive cron** — by default, Matomo archives reports on-demand when a report is viewed. For high-traffic sites, add a cron container running `php /var/www/html/console core:archive` every hour. Not configured here.
- **GeoIP database not shipped** — download MaxMind's `GeoLite2-City.mmdb` manually and place in `volumes/matomo/misc/` for location reports.
- **`APP_TAG` is an exact version (`5.14.2-apache`)** — a new Matomo release arrives only when the pin moves. On an existing install a new tag alone updates PHP and the OS, not Matomo: `./volumes/matomo` holds the application files, and the image copies its own only into an empty directory. The upgrade checklist in [UPSTREAM.md](UPSTREAM.md) has the step that moves the code.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `5.14.2-apache` — the newest upstream release. Scanned 2026-11-08; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `mariadb:12.3.3` | 0 · 1 | — | 1 · 25 |
| `matomo:5.14.2-apache` | 0 · 2 | — | — |

<!-- findings:end -->

The MariaDB image, `mariadb`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.

## Details

- [UPSTREAM.md](UPSTREAM.md)
