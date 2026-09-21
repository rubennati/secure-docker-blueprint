# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/facturascripts/facturascripts
- **Image source:** https://github.com/FacturaScripts/docker-facturascripts
- **GitHub:** https://github.com/NeoRazorX/facturascripts
- **Docs:** https://facturascripts.com/ayuda
- **License:** LGPL-3.0
- **Origin:** Spain · Carlos García Gómez (FacturaScripts) · EU
- **Commercial model:** paid add-on; the core is free, and some plugins are sold on facturascripts.com — https://facturascripts.com/plugins · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Domain:** Business operations
- **Role:** Invoicing, accounting and inventory for small businesses, extended through plugins
- **Based on version:** `2026.5`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

The origin comes from the terms on facturascripts.com, which name the site's owner
and apply Spanish law.

## What we use

- `facturascripts/facturascripts:2026.5` — the image publisher's stable channel;
  `latest` is the same image. `2026.65` is published as `beta`, although the
  GitHub release list does not mark it as a pre-release. PHP 8.4 and Apache on
  Debian 13.
- `mariadb:11.4` — the repository's MariaDB LTS. Upstream's compose uses
  `mysql:8.2`.
- **The image seeds the webroot; the in-app updater owns it afterwards.**
  Upstream's Docker page: updates run through Admin → Updater, and a new image
  does not update a running install, because the version that runs is the one in
  the volume — https://facturascripts.com/descargar/docker

## What we changed and why

| Change | Reason |
|--------|--------|
| The whole webroot as a bind mount, as upstream does | FacturaScripts writes its own updates, plugins and generated classes into the webroot. Mounting less would break the updater |
| `config/entrypoint.sh` replaces the image's start script | The original copies the code and then runs `chmod -R o+w` over the webroot. The replacement copies as `www-data`, once. The existence check runs as `www-data` too — measured: run as root without DAC capabilities, it cannot see into the mode-700 webroot and copied the image's code again on every start, which would undo an in-app update |
| `config/apache/cron.conf` denies `/cron` | Measured: an anonymous GET on `/cron` or `/Cron` ran the log clean-up, the receipt and invoice updates and the work queue. Both now answer 403 |
| `facturascripts-cron` service | Upstream's compose has none. It runs `php index.php -cron`, upstream's command-line entry point, every five minutes as uid 33. Page requests already run the work queue; the scheduled clean-up and plugin jobs need the cron. Its healthcheck only confirms the loop is running: the command exits 0 even with the database unreachable — measured |
| `cap_add: SETUID, SETGID` | Measured with Apache alone: with both, the master is uid 0 and its workers uid 33; with `SETUID` alone every Apache process stays root and `/` answers 403; with `SETGID` alone Apache exits. The entrypoint's `setpriv` needs both as well |
| tmpfs on `/tmp` and `/var/run/apache2` only | Apache exits on a read-only root without `/var/run/apache2` (its PID file) — measured. `/var/lock/apache2` is not needed. `/var/log/apache2` keeps the image's links to stdout and stderr, so the logs reach `docker logs` |
| `ops/install.sh` instead of the web wizard | Upstream's installer in its unattended mode (`unattended=1`), run as `www-data`, with both passwords read from the secrets inside the container. It sends `mysql_socket` empty, as the web form does: without the field the 2026.5 installer stops with a `TypeError` halfway through `config.php` — measured. Fix submitted upstream as [NeoRazorX/facturascripts#2041](https://github.com/NeoRazorX/facturascripts/pull/2041); the empty field can go once `APP_TAG` points to a release that contains it |
| `FS_DB_PASS` reads the Docker Secret | The installer writes the password into `config.php` in plain text; `ops/install.sh` replaces the line with `file_get_contents('/run/secrets/DB_PWD')` |
| `FS_INITIAL_USER` and `FS_INITIAL_PASS` removed after the install | The installer writes the administrator's password into `config.php`. It is read once, when the `users` table is created |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The web installer is open until the install has run |

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, replaced entrypoint,
`app-internal`) on a throwaway `proxy-public` network without Traefik. The
webroot and the database were Docker volumes rather than bind mounts, the webroot
owned by uid 33 with mode 700, as `ops/init.sh` and the `chown` leave it:

- First start: the code was copied as `www-data`; no file was world-writable or
  owned by another user. A restart copied nothing (`index.php` kept its
  modification time)
- `ops/install.sh` installed through the unattended installer; a second run
  reported "already installed" and changed nothing
- Afterwards `config.php` read `FS_DB_PASS` from the secret, held no
  `FS_INITIAL_*` line and no Google Tag Manager. Neither password was in plain
  text in the webroot or in a database dump; the administrator's was a bcrypt hash
- Login with the correct password redirected to the wizard, and the dashboard and
  the customer list answered as the administrator; a wrong password returned the
  login form; the customer list without a session returned the login form
- A customer created through the application's own form was in the database; the
  same POST without the form token, and with the token replayed, created nothing
- `/cron` and `/Cron` answered 403; the cron service ran `php index.php -cron` as
  uid 33 against the database, and its healthcheck reported healthy
- Apache's access log reached `docker logs`
- After `docker compose down` and `up`, the customer was still there, the
  installer stayed closed and login worked
- Hardening from `docker inspect`: `read_only` on the application and the cron
  service, `cap_drop: ALL`, the application with `SETUID` and `SETGID` only, the
  cron service as `33:33` with none, no published port; no secret value in the
  configured environment; the database only on the internal network
- `docker-compose.local.yml` started and served the installer on
  `127.0.0.1:8080`, with `/cron` refused

**Not yet exercised:** Traefik routing and TLS; the browser interface beyond
login, dashboard and the customer form; invoices, accounting and reports; email;
the in-app updater and plugin installation; the web installer path used by the
local file; an upgrade to a newer image; backup and restore.

## Upgrade checklist

FacturaScripts itself is updated in the application; the image carries PHP,
Apache and the operating system.

1. Back up the database, `volumes/facturascripts` and `.secrets/`
2. Application: read the release notes
   (https://github.com/NeoRazorX/facturascripts/releases), then Admin → Updater
3. Runtime: check the stable tag (`latest`) on Docker Hub and the PHP version in
   the image source's `Dockerfile`; bump `APP_TAG` in `.env.example`, then
   `docker compose pull && docker compose up -d`. This does not change the
   installed FacturaScripts version
4. Log in and open the dashboard
5. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
