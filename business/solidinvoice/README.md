# SolidInvoice

Invoicing for small businesses: clients, quotes, invoices, recurring invoices
and payments. One self-contained binary — PHP and a web server embedded — with
SQLite in the configuration volume. Upstream:
[SolidInvoice](https://github.com/SolidInvoice/SolidInvoice).

## Architecture

```text
Internet → Traefik (TLS) → solidinvoice-app :8765
                                  │
                   volumes/config (secrets vault + SQLite in db/)
```

One container, no database service. The application's own installer recommends
SQLite for small and medium businesses; MySQL and PostgreSQL are its
alternatives.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # creates volumes/config/db
sudo chown -R 1000:1000 volumes/config
docker compose up -d            # about a minute until healthy
```

Then open `https://<host>/install` over the VPN. The installer asks, in turn, for
the database — choose **Embedded Database (SQLite)** — then the administrator's
account (locale, the application's URL, name, email, password), shows a review,
and installs: it generates the application's secret, stores it in
`volumes/config` and creates the schema. The first login continues into the
application's onboarding — company and currency, optionally a first client and a
first invoice. The installer's command-line counterpart does not complete in this
release; see [UPSTREAM.md](UPSTREAM.md#installation-in-301).

## The open window, and why the router starts closed

Until the installer has run, every page redirects to `/install`, and whoever
reaches it sets up the instance and its administrator. `.env.example` therefore
ships `APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only.

Self-registration is off by default (`SOLIDINVOICE_ALLOW_REGISTRATION` defaults
to `0`), so after the install, further users are invited by the administrator.

## Resources

This stack is heavier than its size suggests. Measured on start: 2.2 GiB at peak
and 1.8 GiB once running — about 1.4 GiB of process memory and 0.6 GiB of unpacked
application and caches in the tmpfs, which counts against the container's limit.
At a 1 GiB limit it was killed for memory in a loop and never came up. The limit
is set to 3 GiB.

## Security notes

- **Hardening.** The image runs as root by default; this stack pins it to
  `APP_UID:APP_GID` (1000), with `read_only`, `cap_drop: ALL`, `no-new-privileges`
  and no published port.
- **The binary unpacks itself.** On every start it extracts its PHP application
  into `$HOME/.SolidInvoice`, so `HOME` points at the tmpfs.
- **HTTPS is Traefik's.** The binary can obtain its own certificate; it runs with
  `--disable-https` here.
- **The vault key is written world-readable.** The configuration directory holds
  the encrypted secrets vault and its decryption key, which the application
  writes with mode `644`. `ops/init.sh` creates the directory with mode `700`.
- **Telemetry.** Off by default in this release; the compose file sets
  `SOLIDINVOICE_ENABLE_TELEMETRY=0` so an installer choice cannot enable it.
- **Installer logging.** When the command-line installer fails, it writes its full
  command line — including the administrator password — into the log in plain
  text. The web installer is the path used here, but anyone running the command
  line by hand should know it.

## Status

Run behind Traefik with TLS on 2026-09-22 (3.0.1): the web installer to the end,
the onboarding with a client and an invoice, a restart, and the restore below.
Full log in [`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8765/install — after about a minute
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik is not used. It mounts the same
`volumes/config`, so run one at a time.

## Backup

`volumes/config` is the whole state: the encrypted secrets vault and the SQLite
database under `db/`. Stop the container for a consistent copy of the database:

```bash
docker compose stop solidinvoice-app
tar -czf solidinvoice-config.tar.gz volumes/config
docker compose start solidinvoice-app
```

Restore by unpacking it back into place, restoring the `1000:1000` ownership, and
running `docker compose up -d`. The vault's decryption key is in the same
directory, so the archive is self-contained — and has to be kept as private as
the data.
