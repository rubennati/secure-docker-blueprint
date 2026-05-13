# Matomo

**Status: ✅ Ready — v5.10.0 · 2026-05-11**

Self-hosted web analytics platform — privacy-respecting, GDPR-compatible alternative to Google Analytics. Two-service stack: PHP/Apache app + MariaDB.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `matomo:5-apache` (5.10.0) | Tracking endpoint + reporting UI |
| `db` | `mariadb:11.4` | Raw visits, aggregated reports, users, settings |

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
docker compose logs app --follow
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

- **Setup wizard is the first-run gate** — run it yourself immediately after `docker compose up`. An attacker that opens the URL before you can claim the super-user account.
- **`MATOMO_DATABASE_PASSWORD_FILE` is supported natively** — Matomo reads the password from `/run/secrets/DB_PWD` directly. No inline duplication needed.
- **`MYSQL_PASSWORD_FILE` + `MYSQL_ROOT_PASSWORD_FILE`** — MariaDB also reads secrets from files.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **`X-Forwarded-Proto=https`** header injected by Traefik middleware so Matomo generates `https://` tracking URLs (avoids Mixed Content on tracked pages).
- **Default access `acc-public` + `sec-3`** — tracking endpoint must be reachable from every page you track, but the admin UI benefits from the stricter header policy.

## Known Issues

- **Console warnings during installation wizard** — the Congratulations step shows a CSP `unsafe-eval` report-only violation (report-only, no action needed), a `Mousetrap is not defined` JS error, and `.map` file 403s from Apache. All cosmetic; they disappear after installation completes.
- **"Add User" page shows Oops error** — Matomo fires `UsersManager.getSitesAccessForUser` with an empty `userLogin=` when you open the Add User form, which returns a 400 and triggers the red error banner. Known UI bug; dismiss and fill in the form normally — saving works fine.
- **Database table prefix** — change `DB_TABLES_PREFIX=mtm_` before the first setup. The default `matomo_` collides with other Matomo installs sharing a DB, and can be scanned for.
- **Archive cron** — by default, Matomo archives reports on-demand when a report is viewed. For high-traffic sites, add a cron container running `php /var/www/html/console core:archive` every hour. Not configured here.
- **GeoIP database not shipped** — download MaxMind's `GeoLite2-City.mmdb` manually and place in `volumes/matomo/misc/` for location reports.
- **`APP_TAG=5-apache` pins major version 5** — patch updates come in on rebuild. Pin to a specific version for stricter reproducibility.

## Details

- [UPSTREAM.md](UPSTREAM.md)
