# Akaunting

Accounting for small businesses: invoices, bills, customers, vendors, bank
accounts and reports. Laravel on Apache, with MariaDB. Upstream:
[Akaunting](https://github.com/akaunting/akaunting).

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Licence limit — read this first

Akaunting is under the Business Source License, not an open-source licence. Its
additional use grant permits production use **only up to two users, one company
or one thousand invoices**; beyond any of those, a commercial licence is
required. Removing its branding to redistribute it is not permitted. Each release
converts to GPLv3 four years after it is published. The full text is upstream's
`LICENSE.txt`.

## Creating records needs an Akaunting account

Akaunting enforces those limits by asking `api.akaunting.com`. Every page that
creates something — `…/create` for customers, items, invoices, bills — first
fetches the plan limits from `https://api.akaunting.com/plans/limits` with the
API key from an akaunting.com account, and caches the answer for an hour.
Without a key the service answers `403`, and each of those pages redirects to the
user list with "Not able to create a new user." Logging in, the dashboard, the
lists and the reports work without it.

Enter the key from an akaunting.com account where the banner "You have not
entered your API Key!" links to. From then on the server sends it with every
check. A working key was not exercised here.

## Architecture

```text
Internet → Traefik (TLS) → akaunting-app :80 (Apache, mod_php)
                                  │
                     app-internal (internal: true)
                                  │
                           db (MariaDB 11.4)
```

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # secrets, and the two mounted paths
sudo chown -R 33:33 volumes/storage volumes/app.env
docker compose up -d
ops/install.sh admin@example.com "Your Company" billing@example.com
```

`ops/install.sh` runs upstream's own installer from the command line instead of
the web wizard: it creates the tables, the company and the administrator. It
reads both passwords from the Docker Secrets inside the container, so they never
pass through your shell. A second run reports that the instance is installed and
changes nothing.

Log in as the administrator with the password in `.secrets/admin_pwd.txt`. The
first login opens Akaunting's company wizard — currencies, taxes, company details —
which is ordinary first use.

## The open window, and why the router starts closed

Before `ops/install.sh` has run, the web installer is reachable and accepts
whatever database it is given. `.env.example` therefore ships
`APP_TRAEFIK_ACCESS=access-vpn`, the VPN only. After the install, the
installer redirects to the login page.

## What is mounted, and what is not

Upstream's own compose mounts the entire webroot as a volume. This stack mounts
only what changes:

| Path | Holds |
|---|---|
| `volumes/storage` → `storage/` | Uploads, logs, sessions, caches |
| `volumes/app.env` → `.env` | The application key and the installed flag |

Everything else — the application code — comes from the image. The pinned image
carries it as an archive, and `config/entrypoint.sh` unpacks it on every start
into a webroot held in memory (a tmpfs, about 300 MiB), owned by root and
read-only for the web server. So the pinned `APP_TAG` is what runs, and upgrading
means changing the tag. The trade-off: modules installed from Akaunting's in-app
store write into the code directory, which the web server cannot write and which
is rebuilt at every start, so **in-app module installation does not work**. The
two modules the image ships (offline payments, PayPal Standard) are present.

## Security notes

- **Database password.** The installer writes it into `.env`; `ops/install.sh`
  removes that line again. Laravel reads real environment variables before `.env`,
  and the container gets the password from the Docker Secret through
  `config/entrypoint.sh`. The password is absent from `volumes/app.env` and from
  `docker inspect`.
- **Application key.** `APP_KEY` stays in `volumes/app.env`, where Laravel expects
  it. Anything the application encrypts is unreadable without it, so it is part of
  the backup.
- **Hardening.** `read_only`, `cap_drop: ALL`, `no-new-privileges`, no published
  port. Two capabilities are added back, `SETUID` and `SETGID`, because Apache
  starts as root and hands its workers to `www-data` — see UPSTREAM.md for why
  both are needed.
- **Replaced entrypoint.** The image's own entrypoint enables `mod_rewrite` and
  runs `chown -R` over the webroot on every start; a read-only filesystem refuses
  both. `config/rewrite.load` enables the module as a mounted file instead.
- **PHP settings.** `config/php-overrides.ini` sends temporary files to the
  `/var/tmp` tmpfs (`/tmp` holds the image's archive and stays read-only) and
  switches off upload progress, an attack path of CVE-2026-109619.
- **Network.** The database has no route out.

## Status

Run behind Traefik with TLS on 2026-09-22 (3.1.21): the install, the login and
company wizard, a customer, the reports, a restart, and the restore below. The
pages that create records stayed closed without an akaunting.com API key — see
above. Full log in [`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).
The current pin, 3.3.0, has not been run on a host; see
[`UPSTREAM.md`](UPSTREAM.md#version-notes).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/storage`, `volumes/app.env` and `.secrets/`:

```bash
docker exec akaunting-db sh -c 'mariadb-dump -u"$MYSQL_USER" -p"$(cat /run/secrets/DB_PWD)" "$MYSQL_DATABASE"' > akaunting.sql
sudo tar -czf akaunting-files.tar.gz volumes/storage volumes/app.env .secrets
```

`volumes/storage` and `volumes/app.env` belong to `www-data` (33) and are closed to
other users, hence `sudo`. Restore into an empty database:

```bash
docker compose down
# move volumes/ aside, then:
(umask 077; mkdir -p volumes/mysql)
docker compose up -d db
docker exec -i akaunting-db sh -c 'mariadb -u"$MYSQL_USER" -p"$(cat /run/secrets/DB_PWD)" "$MYSQL_DATABASE"' < akaunting.sql
sudo tar -xzf akaunting-files.tar.gz
sudo chown -R 33:33 volumes/storage volumes/app.env
docker compose up -d
```

Without the original `APP_KEY` the encrypted values in the database cannot be
read — which is why `ops/install.sh` refuses a second run: the installer writes a
new key every time.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `3.3.0-v` — the newest upstream release. Scanned 2026-11-08; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `akaunting/akaunting:3.3.0-v@sha256:6c5e9864dfe7…` | 1 · 60 | — | — |
| `mariadb:11.4.13` | 0 · 1 | — | 1 · 25 |

<!-- findings:end -->

The pinned image, `akaunting/akaunting:3.3.0-v`, carries 1 CRITICAL finding
the image scan reports, CVE-2026-99083 in Debian's kernel headers package. A
second one sits inside the application archive the image unpacks at start,
which the scanner does not read: Laravel 10.50.3 (CVE-2026-114509, an API token
authentication bypass), fixed only in Laravel 12 and 13. Akaunting 3.3.0 is the
newest release and is still built on Laravel 10.

**Risk:** nothing in the container runs the kernel headers. The Laravel flaw
concerns the `token` API guard, which Akaunting defines; whether any route uses
it has not been checked, so treat it as possibly reachable. Keep the stack on
the shipped `access-vpn` default and watch for an Akaunting release on a newer
Laravel.

The MariaDB image, `mariadb`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.
