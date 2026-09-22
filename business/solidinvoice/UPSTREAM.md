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
- **Based on version:** `3.0.1`
- **Last verified:** 2026-09-22 (3.0.1) — behind Traefik with TLS: the web installer to the end, the onboarding with a client and an invoice, a restart, and the README's restore

## What we use

- `solidinvoice/solidinvoice:3.0.1` — the static binary image. Upstream's compose
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
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The web installer is the setup and is open until it has run |
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

**Not yet exercised:** payments and payment gateways; recurring invoices; email;
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

**Not yet exercised:** completing the web installer, and therefore everything after
it — login, clients, invoices, payments, the background worker; Traefik routing and
TLS; email; backup and restore. This is the least-verified stack in its batch.

## Upgrade checklist

1. Read the release notes: https://github.com/SolidInvoice/SolidInvoice/releases —
   in particular whether the command-line installer and `solidinvoice:install` have
   shipped
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/config`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`
6. Log in and open an invoice
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
