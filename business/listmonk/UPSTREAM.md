# Upstream Reference

## Source

- **Project:** https://listmonk.app
- **GitHub:** https://github.com/knadh/listmonk
- **Docker Hub:** https://hub.docker.com/r/listmonk/listmonk
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** India · Zerodha (Kailash Nadh) · non-EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Newsletter and mailing-list manager
- **Last verified:** 2026-11-03 (v6.2.0) — lab host behind Traefik 3.7.17 on its edge network: the super admin on the first visit, login, a double opt-in list, the public subscription form, the opt-in and a campaign mail; the README's borgmatic entry did not restore (the host's PostgreSQL client), the PostgreSQL 16 client did (docs/labs/ingress/2026-11-01-results.md). Earlier: 2026-05-03 (Last checked)

## What we use

- Official `listmonk/listmonk` image
- PostgreSQL as backing database
- Docker Secrets for database password
- One Traefik router on `access-vpn` as shipped (closed until the owner exists and SMTP is set — final audit FA-01), with `frame-self@file` before `headers-standard`; the split — admin UI VPN-only, subscriber paths (`/subscription`, `/link`, `/campaign`) public — is a second router the README describes

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik router with `frame-self` before the headers profile** | The campaign preview renders in an iframe; `headers-standard` alone would deny it |
| **Docker Secrets for `LISTMONK_db__password`** | Security baseline |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`LISTMONK_app__admin_username` via env** | Blueprint: no hardcoded credentials |

## Router pattern

```yaml
# The one router as shipped — public, with frame-self before the headers profile
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=frame-self@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}"
```

The admin-VPN-only split is a second, path-scoped router on `access-vpn`; the
README carries it under "Access split".

## Version notes

- Moved `postgres` from `16-alpine` to `18.6-alpine` on 2026-11-05, not run on a
  host at this tag. PostgreSQL 18 support: the installation docs require
  Postgres 12 or newer, with no upper bound
  (https://listmonk.app/docs/installation/); `smtp-guard` uses the same image as
  its client. The 18 image keeps its cluster under
  `/var/lib/postgresql/18/docker`; `PGDATA: /var/lib/postgresql/data` in both
  compose files keeps it on the existing mount. A new major does not read the
  old cluster, so existing data moves by dump and restore: before the tag
  changes, `docker compose exec db sh -c 'pg_dumpall -U "$POSTGRES_USER"' >
  dump.sql`; `docker compose down`; move `./volumes/postgres` aside; set the new
  tag; `docker compose up -d db`; `docker compose exec -T db sh -c 'psql -U
  "$POSTGRES_USER" -d postgres' < dump.sql` (errors that the bootstrap role and
  database already exist are expected); then `docker compose up -d`. A return to
  the old major is only a restore of that dump.

## Upgrade checklist

1. Check [Listmonk releases](https://github.com/knadh/listmonk/releases)
2. Back up:

   ```bash
   docker compose exec db pg_dump -U listmonk listmonk > listmonk-$(date +%Y%m%d).sql
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Run DB upgrade:

   ```bash
   docker compose run --rm app --upgrade
   ```

6. Verify: log in, send a test campaign

## Useful commands

```bash
# Run DB upgrade (required after version bumps)
docker compose run --rm app --upgrade

# Create admin user (first install)
docker compose run --rm app --install
```
