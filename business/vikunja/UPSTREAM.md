# Vikunja — Upstream

- **Last verified:** 2026-11-08 (2.8.0) — over IPv4, with Postgres 18.6 under cap_drop: a project and a task created on 2.3.0 survived the upgrade to 2.8.0 and a `down`/`up`, the refused client answered `403`; a restore through `docker exec` (docs/labs/stack-refresh/2026-11-08-results.md)

## Source

- **Repository:** https://github.com/go-vikunja/vikunja
- **Docker Hub:** https://hub.docker.com/r/vikunja/vikunja
- **Docs:** https://vikunja.io/docs/
- **License:** AGPL-3.0
- **Edition gating:** the self-hosted core is complete and free for personal or company use; a Pro tier for instances you host yourself adds an admin panel, audit logs and time tracking — https://vikunja.io/pricing/ · checked 2026-09-21
- **Commercial model:** paid self-hosted edition; the Cloud offering is the same features without the operations work — https://vikunja.io/pricing/ · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · Konrad Langenberg Software · EU
- **Domain:** Business operations
- **Role:** Task and project management with lists, boards and calendars

## License

AGPL-3.0 — fully open source, self-hosting permitted without restrictions.

## Release notes

https://github.com/go-vikunja/vikunja/releases

## What we use

- `vikunja/vikunja` Docker Hub image as the base
- Upstream single-binary image (API + frontend combined)
- Upstream PostgreSQL recommendation for multi-user setups

## What we changed

| Deviation | Reason |
|---|---|
| Custom `Dockerfile` — multi-stage build from `busybox:musl` | Upstream image is `FROM scratch` with no shell, cat, or wget. We add `/bin/sh`, `/bin/cat`, `/bin/wget` for secrets injection and HTTP healthcheck. |
| `COPY --chown=1000:0 /files-init /app/vikunja/files` | Upstream leaves `/app/vikunja/files` root-owned; named volume inherits root ownership; Vikunja (uid=1000) cannot write. `USER` directive doesn't work in FROM scratch images. |
| Custom `config/entrypoint.sh` | Vikunja has no `_FILE` env var support. Entrypoint injects JWT key, DB password, OIDC secret, and SMTP password from Docker Secrets at startup. Uses intermediate variables to avoid POSIX `export VAR=$(cmd)` silent-failure bug. |
| HTTP healthcheck via `wget` instead of `vikunja healthcheck` | The built-in healthcheck subcommand spawns a fresh process without the entrypoint's env vars — it fails DB auth every time. |
| Authentik OIDC configured | Upstream docs show plain local login. We configure OIDC as the only login method. |
| Traefik `redirectregex` middleware for SSO auto-redirect | `/login` auto-redirects to Authentik — no manual button click required. |
| `VIKUNJA_SERVICE_IPEXTRACTIONMETHOD: xff` | Required for correct client IP behind Traefik. |
| Rate limiting enabled | `VIKUNJA_RATELIMIT_ENABLED: true` — not enabled by default upstream. |

## Version notes

- Moved to `2.8.0` on 2026-11-08. The pin named
  `2.6.0` but `APP_DIGEST` held the digest of `2.3.0`; the build pulls by digest,
  so every install since that bump ran 2.3.0 (`/api/v1/info` answered `v2.3.0`).
  `APP_DIGEST` and the `Dockerfile` defaults now name the digest of `2.8.0`
  (`docker buildx imagetools inspect vikunja/vikunja:2.8.0`). 2.7.0, 2.7.1 and
  2.8.0 carry 6, 41 and 19 security fixes, among them
  GHSA-3598-wrmp-2pp2 (high, richtext table expansion); the changelog names no
  breaking change or configuration change. Tested as an upgrade: a project and a
  task created on the 2.3.0 build were present after the rebuild on 2.8.0, which
  migrated the schema on start.
- Moved `postgres` from `17-alpine` to `18.6-alpine` on 2026-11-05. PostgreSQL 18 support: upstream's CI tests PostgreSQL 18 and
  its full Docker example uses `postgres:18`
  (https://vikunja.io/docs/installing/). The 18 image keeps its cluster under
  `/var/lib/postgresql/18/docker`; `PGDATA: /var/lib/postgresql/data` in both
  compose files keeps it on the existing mount. A new major does not read the
  old cluster, so existing data moves by dump and restore: before the tag
  changes, `docker compose exec db sh -c 'pg_dumpall -U "$POSTGRES_USER"' >
  dump.sql`; `docker compose down`; remove the `db_data` volume once the dump is
  checked; set the new tag; `docker compose up -d db`; `docker compose exec -T
  db sh -c 'psql -U "$POSTGRES_USER" -d postgres' < dump.sql` (errors that the
  bootstrap role and database already exist are expected); then `docker compose
  up -d`. A return to the old major is only a restore of that dump.

## Upgrade checklist

1. Read the release notes for breaking changes or migration steps
2. Check if the database schema migration runs automatically (it does — Vikunja auto-migrates on startup)
3. Bump `APP_TAG` in `.env`
4. `docker compose build --pull && docker compose up -d`
5. Verify the UI loads and existing tasks are intact
6. Verify Authentik OIDC login still works
7. Update `Last verified` date and version in this file
