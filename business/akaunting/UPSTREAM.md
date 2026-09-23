# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/akaunting/akaunting
- **GitHub:** https://github.com/akaunting/akaunting
- **Docs:** https://akaunting.com/hc/docs
- **License:** BSL (Business Source License; production use free up to two users, one company or one thousand invoices; converts to GPLv3 four years after each release)
- **Origin:** Turkey · Akaunting Inc · non-EU
- **Use restrictions:** production use is permitted only while it stays within two users, one company and one thousand invoices; beyond any of these a commercial licence is required, and the name, logo and branding may not be removed to create a rebranded or white-labelled version for distribution; each release converts to GPLv3 four years after it is published — https://github.com/akaunting/akaunting/blob/master/LICENSE.txt · checked 2026-09-21
- **Edition gating:** the pages that create records are gated at runtime, not by the licence text: the `plan.limits` middleware runs on every GET whose last segment is `create` and asks `https://api.akaunting.com/plans/limits` for the plan, with the API key of an akaunting.com account (setting `apps.api_key`); without a key the service answers `403` and each of those pages redirects, and the image carries no switch to skip the check. Signing in, the dashboard, the lists and the reports do not touch it — https://github.com/akaunting/akaunting/blob/3.1.21/app/Http/Middleware/RedirectIfHitPlanLimits.php · checked 2026-09-23
- **Commercial model:** commercial licence — https://github.com/akaunting/akaunting/blob/master/LICENSE.txt · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Domain:** Business operations
- **Role:** Accounting for small businesses: invoices, bills, customers, vendors, bank accounts and reports
- **Based on version:** `3.1.21`
- **Last verified:** 2026-09-22 (3.1.21) — behind Traefik with TLS: the install, the login and company wizard, a customer, the reports, a restart, and the README's restore; creating records needs an akaunting.com API key

The origin comes from the governing-law clause of Akaunting's terms of service
(law of Turkey, courts of Istanbul).

## What we use

- `akaunting/akaunting:3.1.21` — the newest image tag. **The image lags the source
  releases**: the repository's newest release is 3.2.4 (2026-09-17). Pinning the
  image means running a release older than the source's newest.
- `mariadb:11.4` — the repository's MariaDB LTS. Upstream's compose uses an untagged
  `mariadb`.
- Not the `-v` image variant: it downloads `version=latest` at build time and is
  not pinned in any meaningful way.

## What we changed and why

| Change | Reason |
|--------|--------|
| Only `storage/` and `.env` mounted, not the whole webroot | Upstream mounts `/var/www/html` as a named volume, so the code lives in the volume and a newer image does not update it. A bind mount there would also hide the image's code entirely. Mounting only the changing paths keeps the pinned tag meaningful |
| `config/entrypoint.sh` replaces the image's entrypoint | The original runs `a2enmod rewrite` and `chown -R` over the webroot at every start, both writes a read-only root refuses |
| `config/rewrite.load` mounted into `mods-enabled/` | The image does not enable `mod_rewrite`; its entrypoint did at runtime |
| `bootstrap/cache` as a tmpfs with `mode: 1023` | The image ships it owned by root, and a plain tmpfs mounts as `755 root` — verified; `www-data` could not write it. Compose takes the tmpfs mode as the decimal of the bit pattern, so 1023 is octal 1777 |
| Apache's tmpfs: `/var/run/apache2` only | It holds the PID file. `/var/log/apache2` keeps the image's links to stdout and stderr: a tmpfs there turned them into files in memory, and no request reached `docker logs` — measured. `/var/lock/apache2` is not needed |
| `cap_add: SETUID, SETGID` | Apache's master starts as root and drops its workers to `www-data`. Measured: with both, the master is uid 0 and six workers uid 33; with `SETUID` alone **all seven stay root while the site still answers 200**. `NET_BIND_SERVICE` is not needed — Docker lets a container bind port 80 |
| Database connection as environment variables, password from a Docker Secret | Laravel reads real environment variables before `.env`. The installer still writes the password into `.env`; `ops/install.sh` deletes that line, and the application keeps working |
| `ops/install.sh` instead of the web wizard | Upstream's own `php artisan install`, run as `www-data`, with both passwords read from the secrets inside the container |
| `config/entrypoint.sh` creates `storage/`'s directories as `www-data` (`setpriv`) | The script runs as root without `CAP_DAC_OVERRIDE`, and `volumes/storage` belongs to `www-data` with mode `700`: as root, `mkdir -p` could not enter it and the container restarted in a loop on a fresh install — measured |
| `ops/install.sh` reads and edits `.env` inside the container | `volumes/app.env` belongs to `www-data` with mode `600`. Read from the host, the "already installed" check could not see the file and let a second run through — and the installer writes a new `APP_KEY` on every run (measured: the key changed); the database password also stayed in the file. Both now run as `www-data` in the container, and the script stops if the password line is still there |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The web installer is open until the install has run |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- On a fresh install the application container restarted in a loop:
  `mkdir: cannot create directory 'storage': Permission denied` — the entrypoint
  runs as root without `CAP_DAC_OVERRIDE`, `volumes/storage` is `www-data`'s with
  mode `700`. With the directories created as `www-data` it came up `healthy`
- `ops/install.sh` as shipped installed the application but could not read
  `volumes/app.env` from the host: `sed` failed, `DB_PASSWORD` stayed in the file,
  and the script still reported success. A second run passed the "already
  installed" check (`grep` could not read the file), replaced `APP_KEY` and then
  failed at "Creating company". With both steps moved into the container, on a
  fresh instance: `DB_PASSWORD` gone, `APP_INSTALLED=true`, and a second run
  reported the install and left `APP_KEY` unchanged
- A client outside the access policy's ranges got `403` on `/` and `/install`,
  over IPv4 and IPv6
- Login in the browser, then the company wizard (company, currencies, finish); the
  dashboard in 25 requests; the reports page
- Every `…/create` page redirected to the user list with "Not able to create a new
  user.": Akaunting fetches its plan limits from `api.akaunting.com`, which answered
  `403` without an API key (the call made from the container). A customer was
  created through the application's store endpoint with the session's CSRF token;
  the same `POST` without the token got `419`
- The interface requests `akaunting.com` and `assets.akaunting.com` from the
  visitor's browser; the API's `ping` answered, its write endpoints refused the
  administrator (`403`) with `X-Company` set
- Customer and login unchanged after `docker compose down` and `up`
- Backup as the README describes; the archive needs `sudo`. Restore into an empty
  database (46 tables), the archive unpacked, ownership restored: `APP_KEY`
  unchanged, login and customer back
- Peaks: application 136 MiB, MariaDB 133 MiB

**Not yet exercised:** invoices, bills and payments — the pages that create them
need an akaunting.com API key; email; the in-app module store (read-only by design
here); an upgrade to a newer image.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, replaced entrypoint,
`app-internal`) on a throwaway `proxy-public` network without Traefik, with the
application code left in the image:

- The pinned image started read-only; before the install every page redirected to
  the web installer
- `ops/install.sh` created 46 tables, the company and the administrator; a second
  run reported "already installed" and changed nothing
- Afterwards `volumes/app.env` held `APP_KEY` and `APP_INSTALLED=true` and no
  database password, and the installer redirected to the login page
- Login with the correct password succeeded; a wrong password returned "These
  credentials do not match our records"; a POST without the token was refused as a
  CSRF mismatch
- The company wizard completed, and a customer created through the application's
  own endpoint was in the database
- After `docker compose down` and `up`, the customer was still there and the
  installer stayed closed
- Hardening from `docker inspect`: `read_only`, `cap_drop: ALL` plus `SETUID` and
  `SETGID`, no published port; Apache's master as uid 0 and its workers as uid 33;
  the secret values absent from the configured environment; the database without a
  route out
- The capability set was measured by removing each capability in turn and checking
  both that the site answers and which uid the workers run as
- With `/tmp` and `/var/run/apache2` as the only tmpfs mounts, the read-only
  container started and its access log reached `docker logs`

**Not yet exercised:** Traefik routing and TLS; the browser interface beyond the
login and wizard endpoints; invoices, payments and reports; email; the in-app module
store (read-only by design here); an upgrade to a newer image; backup and restore.

## Upgrade checklist

1. Read the release notes: https://github.com/akaunting/akaunting/releases
2. Check whether a newer image tag exists — the image lags the source releases
3. Back up the database, `volumes/storage`, `volumes/app.env` and `.secrets/`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`, then apply the database
   migrations of the new release:
   `docker compose exec --user www-data akaunting-app php artisan migrate --force`
   (not exercised here). `php artisan update` is Akaunting's in-app code updater; it
   writes into the code directory and does not apply to this stack
6. Log in and open the dashboard
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install

Because the code is in the image, upgrading is a tag change followed by the
database migration — not an in-app update, which would write into the read-only
code directory.
