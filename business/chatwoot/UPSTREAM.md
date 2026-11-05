# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/chatwoot/chatwoot
- **GitHub:** https://github.com/chatwoot/chatwoot
- **Docs:** https://www.chatwoot.com/docs/self-hosted
- **License:** MIT (core; the `enterprise/` directory is under a separate enterprise licence)
- **Use restrictions:** none for the MIT-licensed portion; content under the `enterprise/` directory is under the separate licence defined there — https://github.com/chatwoot/chatwoot/blob/develop/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** United States · Chatwoot Inc · non-EU
- **Domain:** Business operations
- **Role:** Customer support across website chat, email and messaging channels in one shared inbox
- **Edition gating:** everything under the repository's `enterprise/` directory is licensed under `enterprise/LICENSE` rather than MIT — https://github.com/chatwoot/chatwoot/blob/develop/LICENSE · checked 2026-09-21
- **Based on version:** `v4.19.1`
- **Last verified:** 2026-09-22 (v4.18.0) — behind Traefik with TLS: the onboarding, the dashboard and its websocket, the API, a website widget, a restart, and the README's restore

The origin comes from the governing-law clause of Chatwoot's terms of service
(State of California).

## What we use

- `chatwoot/chatwoot:v4.19.1` for web and worker. Upstream's production compose pins
  `:latest`; not used here. A `-ce` tag also exists; this stack uses the tag upstream's
  compose names.
- `pgvector/pgvector:0.8.1-pg16` — upstream's production compose uses
  `pgvector/pgvector:pg16`.
- `redis:8.10.3-alpine` — upstream's uses `redis:alpine`.
- Local file storage, upstream's default.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` replaces upstream's rails entrypoint | The original runs `bundle install` on every start; the replacement keeps the database wait and exports the secrets |
| `db:chatwoot_prepare` before the server starts | Upstream documents it as a separate first-time step; it is idempotent, so running it at each start also migrates after an upgrade |
| `user: 1000:1000`, `read_only: true` | The image runs as root; verified unprivileged and read-only through onboarding, API use, jobs and a restart |
| `tmp/`, `log/` and `/tmp` as tmpfs with `mode: 1023` | A plain tmpfs mounts as `755 root`: the web service failed with `Permission denied @ dir_s_mkdir - /app/tmp/cache` until the mode was set. Compose takes the bit pattern as a decimal; 1023 is octal 1777 |
| Worker healthcheck on port 7433 | The image runs sidekiq-alive, which answers there while the worker is registered |
| Redis password from a secret, via a tmpfs config file | Upstream passes it on the command line |
| `FORCE_SSL=false` | TLS terminates at Traefik |
| `APP_TRAEFIK_ACCESS=access-vpn` | The first visit creates the administrator |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403`, over IPv4 and IPv6
- First load: the onboarding page in 7 requests; the onboarding created the first
  account as super administrator (84 requests), the dashboard followed (51) — no
  `429` under `sec-2`
- The dashboard's websocket (`/cable`) opened through the route
- `GET /api/v1/profile` with the session's token headers returned the personal
  access token; with it a contact created and listed through the API; a wrong
  token got `401`
- A website inbox created through the API; its widget page loaded through the
  route with its websocket
- After `docker compose down` and `up`: login, the contact and the websocket
- Backup as the README describes; restore into an empty database without errors,
  the archive unpacked — login and the contact back
- Peaks: Sidekiq 559 MiB, Rails 484 MiB, PostgreSQL 78 MiB, Redis 14 MiB

**Not yet exercised:** email in and out; channels other than the website widget;
the captain and AI features.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, wrapper,
`app-internal`, `app-egress`) on a throwaway `proxy-public` network without Traefik,
from a peer container:

- All four services started; the database was created and prepared on the first
  start
- A fresh install redirected every page to `/installation/onboarding`; submitting it
  created the administrator, and afterwards the onboarding page redirected away
- Login through `POST /auth/sign_in` returned 200 with tokens; a wrong password
  returned 401
- Public account sign-up returned 404
- With the access token, a contact was created and listed; without it the API
  returned 401
- Sidekiq processed 9 jobs with none failed; its health endpoint on 7433 answered 200
- After `docker compose down` and `up`, the contact was still there and onboarding
  stayed closed
- Hardening from `docker inspect`: web and worker uid 1000, read-only, all
  capabilities dropped; Redis uid 999, read-only; no published port; the secret
  values absent from the configured environment; PostgreSQL and Redis without a
  route out

**Not yet exercised:** Traefik routing and TLS; the browser dashboard; the website
widget and its websocket; email in and out; messaging channel integrations; the
enterprise features; backup and restore; an upgrade across versions.

## Version notes

- pgvector moved to `0.8.7-pg16` on 2026-10-31, not run at this tag; the stack's
  state is anchored on the application pin, which did not move. 0.8.2 to 0.8.7 list no breaking change and no advisory; 0.8.3 and
  0.8.4 fix index corruption and a repair error with HNSW vacuuming, 0.8.2, 0.8.6
  and 0.8.7 fix buffer overflows. After the image moves, upstream's upgrade note
  applies per database: `ALTER EXTENSION vector UPDATE;`.
- Moved to `v4.19.1` on 2026-11-05 (released 2026-10-24), web and worker
  together, not run on a host at this tag. v4.19.0 retires Captain V1:
  installations with V1 assistant instructions must migrate them to V2 before
  upgrading (upstream's `docs/captain_v1_sunset.md`); this stack has not
  exercised Captain. New optional variables only — `SEARCH_TIME_RANGE_LIMIT_DAYS`,
  `WEB_CONCURRENCY`, `AUTO_RESOLVE_MIN_MINUTES`, `AUTO_RESOLVE_CRON`,
  `SIDEKIQ_ALIVE_HOST` and `SIDEKIQ_ALIVE_PORT` (still 7433 by default, so the
  worker healthcheck is unchanged); upstream's production compose did not
  change; the web service migrates at start. Both releases recommend upgrading
  for security hardening (Twilio webhook verification, CSS sanitization) and
  v4.19.1 moves the build stage to Node.js 24.22.1 (CVE-2026-111497, build only).
  No GHSA named.
- Moved `redis` from `7.4-alpine` to `8.10.3-alpine` on 2026-11-05, a new major, not
  run on a host at this tag; the tag follows the 8.10 patch releases (8.10.3,
  2026-10-26). Redis 8 is offered under RSALv2, SSPLv1 or AGPLv3 at the user's
  choice (7.4: RSALv2 or SSPLv1). The image bundles the Query Engine, JSON, time
  series and probabilistic data types as modules, which the image's entrypoint loads
  at start on amd64 and arm64; this stack uses none of them. 8.x reads the 7.4 data
  files in place, but Redis does not load files written by a newer version, so a
  rollback needs the backup of the Redis data. The one potentially breaking change
  upstream lists: `GETRANGE` with an out-of-range negative end returns an empty
  string. Security fixes in the 8.10 line: CVE-2026-62356 (8.10.1, heap write when
  loading a Count-min sketch from an RDB file), queued `MULTI` commands keeping
  access to keys whose ACL permission was revoked (8.10.2), and a cluster-bus
  overflow that needs cluster mode (8.10.3). The 7.4 line still receives fixes
  (7.4.12, 2026-10-26); the move is to the newest stable line, not away from an
  unmaintained one. Chatwoot recommends Redis 6 or newer for production and names no
  upper limit. This service starts as UID 999 through its own
  `config/redis-entrypoint.sh`, which execs `redis-server` directly, so the image
  entrypoint's privilege handling and module loading do not apply; no compose
  change. Sources: https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://developers.chatwoot.com/self-hosted

## Upgrade checklist

1. Read the release notes: https://github.com/chatwoot/chatwoot/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database, `volumes/storage` and `secret_key_base.txt`
4. Bump `APP_TAG` in `.env.example` — web and worker move together
5. `docker compose pull && docker compose up -d`; the web service migrates at start
6. Log in and open a conversation
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
