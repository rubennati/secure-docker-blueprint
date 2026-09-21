# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/akaunting/akaunting
- **GitHub:** https://github.com/akaunting/akaunting
- **Docs:** https://akaunting.com/hc/docs
- **License:** BSL (Business Source License; production use free up to two users, one company or one thousand invoices; converts to GPLv3 four years after each release)
- **Origin:** Turkey · Akaunting Inc · non-EU
- **Use restrictions:** production use is permitted only while it stays within two users, one company and one thousand invoices; beyond any of these a commercial licence is required, and the name, logo and branding may not be removed to create a rebranded or white-labelled version for distribution; each release converts to GPLv3 four years after it is published — https://github.com/akaunting/akaunting/blob/master/LICENSE.txt · checked 2026-09-21
- **Commercial model:** commercial licence — https://github.com/akaunting/akaunting/blob/master/LICENSE.txt · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Domain:** Business operations
- **Role:** Accounting for small businesses: invoices, bills, customers, vendors, bank accounts and reports
- **Based on version:** `3.1.21`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

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
| `cap_add: SETUID, SETGID` | Apache's master starts as root and drops its workers to `www-data`. Measured: with both, the master is uid 0 and six workers uid 33; with `SETUID` alone **all seven stay root while the site still answers 200**. `NET_BIND_SERVICE` is not needed — Docker lets a container bind port 80 |
| Database connection as environment variables, password from a Docker Secret | Laravel reads real environment variables before `.env`. The installer still writes the password into `.env`; `ops/install.sh` deletes that line, and the application keeps working |
| `ops/install.sh` instead of the web wizard | Upstream's own `php artisan install`, run as `www-data`, with both passwords read from the secrets inside the container |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The web installer is open until the install has run |

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
