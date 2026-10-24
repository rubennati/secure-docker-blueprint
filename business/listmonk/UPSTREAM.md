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
- **Based on version:** `v6.2.0`
- **Last checked:** 2026-05-03

## What we use

- Official `listmonk/listmonk` image
- PostgreSQL as backing database
- Docker Secrets for database password
- One Traefik router on `access-public` as shipped, with `frame-self@file` before `headers-standard`; the split — admin UI VPN-only, subscriber paths (`/subscription`, `/link`, `/campaign`) public — is a second router the README describes

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
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_LIMIT}@file,frame-self@file,${APP_TRAEFIK_HEADERS}@file,${APP_TRAEFIK_AUTH}"
```

The admin-VPN-only split is a second, path-scoped router on `access-vpn`; the
README carries it under "Access split".

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
