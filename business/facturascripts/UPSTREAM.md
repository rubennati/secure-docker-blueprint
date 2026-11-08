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
- **Last verified:** 2026-11-08 (2026.72) — lab host (VM), IPv4 LAN: moved from 2026.7, `ops/install.sh` ran the unattended installer and closed the web installer, the administrator logged in and reached the first-use wizard before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

The origin comes from the terms on facturascripts.com, which name the site's owner
and apply Spanish law.

## What we use

- `facturascripts/facturascripts:2026.7` — the image publisher's stable channel;
  `latest` is the same image. Newer tags such as `2026.72` are published as
  `beta`, although the GitHub release list does not mark them as pre-releases. PHP 8.4 and Apache on
  Debian 13.
- `mariadb:11.4.13` — the repository's MariaDB LTS. Upstream's compose uses
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
| `ops/install.sh` instead of the web wizard | Upstream's installer in its unattended mode (`unattended=1`), run as `www-data`, with both passwords read from the secrets inside the container. It sends `mysql_socket` empty, as the web form does: without the field the 2026.5 installer stops with a `TypeError` halfway through `config.php` — measured. Fixed upstream in [NeoRazorX/facturascripts#2041](https://github.com/NeoRazorX/facturascripts/pull/2041), merged 2026-09-25; the `2026.7` release contains the fix. The empty field stays, as the web form also sends it; not yet run against `2026.7` |
| `FS_DB_PASS` reads the Docker Secret | The installer writes the password into `config.php` in plain text; `ops/install.sh` replaces the line with `file_get_contents('/run/secrets/DB_PWD')` |
| `FS_INITIAL_USER` and `FS_INITIAL_PASS` removed after the install | The installer writes the administrator's password into `config.php`. It is read once, when the `users` table is created |
| `APP_TRAEFIK_ACCESS=access-vpn` | The web installer is open until the install has run |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403` on `/` and `/cron`, over
  IPv4 and IPv6; `/cron` answered `403` inside the policy as well
- `ops/install.sh admin` finished; `config.php` afterwards read `FS_DB_PASS` from
  the Docker Secret and held no `FS_INITIAL_*` line; a second run reported the
  install and changed nothing
- Login in the browser, the wizard (company, country), a customer created and
  listed; login page 9 requests, the customer list 23
- The updater at 2026.5: "No updates at this time"
- In-app update, on a separate install from the `2026.41` image: the updater
  offered the core update to 2026.5; "Download", then "Update" — the webroot's
  `Core/Kernel.php` reported 2026.5. After `docker compose down` and `up` on the
  same `2026.41` image, the webroot still ran 2026.5 while the image's own copy
  in `/usr/src/facturascripts` was 2026.41, and the updater showed 2026.5 with no
  further update
- Customer and login unchanged after `docker compose down` and `up`
- Backup as the README describes; restore into an empty database (83 tables), the
  archive unpacked, ownership restored — login and customer back
- Peaks: application 113 MiB, MariaDB 130 MiB, cron 10 MiB

**Not yet exercised:** invoices and accounting entries; plugins; email; the
installation's registration, which starts the weekly telemetry.

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

## Version notes

- Moved to `2026.72` on 2026-11-08 and run on the lab host (VM). The image
  repository publishes no release notes; the unattended install and the login
  ran unchanged.
- Moved to `2026.7` on 2026-11-05 (image published 2026-10-21), not run on a
  host at this tag. `2026.7` is the image behind `latest`; the automatic pick
  `2026.72` is the `beta` tag and was not used. The image tag changes PHP,
  Apache and the operating system and seeds the webroot of a new install; an
  existing install keeps the version in its webroot until the in-app updater
  moves it. Upstream's GitHub release notes for 2026.6 to 2026.7 only link to
  the facturascripts.com announcements, which were not reviewed here. The
  release contains the installer fix for an absent `mysql_socket`
  (NeoRazorX/facturascripts#2041). Advisories fixed in 2026.7, published
  2026-10-05, include GHSA-grw9-xvv2-5623 (critical, path traversal in SendMail
  attachments), GHSA-3cjq-m4qh-3w8p (unauthenticated code injection in the
  installer), GHSA-r2vf-58f8-chgr, GHSA-jrgg-j699-qm3h, GHSA-7pf9-mm9p-ph24,
  GHSA-r6rq-mv65-vrw7 (high) and, from 2026.65, GHSA-pmhg-rhr4-5624 and
  GHSA-7598-jq2v-gmxf (high SQL injection); the remaining 2026.7 advisories are
  medium.

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
5. Add **Last verified** only if the
   upgrade was exercised on a real install
