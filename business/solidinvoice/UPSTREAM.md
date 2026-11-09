# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/solidinvoice/solidinvoice
- **GitHub:** https://github.com/SolidInvoice/SolidInvoice
- **Docs:** https://docs.solidinvoice.co
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** SolidInvoice · no country stated in its published terms · no country
- **Domain:** Business operations
- **Role:** Invoicing: clients, quotes, invoices, recurring invoices and payments
- **Last verified:** 2026-11-08 (3.1.2) — over IPv4: the stack healthy and `/` redirecting a new instance to the web installer at `/install` before and after `down`/`up`, the refused client answered `403`; the installer was not driven (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- `solidinvoice/solidinvoice:3.1.2` — the static binary image. Upstream's compose
  pins `:latest`; not used here.
- SQLite in the configuration volume, the installer's recommendation. Upstream's
  compose runs `mysql:8.0` beside it, a line that went out of support in April 2026.

## Installation in 3.0.1

The setup route that works in this release is the web installer. What was found
trying the others, so nobody repeats it:

- **The command-line installer (`app:install`) does not create the schema.** Its
  "Creating database schema" step runs and leaves the database with one table, and
  the next step fails on the missing `users` table. Reproduced on MariaDB 11.4,
  MySQL 8.4 and SQLite, with and without this stack's hardening — the control run
  without hardening failed the same way, so the hardening is not the cause.
- Running the migrations by hand (`doctrine:migrations:migrate`) got further but
  stopped part-way on both server databases, at different migrations.
- Without a `serverVersion` in `SOLIDINVOICE_DATABASE_URL`, Doctrine treats
  MariaDB 11.4 as MySQL 5.6.
- For SQLite the command still insists on `--database-host`.
- Upstream's Helm chart installs with `solidinvoice:install` — a command that does
  not exist in 3.0.1, so the command-line path is being reworked for a later
  release.
- **When the command fails, it logs its full command line, administrator password
  included, in plain text.**

The web installer completes on this stack — database, user account, review,
install — and hands over to the application's onboarding (verified 2026-09-22,
below).

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: 1000:1000` | The image runs as root; it serves unprivileged when the configuration directory belongs to that uid — verified |
| `read_only: true`, `HOME=/tmp` | The binary unpacks its PHP application into `$HOME` on every start; on a read-only root that fails with `mkdir /.SolidInvoice: read-only file system` until `HOME` is the tmpfs |
| Memory limit 3 GiB | Measured: 2.2 GiB peak on start, 1.8 GiB running, of which 0.6 GiB is the tmpfs. At 1 GiB the container was killed for memory 25 times in a row |
| `run --disable-https` | TLS terminates at Traefik |
| `SOLIDINVOICE_ENABLE_TELEMETRY=0` | Already the default; set so the installer cannot change it |
| `APP_TRAEFIK_ACCESS=access-vpn` | The web installer is the setup and is open until it has run |
| `volumes/config/db` created by `ops/init.sh` | The default SQLite path is `/etc/solidinvoice/db/solidinvoice.db`, and the application does not create the directory |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403` on `/` and `/install`,
  over IPv4 and IPv6
- `healthy` 36 s after the first start, at 2.0 GiB
- The web installer in a browser, to the end: welcome, database (Embedded
  Database, SQLite), user account (locale, application URL, name, email, password;
  telemetry left off), review, install ("Generating secret", "Generating build
  id", …), "Installation Complete!". Its four database icons (`/img/*-icon.png`)
  answer `500`; nothing else did
- `volumes/config` then held the vault — its decryption key
  `solidinvoice.decrypt.private.php` with mode `644` — and `db/solidinvoice.db`.
  `ops/init.sh` now creates the directory with mode `700`; with it the container
  started `healthy` and served the login page
- Login, then the onboarding: company and currency, a first client, a first
  invoice (`/invoices/view/<id>`); clients and invoices listed it
- First loads under `sec-2`: the installer 10 requests, login 9, the dashboard 10
- Client and invoice unchanged after `docker compose down` and `up` (`healthy`
  after 30 s)
- Backup as the README describes; restore into place with the ownership restored —
  login, client and invoice back
- Peak 2.2 GiB (limit 3 GiB), as the README states

**Outside this verification:** payments and payment gateways; recurring invoices; email;
the MySQL and PostgreSQL alternatives.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` on a throwaway `proxy-public` network
without Traefik:

- The pinned image started read-only as uid 1000 and reported healthy; `/health`
  answers 200
- Before installation every page redirects to `/install`, which answers 200; the
  installer's welcome page and database step render
- Memory as above, measured with the container unconstrained and again at the
  3 GiB limit (2.0 GiB in use, no restarts)
- Hardening from `docker inspect`: uid 1000, `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, no published port

**Outside this verification:** completing the web installer, and therefore everything after
it — login, clients, invoices, payments, the background worker; Traefik routing and
TLS; email; backup and restore. This is the least-verified stack in its batch.

## Version notes

- Moved `solidinvoice/solidinvoice` to `3.1.2` on 2026-11-05 (released 2026-10-21),
  across 3.1.0 and 3.1.1. Not stopped at 3.1.0 or
  3.1.1: their in-app upgrade aborted on MySQL, MariaDB and PostgreSQL, and they
  ignored `SOLIDINVOICE_APP_SECRET`, so the app secret changed whenever the cache was
  rebuilt. 3.1.2 runs the real database migrations once at startup, under a lock,
  instead of marking them done from a web request (#3024), so `docker compose up -d`
  migrates the SQLite database in `volumes/config/db`; back up `volumes/config`
  first — the upgrade rewrites every invoice-line and quote-line row more than once.
  Behaviour changes from UPGRADE.md: Symfony 8.1 and PHP 8.4.1 (bundled in the
  binary); the Sms77 and Gitter notification transports are removed; all remember-me
  cookies are invalidated, so users log in again; client website URLs must have a
  real domain; lines gain a name (taken from the first line of the description) and
  an explicit order; invoices, recurring invoices and clients gain payment terms, with
  a new company default of Net 30 and existing invoices set to Custom (due dates
  unchanged); issued invoices and quotes freeze their currency, backfilled for older
  documents in 3.1.2. The embedded Caddy now takes the client IP from
  `Cf-Connecting-Ip` and `X-Forwarded-For` of trusted proxies (private ranges by
  default, which includes Traefik on `proxy-public`). The command `run --disable-https
  --skip-intro`, port 8765, `/health` and the `HOME` unpacking are not named as
  changed, so the compose files keep their configuration and hardening. Whether the
  command-line installer completes in 3.1.2 was not examined. Sources:
  https://github.com/SolidInvoice/SolidInvoice/releases/tag/3.1.2,
  https://github.com/SolidInvoice/SolidInvoice/blob/3.1.2/UPGRADE.md

## Upgrade checklist

1. Read the release notes: https://github.com/SolidInvoice/SolidInvoice/releases —
   in particular whether the command-line installer and `solidinvoice:install` have
   shipped
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/config`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`
6. Log in and open an invoice
7. Add **Last verified** only if the
   upgrade was exercised on a real install
