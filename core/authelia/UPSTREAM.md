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
- `postgres:17.11-alpine` for storage — the tag `core/keycloak` pins
- `redis:7.4-alpine` for sessions — the tag `core/authentik` pins
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

## Upgrade checklist

1. Read the release notes for breaking changes — configuration keys are renamed
   between minor versions and the old ones are removed after a deprecation period
2. `docker compose run --rm --no-deps authelia authelia validate-config --config /config/configuration.yml` against the new tag
3. Back up the database, `volumes/data` and `.secrets/`
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d` — Authelia migrates the schema at start
