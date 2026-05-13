# Upstream Reference

## Source

- **NocoDB project:** https://nocodb.com/
- **GitHub:** https://github.com/nocodb/nocodb
- **Docker Hub:** https://hub.docker.com/r/nocodb/nocodb
- **License:** AGPL-3.0
- **Origin:** US · NocoDB Inc · non-EU
- **Based on version:** `0.301.5`
- **Last verified:** 2026-05-02 (v0.301.5)

## What we use

- Official `nocodb/nocodb`
- Built-in SQLite database (in `./volumes/data/`)
- Docker Secret for `NC_AUTH_JWT_SECRET`
- No separate DB service for the default deployment

## What we changed vs. upstream examples

The inbox directory was empty — no inbox compose to diff against. This is built from upstream docs + the blueprint defaults:

| Change from upstream quickstart | Reason |
|---|---|
| **Traefik labels instead of `-p 8080:8080`** | Blueprint routes via Traefik |
| **`NC_AUTH_JWT_SECRET_FILE`** (Docker Secret) | NocoDB supports `_FILE` natively for the JWT secret — no `.env` exposure |
| **`NC_DISABLE_TELE=true`** | Blueprint default: no telemetry |
| **`NC_INVITE_ONLY_SIGNUP=true`** | Safer default for self-hosted deployments |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Healthcheck on `/api/v1/health`** | Proper readiness gate |
| **Access `acc-tailscale` + security `sec-3` defaults** | NocoDB cells commonly contain API keys, tokens, credentials → VPN-only makes sense |

## Upgrading SQLite → Postgres

For larger deployments (heavy automation traffic, multiple concurrent users, tables > 100k rows), switch the backing DB to Postgres. NocoDB supports native Postgres via a single env var:

```yaml
# Add a db service
db:
  image: postgres:16
  environment:
    POSTGRES_DB: nocodb
    POSTGRES_USER: nocodb
    POSTGRES_PASSWORD_FILE: /run/secrets/DB_PWD
  secrets: [DB_PWD]
  volumes: ["./volumes/postgres:/var/lib/postgresql/data"]
  networks: [app-internal]

# On app service, add env:
NC_DB: "pg://db:5432?u=nocodb&d=nocodb"
NC_DB_PASSWORD_FILE: /run/secrets/DB_PWD
# and attach app to app-internal too
```

Blueprint's existing Postgres + `app-internal` patterns from `apps/paperless-ngx/` or `apps/immich/` can be copied.

Migrating data from SQLite to Postgres requires running NocoDB's CLI `nc-migrate` tool or re-entering data — there is no supported in-place upgrade.

## Upgrade checklist

1. Check [NocoDB releases](https://github.com/nocodb/nocodb/releases) — minor bumps can be breaking
2. Back up:
   ```bash
   tar czf nocodb-data-$(date +%Y%m%d).tgz volumes/data/
   ```
3. Bump `APP_TAG` in `.env` (pin to a specific version)
4. `docker compose pull && docker compose up -d`
5. Watch logs for schema migrations:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, open a table, create a row, issue an API call with a stored token

### Rollback

Restore `volumes/data/`, revert `APP_TAG`. Schema migrations are forward-only — a downgrade after a major bump requires the SQLite backup.

## Useful commands

```bash
# Shell into the container
docker compose exec app sh

# Inspect the SQLite DB (nocodb uses better-sqlite3 internally)
docker compose exec app ls -lh /usr/app/data/
docker compose exec app sqlite3 /usr/app/data/noco.db '.tables'

# Reset the JWT secret (CAUTION: invalidates all tokens)
openssl rand -hex 64 > .secrets/nc_jwt_secret.txt
docker compose restart app
```

## Integration with n8n

Typical automation patterns:

- **n8n → NocoDB**: write rows from webhooks / cron. Use the HTTP node with `xc-token` header.
- **NocoDB → n8n**: use NocoDB Webhooks (Table → Settings → Webhooks) to notify n8n on insert/update/delete — n8n receives at `/webhook/*` paths.

If both apps run on the same host:
- Put `apps/n8n/` and `apps/nocodb/` both on the `proxy-public` network (default) so they can reach each other as `http://nocodb-app:8080` / `http://n8n-app:5678`.
- Or build a shared `automation` network and attach both app services to it.
