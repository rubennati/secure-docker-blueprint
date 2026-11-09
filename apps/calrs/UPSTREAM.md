# Upstream Reference

## Source

- **Image:** https://github.com/olivierlambert/calrs/pkgs/container/calrs
- **GitHub:** https://github.com/olivierlambert/calrs
- **Docs:** https://cal.rs/docs/
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** France · Olivier Lambert · EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Scheduling with booking pages and availability read from a CalDAV calendar you already run
- **Last verified:** 2026-11-09 (1.23.3) — lab host (VM), IPv4 LAN, moved from 1.23.2 on a new installation: 79 migrations applied, the sign-in page served through Traefik before and after `down`/`up`, the refused client answered `403`; with `CALRS_TRUSTED_PROXIES` at its default the failed sign-ins were logged and rate-limited under the client's own address, not Traefik's (docs/labs/stack-refresh/2026-11-08-results.md)

## Project maturity

257 stars, first public release in 2026, single maintainer, releases through
2026-09. Under a year of public history at the time of writing. The country in
**Origin** comes from the maintainer's stated GitHub location (Grenoble); the
project publishes no imprint, so it is weaker evidence than a legal page. The verification
below is evidence about this image, not about the project's longevity — the same
distinction `core/orion-belt` records.

## What we use

- `ghcr.io/olivierlambert/calrs:1.22.0` — upstream's own registry. Its README pins
  `:latest`; not used here.
- One container. SQLite in the data directory; upstream ships no database service
  and the application needs none.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `CALRS_SECRET_KEY` from a Docker Secret | No `_FILE` variant. Left unset, the application generates the key and writes `secret.key` into the data directory, next to the data it protects |
| `command` restated in the compose file | Overriding `entrypoint` clears the image's `CMD`; without it the container has nothing to run |
| Healthcheck over bash's `/dev/tcp` | The image carries no HTTP client. `CMD`, not `CMD-SHELL`: `/dev/tcp` is a bash feature and the default shell is dash |
| `read_only: true`, `cap_drop: ALL` | Verified; only `/tmp` and the data volume are written |
| `APP_TRAEFIK_ACCESS=access-vpn` | Registration is open until `ops/bootstrap-admin.sh` has run, and there is no setup password |
| `ops/bootstrap-admin.sh` is interactive | The password prompt uses the terminal directly (`rpassword`), so it cannot be piped |
| `ops/bootstrap-admin.sh` runs the CLI through `config/entrypoint.sh` | `docker compose exec` bypasses the entrypoint. A bare `calrs` started without `CALRS_SECRET_KEY` and wrote `volumes/data/secret.key` — upstream's `src/crypto.rs` takes the environment variable first, then that file, and otherwise generates the file. Measured on the first bootstrap; none written once the calls went through the entrypoint |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403`, over IPv4 and IPv6
- Before the bootstrap, `/auth/register` served the registration form — the open
  window the README describes; afterwards it answered "Registration is disabled."
- `ops/bootstrap-admin.sh` in a terminal asked for the password once, created the
  administrator and closed registration; a second run changed nothing. That run
  called the CLI without the entrypoint and left `volumes/data/secret.key`
  (mode `600`, uid 999) — the script now goes through the entrypoint; on an empty
  instance two runs of it wrote no such file
- Login in the browser: `__Host-calrs_session` (`Secure`, `HttpOnly`, `SameSite=Lax`)
  and `__Host-calrs_csrf`; a login `POST` without `_csrf` got `403`
- A public event type created in the dashboard; a guest without a session booked a
  slot on `/u/<user>/<event>`, and the booking appeared in the administrator's
  list. With no SMTP relay configured, the confirmation page still said an email
  had been sent; with no CalDAV source, the calendar write-back was skipped and
  logged
- First loads under `sec-2`: login page 3 requests, dashboard 5, booking page 7
- Event type and booking unchanged after `docker compose down` and `up`
- Backup as the README describes; `tar` stopped at the `secret.key` above, which
  the operator cannot read. Restore: the archive unpacked into place, ownership
  restored — login, event type and booking back
- Peak 34 MiB (limit 512 MiB)

**Not yet exercised:** a CalDAV source; SMTP; teams and invite links.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secret, `entrypoint.sh`) on a
throwaway `proxy-public` network without Traefik, and against
`docker-compose.local.yml` on a loopback port:

- The pinned image pulled, applied its migrations and reported healthy; the
  bash `/dev/tcp` healthcheck returns `200` from `/healthz`
- With the Docker Secret set, no `secret.key` appears in the data directory, and the
  key is absent from the container's configured environment
- `ops/bootstrap-admin.sh` created the administrator and disabled registration; a
  second run reported "already bootstrapped" and changed nothing
- Login with the correct password redirected (303) and the dashboard answered 200; a
  wrong password re-rendered the form with an error and no session
- With registration disabled, a POST to `/auth/register` carrying a valid token
  created no user — the user list still held one
- A POST without the `_csrf` token was refused with 403
- Hardening from `docker inspect`: uid 999, `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, no published port

**Not yet exercised:** Traefik routing and TLS; a real CalDAV source and therefore
availability, booking and rescheduling; SMTP and the `.ics` invitations; OIDC
login; the public booking page as a guest sees it; backup and restore.

## Version notes

- Moved to `1.23.3` on 2026-11-09 and run on the lab host. A security release:
  the rate limits believe `X-Forwarded-For` only from a trusted proxy
  (`CALRS_TRUSTED_PROXIES`, new; default loopback and private ranges, which
  covers Traefik on the edge network, so the production file keeps the
  default; the local file sets `none`, nothing sits in front of it); outbound
  calendar requests connect only to the addresses they checked, at every
  request, so a CalDAV or EWS source on a private IP literal stops until it is
  on the private-host allowlist (`CALRS_ALLOW_PRIVATE_HOSTS`); captcha and
  meeting webhook no longer follow redirects. No migrations.
- Moved to `1.23.2` on 2026-11-09, run on the lab host. 1.23.1 is a security
  release (a new user could be attached to an existing user's scheduling
  account; the private-address check now also covers 64:ff9b:1::/48 and
  198.18.0.0/15, so a resource feed on such an address stops until its host is
  allowlisted); 1.23.2 refuses a booking whose availability cannot be read. No
  migrations, no configuration change.
- Moved to `1.23.0` on 2026-11-08 and run on the lab host (VM). A minor release
  (booking directory, first day of the week, calendar selection per source,
  `X-Robots-Tag: noindex`); no configuration change.
- Moved to `1.22.0` on 2026-11-05, not run on a host at this tag; `Last verified`
  stays at `1.17.1`. Back up `volumes/data` first: migrations 064 to 076 add
  columns, tables and an index, and rolling back means restoring that backup with
  the old image. Migration 074 renames duplicate team slugs; since `1.19.0`
  `/u/{username}` pages follow the visitor's language. No configuration change;
  `CALRS_SYNC_MIN_AGE` is new and optional. `1.20.6` fixes a reflected XSS in the
  Google Calendar OAuth callback (#299); no GHSA is published.
  https://github.com/olivierlambert/calrs/releases

## Upgrade checklist

1. Read the release notes: https://github.com/olivierlambert/calrs/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data` and `.secrets/calrs_secret_key.txt`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; migrations run at start
6. Log in, then open a booking page
7. Add **Last verified** only if the
   upgrade was exercised on a real install
