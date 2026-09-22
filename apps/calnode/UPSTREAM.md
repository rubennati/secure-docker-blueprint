# Upstream Reference

## Source

- **Image:** https://github.com/Calnode/calnode/pkgs/container/calnode
- **GitHub:** https://github.com/Calnode/calnode
- **Docs:** https://github.com/Calnode/calnode/blob/main/DEPLOY.md
- **License:** Apache-2.0
- **Decision facts checked:** not yet
- **Origin:** Calnode · no country stated in its published terms · no country
- **Domain:** Publishing, forms and scheduling
- **Role:** Scheduling with booking pages, an admin interface and a REST API, as one binary with SQLite
- **Based on version:** `0.9.0`
- **Last verified:** 2026-09-22 (0.9.0) — behind Traefik with TLS: the setup, the API, the admin interface after `reset-admin`, a guest booking, a restart, and the README's restore

## Project maturity

90 stars, pre-1.0 (`0.9.0`), releases through 2026-09, published by a GitHub
organisation that states no location. Under a year of public history at the time
of writing. The verification below is evidence about this image, not about the
project's longevity.

## What we use

- `ghcr.io/calnode/calnode:0.9.0` — upstream's own registry. Its quick start pins
  `:latest`; not used here.
- One container. SQLite at `/data/calnode.db`; upstream ships no database service.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `CALNODE_ENCRYPTION_KEY` and `CALNODE_RECOVERY_SECRET` from Docker Secrets | Neither has a `_FILE` variant; upstream sets them as plain environment variables |
| `user: 1000:1000` | The image runs as root. It works unprivileged when the data directory belongs to that uid — verified |
| `read_only: true` with `tmpfs: /tmp` | Verified: migrations, first-run setup, API calls and a restart |
| `BASE_URL` built from `APP_TRAEFIK_HOST` with `https://` | The scheme is what switches the application into production mode |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | `POST /v1/setup` is public until it has run once |
| `ops/setup.sh` calls the route from inside the container | No port is published, and the route is reached over loopback |
| Litestream left unconfigured | It is built into the image's entrypoint and inert without `LITESTREAM_REPLICA_URL` |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403` on `/` and on
  `POST /v1/setup`, over IPv4 and IPv6
- `ops/setup.sh` returned the owner's API key once; a second run got `409`
- API through the route: `/v1/event-types` `401` without a key, `200` with
  `Authorization: Bearer` and with `X-API-Key`, `401` with a wrong key; an event
  type and working hours for five weekdays created through the API
- The admin interface said "No login methods are configured": `/v1/setup` creates
  the owner without a password (`/v1/auth/status`: `email_login` false). Upstream's
  `calnode reset-admin`, run through the entrypoint, set a password and enabled
  email login; the admin interface then signed in
- `Set-Cookie: calnode_session=…; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax` —
  no `Secure` despite the `https://` `BASE_URL`. Upstream sets the flag only in the
  Google and Microsoft sign-in setup (`internal/server/server.go`)
- The guest booking page `/book/<slug>` showed every day unavailable until working
  hours existed; afterwards a guest booked a slot (`POST /v1/bookings` `201`), and
  the API listed it as confirmed
- First loads under `sec-2`: admin interface 54 requests, login 28, after login 34,
  booking page 3; the admin interface requests `fonts.googleapis.com`
- Event type, working hours, booking and the email login unchanged after
  `docker compose down` and `up`
- Backup as the README describes; restore into place with the ownership restored —
  all of it back
- Peak 149 MiB (limit 512 MiB)

**Not yet exercised:** calendar providers; SMTP; Litestream; the MCP endpoint and
its OAuth flow.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, `entrypoint.sh`) on
a throwaway `proxy-public` network without Traefik:

- The pinned image pulled, applied its migrations and reported healthy; `/healthz`
  answers through the image's own `wget`
- `ops/setup.sh` created the owner with the requested timezone and returned an
  API key; a second run received `409 Conflict` and the script reported it
- The API key authenticated `GET /v1/users` both as `Authorization: Bearer` and as
  `X-API-Key`; no key and a wrong key each returned `401`
- After `docker compose down` and `up`, the account and the key still worked
- Started with an `https://` `BASE_URL` and no encryption key, the application
  refused to serve: `keyvault: CALNODE_ENCRYPTION_KEY must be set in production`
- Hardening from `docker inspect`: uid 1000, `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, no published port; the secret values are absent from the
  container's configured environment

**Not yet exercised:** Traefik routing and TLS; the admin interface in a browser;
a real calendar provider, and therefore availability, booking and rescheduling;
SMTP; the built-in video, recording and notetaking features, which need a LiveKit
server; the MCP server; Litestream replication and restore; backup and restore.

## Upgrade checklist

1. Read the release notes: https://github.com/Calnode/calnode/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up `volumes/data` and both files in `.secrets/`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`; migrations run at start
6. Check `/healthz`, then make an authenticated API call
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install

Pre-1.0: read the release notes for breaking changes before every bump.
