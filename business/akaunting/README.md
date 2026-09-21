# Akaunting

Accounting for small businesses: invoices, bills, customers, vendors, bank
accounts and reports. Laravel on Apache, with MariaDB. Upstream:
[Akaunting](https://github.com/akaunting/akaunting).

## Licence limit — read this first

Akaunting is under the Business Source License, not an open-source licence. Its
additional use grant permits production use **only up to two users, one company
or one thousand invoices**; beyond any of those, a commercial licence is
required. Removing its branding to redistribute it is not permitted. Each release
converts to GPLv3 four years after it is published. The full text is upstream's
`LICENSE.txt`.

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
`APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only. After the install, the
installer redirects to the login page.

## What is mounted, and what is not

Upstream's own compose mounts the entire webroot as a volume. This stack mounts
only what changes:

| Path | Holds |
|---|---|
| `volumes/storage` → `storage/` | Uploads, logs, sessions, caches |
| `volumes/app.env` → `.env` | The application key and the installed flag |

Everything else — the application code — stays in the image, so the pinned
`APP_TAG` is what runs, and upgrading means changing the tag. The trade-off:
modules installed from Akaunting's in-app store write into the code directory,
which is read-only here, so **in-app module installation does not work**. The two
modules the image ships (offline payments, PayPal Standard) are present.

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
- **Network.** The database has no route out.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-21).

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
tar -czf akaunting-files.tar.gz volumes/storage volumes/app.env .secrets
```

Restore into an empty database with `mariadb`, unpack the archive, restore the
`33:33` ownership on `volumes/storage` and `volumes/app.env`, and run
`docker compose up -d`. Without the original `APP_KEY` the encrypted values in the
database cannot be read. Restore is not exercised here.
