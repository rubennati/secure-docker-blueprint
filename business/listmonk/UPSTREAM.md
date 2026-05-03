# Upstream Reference

## Source

- **Project:** https://listmonk.app
- **GitHub:** https://github.com/knadh/listmonk
- **Docker Hub:** https://hub.docker.com/r/listmonk/listmonk
- **License:** AGPL-3.0
- **Origin:** India · Zerodha (Kailash Nadh) · non-EU
- **Based on version:** `v6.1.0`
- **Last checked:** 2026-05-03

## What we use

- Official `listmonk/listmonk` image
- PostgreSQL as backing database
- Docker Secrets for database password
- Two-router Traefik pattern: admin UI VPN-only (`/` via `acc-tailscale`), subscriber paths public (`/subscription`, `/link`, `/campaign`)

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik two-router pattern** | Admin UI must not be public; subscription/unsubscribe must be |
| **Docker Secrets for `LISTMONK_db__password`** | Security baseline |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`LISTMONK_app__admin_username` via env** | Blueprint: no hardcoded credentials |

## Router pattern

```yaml
# Private router — admin UI (VPN only)
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"

# Public router — subscriber paths
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-public.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/subscription`, `/link`, `/campaign`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-public.middlewares=acc-public@file,sec-2@file"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-public.priority=10"
```

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
