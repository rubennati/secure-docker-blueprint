# Upstream Reference

## Source

- **Upstream GitHub:** https://github.com/Infisical/infisical
- **Image registry:** `infisical/infisical` (Docker Hub)
- **Docs:** https://infisical.com/docs/self-hosting/overview
- **Self-host compose reference:** `docker-compose.prod.yml` in the upstream repo
- **License:** MIT (core; some features under a separate enterprise licence)
- **Based on version:** `v0.162.13`
- **Last verified:** — (config authored 2026-07-26; not yet run on a live server)

## What we use

- `infisical/infisical:v0.162.13` standalone image (backend + UI + API)
- `postgres:16-alpine` as the secret store
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
| Traefik `acc-tailscale` + `sec-3-spa` default | A central secret manager must not be public; UI is an SPA |
| Postgres pinned to `16-alpine` | Upstream sample uses `postgres:14-alpine`; blueprint prefers a current supported line |
| DB password generated as hex | URL-safe in `DB_CONNECTION_URI` (avoids `/ + =` breaking the URI) |

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
