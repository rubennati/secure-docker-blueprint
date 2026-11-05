# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/authelia/authelia
- **GitHub:** https://github.com/authelia/authelia
- **Docs:** https://www.authelia.com/configuration/prologue/introduction/
- **Release notes:** https://github.com/authelia/authelia/releases
- **Traefik integration:** https://www.authelia.com/integration/proxies/traefik/
- **License:** Apache-2.0
- **Decision facts checked:** 2026-09-26
- **Origin:** Community · no single company · no single jurisdiction
- **Domain:** Identity, access and secrets
- **Role:** Login portal with two-factor authentication that Traefik asks through forward-auth
- **Based on version:** `4.39.28`

## What we use

- Official `authelia/authelia` image, pinned tag, run as `1000:1000`
- `postgres:18.6-alpine` for storage — the tag `core/keycloak` pins
- `redis:8.10.3-alpine` for sessions — the tag `core/authentik` pins
- The file authentication backend (`users_database.yml`), Argon2 hashes
- Secrets through Authelia's own `_FILE` variables, no entrypoint wrapper
- The configuration template filter, so the committed `configuration.yml` holds no
  deployment value

## Architecture

```text
Internet → Traefik (TLS, 443) → Authelia :9091 (portal)
Traefik ──forward-auth──→ Authelia :9091/api/authz/forward-auth
Authelia → Redis (app-internal) · PostgreSQL (app-internal)
```

## What we changed and why

| Change | Reason |
|--------|--------|
| `user: "1000:1000"` | The image defaults to root, chowns `/config` and drops to `PUID:PGID`, which also default to `0` |
| `read_only: true` plus a writable `/app/.healthcheck.env` | Authelia rewrites that file at every start and exits without naming the cause when it cannot (measured on 4.39.28) |
| Healthcheck against `/api/health` directly | The image's `healthcheck.sh` exits 0 whenever the file above lacks its `X_AUTHELIA_HEALTHCHECK` line |
| `X_AUTHELIA_CONFIG_FILTERS: template` | Domain, database and mail values come from `.env`; `mustEnv` stops the start when one is missing |
| No template expression in comments | The template filter renders comments too; `{{ … }}` in one stops the start |
| Template variables not prefixed `AUTHELIA_` | Authelia reads every `AUTHELIA_*` variable as a setting and refuses one it does not know: *configuration environment variable not expected* |
| Mail password read by the template's `secret` function | `AUTHELIA_NOTIFIER_SMTP_PASSWORD_FILE` configures SMTP even when the file notifier is chosen: *please ensure only one of the 'smtp' or 'filesystem' notifier is configured* |
| File notifier when `SMTP_ADDRESS` is empty | One administrator can run without a relay; codes land in `volumes/data/notification.txt` |
| Deny by default, `two_factor` for every host under the cookie domain | Nothing is reachable through forward-auth that no rule names |
| Redis as `999:1000`, `cap_drop: ALL`, `read_only` | The combination measured for the Redis family in issue #40 |
| `trustForwardHeader` not set in the documented middleware | Upstream's example sets it; this blueprint trusts forwarded headers at the entrypoint only, from Cloudflare |
| Local file: TLS served by Authelia, `*.example.localhost`, SQLite, in-memory sessions | Authelia refuses a portal that is not https and a cookie on bare `localhost`; browsers resolve `*.localhost` themselves |

## Verification performed (2026-09-26)

Local, not behind Traefik on a real host — so no `Last verified` line.

- `authelia validate-config` passes for both notifier branches (file and SMTP).
- Production file with PostgreSQL and Redis: all three services healthy with
  `read_only` and `cap_drop: ALL` on Authelia and Redis; schema migrated to
  version 29 on first start.
- Forward-auth as Traefik calls it, from a container on `proxy-public`: no session
  → `302` to the portal with `rd`; first factor → `200` and a `secure`, `HttpOnly`,
  `SameSite=Lax` cookie on the cookie domain; one factor on a `two_factor` host →
  `302`; one factor on a `one_factor` test rule → `200` with `Remote-User`,
  `Remote-Groups`, `Remote-Name`, `Remote-Email`; wrong password → `401`; a host
  outside the cookie domain → `400`.
- Local file: portal, health, first factor and forward-auth over TLS on
  `auth.example.localhost:9091`.
- The portal's first load: 43 requests (33 JavaScript, 6 JSON, 1 CSS, 1 API),
  headless Chrome.
- Trivy 0.74.0, `--ignore-unfixed`: no CRITICAL or HIGH finding in
  `authelia/authelia:4.39.28`.

Not exercised: registering TOTP or WebAuthn in a browser, mail delivery, a
restore.

## Version notes

- Moved `postgres` from `17.11-alpine` to `18.6-alpine` on 2026-11-05, not run
  on a host at this tag. PostgreSQL 18 support: Authelia supports any version
  the PostgreSQL project still supports and tests against the newest
  (https://www.authelia.com/reference/integrations/database-integrations/). The
  18 image keeps its cluster under `/var/lib/postgresql/18/docker`; `PGDATA:
  /var/lib/postgresql/data` in the compose file keeps it on the existing
  mount. A new major does not read the old cluster, so existing data moves by
  dump and restore: before the tag changes, `docker compose exec db sh -c
  'pg_dumpall -U "$POSTGRES_USER"' > dump.sql`; `docker compose down`; move
  `./volumes/postgres` aside; set the new tag; `docker compose up -d db`;
  `docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres' <
  dump.sql` (errors that the bootstrap role and database already exist are
  expected); then `docker compose up -d`. A return to the old major is only a
  restore of that dump.
- Moved `redis` from `7.4-alpine` to `8.10-alpine` on 2026-11-05, a new major, not
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
  unmaintained one. Authelia names no supported Redis range; it requires 6.0 or
  newer only for ACL user names, which this stack does not set. This service starts
  as UID 999 with the image's entrypoint, which then skips the privilege drop and
  loads the bundled modules; no compose change. Sources:
  https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://www.authelia.com/configuration/session/redis/

## Upgrade checklist

1. Read the release notes for breaking changes — configuration keys are renamed
   between minor versions and the old ones are removed after a deprecation period
2. `docker compose run --rm --no-deps authelia authelia validate-config --config /config/configuration.yml` against the new tag
3. Back up the database, `volumes/data` and `.secrets/`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d` — Authelia migrates the schema at start
