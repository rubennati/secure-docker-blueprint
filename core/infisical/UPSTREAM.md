# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/Infisical/infisical
- **Image registry:** `infisical/infisical` (Docker Hub)
- **Docs:** https://infisical.com/docs/self-hosting/overview
- **Self-host compose reference:** `docker-compose.prod.yml` in the upstream repo
- **License:** MIT (core; some features under a separate enterprise licence)
- **Use restrictions:** none for the MIT-licensed portion; content under any `ee/` directory is under the separate licence in `ee/LICENSE` — https://github.com/Infisical/infisical/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** US · Infisical Inc · non-EU
- **Domain:** Identity, access and secrets
- **Role:** Central secret manager, an alternative to per-stack Docker Secrets
- **Based on version:** `v0.167.6`
- **Last verified:** — (config authored 2026-07-26; not yet run on a live server)

## What we use

- `infisical/infisical:v0.167.6` standalone image (backend + UI + API)
- `postgres:18-alpine` as the secret store
- `redis:7.4-alpine` for cache + job queue
- Custom `config/entrypoint.sh` to inject secrets from Docker Secret files (no `_FILE` support)

## What we changed vs. upstream compose

| Change | Reason |
|--------|--------|
| Custom entrypoint for secret injection | Infisical reads plain env; entrypoint builds `DB_CONNECTION_URI` and exports `ENCRYPTION_KEY`/`AUTH_SECRET` from `/run/secrets/`, then execs `./standalone-entrypoint.sh` |
| `app-internal` network (`internal: true`) | Postgres + Redis not reachable from host |
| `no-new-privileges:true` + `cap_drop: ALL` on all services | Security baseline |
| `read_only` + `tmpfs` on Redis | Baseline |
| `deploy.resources` (memory/cpus/pids) on all services | Bound a compromised container |
| Healthcheck via `node` hitting `/api/status` | Image ships node but not curl/wget |
| Traefik `access-vpn` + `limit-standard` default | A central secret manager must not be public; UI is an SPA |
| Postgres pinned to `18-alpine` | Upstream sample uses `postgres:14-alpine`; blueprint prefers a current supported line |
| DB password generated as hex | URL-safe in `DB_CONNECTION_URI` (avoids `/ + =` breaking the URI) |

## Version notes

- Moved to `v0.167.6` on 2026-11-05, not run on a host at this tag. Upstream's
  upgrade-impact records (`upgrade-impact/data/releases/`) list startup
  database migrations in most releases of the range, no manual step for them.
  Breaking changes: the Agent Vault member, variable and session-log APIs
  change shape (v0.166.4–v0.166.6, v0.167.5); since v0.166.6, revoking auth
  and managing tokens and client secrets on org identities needs the specific
  identity action, so roles on the legacy privilege system without it — the
  built-in Member role included — get `403`, and LDAP auth template URLs on
  private addresses need `ALLOW_INTERNAL_IP_CONNECTIONS=true`; v0.167.0 drops
  the bundled `go-sidecar` binary, which this stack does not use; v0.167.5
  disables creating proxied services and soft-deletes certificates. The
  v0.167.5 certificate migration takes a 10-second lock: a concurrent
  `pg_dump` or other long transaction can make startup fail, so take the
  database backup before, not during, the upgrade; rollback is restoring that
  snapshot. No variable this stack sets changed. No advisory is listed in the
  repository's advisory feed for the range.
- Moved `postgres` from `16-alpine` to `18-alpine` on 2026-11-05, not run on a
  host at this tag. PostgreSQL 18 support: the requirements recommend version 14
  and up, with no upper bound
  (https://infisical.com/docs/self-hosting/configuration/requirements); upstream
  names 16 as its extensively tested version. The 18 image keeps its cluster
  under `/var/lib/postgresql/18/docker`; `PGDATA: /var/lib/postgresql/data` in
  both compose files keeps it on the existing mount. A new major does not read
  the old cluster, so existing data moves by dump and restore: before the tag
  changes, `docker compose exec db sh -c 'pg_dumpall -U "$POSTGRES_USER"' >
  dump.sql`; `docker compose down`; move `./volumes/postgres` aside; set the new
  tag; `docker compose up -d db`; `docker compose exec -T db sh -c 'psql -U
  "$POSTGRES_USER" -d postgres' < dump.sql` (errors that the bootstrap role and
  database already exist are expected); then `docker compose up -d`. A return to
  the old major is only a restore of that dump.

## Upgrade checklist

1. Watch [Infisical releases](https://github.com/Infisical/infisical/releases)
2. Read the changelog for breaking changes / required migrations
3. Back up the database before upgrading:

   ```bash
   docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > infisical-$(date +%Y%m%d).sql
   ```

4. Bump `APP_TAG` in `.env` (prefer a digest pin — see `apps/caldiy`)
5. `docker compose pull && docker compose up -d`
6. Watch migrations on first boot: `docker compose logs app --follow`

## Known limitations

- **No `_FILE` support** — mitigated via the custom entrypoint; secrets stay in `.secrets/`
- **Not yet live-verified** — see the README "Verify on first deploy" gate before marking ✅
- **Enterprise features** — some capabilities require an Infisical licence; core secret management is MIT
