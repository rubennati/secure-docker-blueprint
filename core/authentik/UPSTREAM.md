# Upstream Reference

## Source

- **Image:** https://github.com/goauthentik/authentik/pkgs/container/server
- **GitHub:** https://github.com/goauthentik/authentik
- **Docs:** https://docs.goauthentik.io/
- **Release notes:** https://docs.goauthentik.io/docs/releases/
- **Reference compose:** https://docs.goauthentik.io/docs/installation/docker-compose
- **License:** MIT
- **Edition gating:** enhanced audit logging, client certificate authentication, RADIUS EAP-TLS, password history compliance, privileged access management, account lockdown, and Google Workspace and Microsoft Entra ID provisioning are listed as Enterprise; the list does not include the OIDC or SAML provider — https://docs.goauthentik.io/enterprise/enterprise-features/ · checked 2026-09-21
- **Commercial model:** per-user subscription — https://goauthentik.io/pricing/ · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Netherlands · Authentik Security · EU
- **Domain:** Identity, access and secrets
- **Role:** Identity provider with forward-auth, OAuth2, OpenID Connect and SAML
- **Based on version:** `2026.8.5`
- **Last verified:** 2026-11-02 (v2026.5.7) — step 8 lab host behind Traefik 3.7.17 with PostgreSQL 16 and Redis 7.4: first-run setup from the root URL, a login through the flow executor with password and TOTP (a lab script driving the endpoints the browser UI uses, not a browser), forward-auth through the embedded outpost (302 to the login, `X-Authentik-Username` after it, 500 and never 200 with the server stopped), e-mail delivered through a relay over the worker's `app-egress` network with the corrected compose file applied (docs/labs/ingress/2026-11-01-results.md)

## What we use

- Official `ghcr.io/goauthentik/server` image, same image for `server` and `worker` (different `command`)
- `postgres:16-alpine` as primary database
- `redis:7.4-alpine` as session cache + Celery broker
- Native `file://` secret loading (no entrypoint wrapper needed)

## What we changed and why

| Change | Reason |
|--------|--------|
| Four-service layout with `server` and `worker` on the same image | Matches Authentik's documented production architecture — UI/API and background workers are split so worker load doesn't block the user-facing server |
| `server` exposed through Traefik, `worker` isolated | Worker has no HTTP entry point; keeping it off `proxy-public` is pure defence-in-depth |
| `file://` secrets instead of plain env vars | Passwords/secret key never land in `.env` or in `docker inspect` output |
| Redis with `read_only: true` + `tmpfs: /tmp` | No writable root filesystem, Redis only writes to the persistent data volume |
| `AUTHENTIK_ERROR_REPORTING__ENABLED: "false"` | No telemetry leaving the box |
| `AUTHENTIK_LISTEN__TRUSTED_PROXY_CIDRS` set on server and worker: the private IPv4 ranges, `fc00::/7` and loopback | From 2026.8 forwarded headers count only from a trusted proxy network; upstream's default list lacks IPv6 ULA, which the dual-stack `proxy-public` uses |
| `AUTHENTIK_WEB__BASE_URL: https://${APP_TRAEFIK_HOST}` | New in 2026.8, required from 2026.11; seeds the Base URL system setting on first start |
| Internal hostnames via Docker service names (`db`, `redis`) | Survives renaming of `COMPOSE_PROJECT_NAME` without edits; service-name resolution is guaranteed on `app-internal` |
| `app-internal` with `internal: true` | Blueprint baseline — db/redis/worker have no route to the outside |
| `no-new-privileges:true` everywhere | Blueprint baseline |

## Version / tag notes

- Authentik releases use date-based versioning: `YYYY.MM.patch`. Majors (`2024.x` → `2025.x`) can include schema migrations.
- `postgres:16-alpine` — safe to update within Postgres 16. Postgres 16 → 17 is not automatic (dump/restore or `pg_upgrade` required).
- `redis:7.4-alpine` — safe to update within 7.x.
- Moved to `2026.8.5` on 2026-11-05, not run on a host at this tag; `Last
  verified` stays at 2026.5.7. Breaking in 2026.8: forwarded request headers
  (`X-Forwarded-Proto`, `-Host`, `-For`) are honoured only from a trusted proxy
  network, hence `AUTHENTIK_LISTEN__TRUSTED_PROXY_CIDRS` in `docker-compose.yml`;
  `hash_password` no longer takes the password as an argument (stdin or a hidden
  prompt); the WebAuthn setup stage's "Prevent duplicate devices" option is
  removed. `AUTHENTIK_POSTGRESQL__CONN_OPTIONS` is deprecated (not used here). The
  server's request entrypoint and the proxy outpost, the embedded one included,
  are rewritten from Go to Rust, stated as a one-to-one match: forward-auth
  through the embedded outpost (302 to the login, `X-Authentik-Username` after it)
  and the server healthcheck on `/-/health/live/` have to be checked again on a
  host. New `AUTHENTIK_WEB__BASE_URL`, required from 2026.11. 2026.8.2 carries the
  2026-09-09 security patches already in 2026.5.7 (GHSA-cxwx-9x59-28qm,
  GHSA-qgqp-xh8r-v73r, GHSA-h6c5-mpvq-j4jc, GHSA-m9h4-7j9c-55x9,
  GHSA-cqj8-fxxf-9pg7) plus a libxml2 DOCTYPE patch; 2026.8.5 bumps
  certificate-related dependencies after the eMudhra CA incident.
  https://docs.goauthentik.io/docs/releases/2026.8

## Upgrade checklist

1. Read the release notes for every intermediate version you skip: https://docs.goauthentik.io/docs/releases/
   - Pay special attention to "Breaking changes" and "Manual action required" sections.
2. Back up database + media volumes:

   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > authentik-db-$(date +%Y%m%d).sql
   tar czf authentik-media-$(date +%Y%m%d).tgz ./volumes/media
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch the server container; schema migrations run on first start:

   ```bash
   docker compose logs server --follow
   ```

   Expect `Applying migration ...` lines and finally `Startup complete`.
6. Verify:
   - Login still works
   - `Admin Interface → System → Tasks` — all worker tasks `Successful`
   - `Admin Interface → System → Configuration` — DB and Redis green

### Rollback

Authentik's migrations are forward-only. Downgrading requires restoring the SQL dump and reverting `APP_TAG`.

## Related images to keep in sync

- `postgres` — same tag for `db`; update within the major version
- `redis` — independent; update within 7.x

## Useful commands

```bash
# Shell into the server
docker compose exec server bash

# Check Authentik's effective config (after file:// resolution)
docker compose exec server ak dump_config

# Manually run a migration check
docker compose exec server ak migrate --check

# Create an admin user (if you missed the initial-setup flow)
docker compose exec server ak create_admin_group akadmins
docker compose exec server ak create_admin_user admin admin@example.com

# Run an arbitrary Django management command
docker compose exec server ak <command>

# PostgreSQL dump / restore
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql
cat dump.sql | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# Live log across server + worker
docker compose logs server worker --follow
```
