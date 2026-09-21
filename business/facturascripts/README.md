# FacturaScripts

Invoicing, accounting and inventory for small businesses, extended through
plugins. PHP on Apache, with MariaDB. Upstream:
[FacturaScripts](https://github.com/NeoRazorX/facturascripts).

## Updates run inside the application — read this first

FacturaScripts updates itself: **Admin → Updater** downloads a new version and
writes it into the webroot. The image copies the code into the webroot on the
first start only, and upstream's Docker page states that a newer image leaves a
running install unchanged. This stack keeps that model:

- `APP_TAG` sets PHP, Apache and the operating system, and the version the
  first install starts from. Raising it does not change the installed
  FacturaScripts version.
- The installed version lives in `volumes/facturascripts`, so the backup
  includes the whole webroot.
- Image scans cover PHP, Apache and the operating system, not the code in the
  webroot.

## Architecture

```text
Internet → Traefik (TLS) → facturascripts-app :80 (Apache, mod_php)
                                  │
                     app-internal (internal: true)
                        │                    │
               db (MariaDB 11.4)    facturascripts-cron ── app-egress
```

## Setup

```bash
cp .env.example .env            # host name, language
ops/init.sh                     # secrets and the mounted paths
sudo chown -R 33:33 volumes/facturascripts
docker compose up -d
ops/install.sh admin
```

`ops/install.sh` runs upstream's own installer in its unattended mode instead of
the web wizard. It reads both passwords from the Docker Secrets inside the
container, so they never pass through your shell, and afterwards takes both back
out of `config.php`. A second run reports that the instance is installed and
changes nothing.

Log in as `admin` with the password in `.secrets/admin_pwd.txt`. The first login
opens FacturaScripts' wizard — company, country, taxes — which is ordinary first
use.

## The open window, and why the router starts closed

Before `ops/install.sh` has run, the web installer is reachable and accepts
whatever database it is given. `.env.example` therefore ships
`APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only. The installer closes once
`config.php` exists.

## What is mounted

| Path | Holds |
|---|---|
| `volumes/facturascripts` → `/var/www/html` | The installed code, `config.php`, `MyFiles/` (uploads, cache), `Plugins/`, `Dinamic/` (generated) |
| `volumes/mysql` | The database |

Both services from the image mount the webroot: the application and
`facturascripts-cron`, which runs `php index.php -cron` every five minutes as
uid 33.

## Security notes

- **Database password.** The installer writes it into `config.php`;
  `ops/install.sh` replaces that line with a read of the Docker Secret.
- **The database password opens every account.** The login page's password reset
  accepts it to set a new password for any enabled user, and switches off that
  user's two-factor login. Treat it as an administrator credential; `ops/init.sh`
  generates 48 hex characters.
- **Administrator password.** The installer writes it into `config.php`, where it
  is read once to create the account; `ops/install.sh` deletes the line
  afterwards. The account stores a bcrypt hash.
- **`/cron` is refused.** It runs every scheduled job for any caller, without a
  login. `config/apache/cron.conf` denies it; the cron service runs the same jobs
  from the command line.
- **Plugins are code.** Administrators can upload plugins through the web
  interface. `FS_DISABLE_ADD_PLUGINS` in `config.php` switches that off.
- **Replaced start script.** The image's own runs `chmod -R o+w` over the webroot.
  `config/entrypoint.sh` copies the code as `www-data` on the first start and
  leaves nothing world-writable.
- **Hardening.** `read_only`, `cap_drop: ALL`, `no-new-privileges`, no published
  port. The application adds back `SETUID` and `SETGID`, because Apache starts as
  root and hands its workers to `www-data` — see UPSTREAM.md for the measurement.
  The cron service runs as uid 33 with no capabilities.
- **Network.** The database has no route out; the cron service reaches outward
  for plugin jobs that call external services.

## What it sends outward

- **Update check.** The administrator's dashboard fetches the list of builds from
  `facturascripts.com`.
- **Telemetry, once registered.** Nothing is sent until an administrator
  registers the installation in the updater. After that, weekly: country code,
  version, installation ID, language, PHP version, database engine, the enabled
  plugins and their fingerprints.
- **The installer's "send anonymous data" option** adds Google Tag Manager to the
  interface's pages. It is off in the web installer unless ticked, and
  `ops/install.sh` does not set it.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
sudo chown -R 33:33 volumes/facturascripts
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — the web installer: database host db, name and user
# from .env.local, password from .secrets/db_pwd.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/facturascripts` and `.secrets/`:

```bash
docker exec facturascripts-db sh -c 'mariadb-dump -u"$MYSQL_USER" -p"$(cat /run/secrets/DB_PWD)" "$MYSQL_DATABASE"' > facturascripts.sql
sudo tar -czf facturascripts-files.tar.gz volumes/facturascripts .secrets
```

The webroot is the installed version, so restore the database and the webroot
from the same point in time. Restore into an empty database with `mariadb`,
unpack the archive, restore the `33:33` ownership on `volumes/facturascripts`,
and run `docker compose up -d`. Restore is not exercised here.
