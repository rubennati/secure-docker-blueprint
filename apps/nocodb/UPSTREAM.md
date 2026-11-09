# Upstream Reference

## Source

- **NocoDB project:** https://nocodb.com/
- **GitHub:** https://github.com/nocodb/nocodb
- **Docker Hub:** https://hub.docker.com/r/nocodb/nocodb
- **License:** Sustainable Use License 1.0 (source-available, **not** OSI-approved). NocoDB relicensed from AGPL-3.0; the licence file is dated 2026-01-29
- **Use restrictions:** it may be used or modified only for your own internal business purposes or for non-commercial or personal use, and given to others only free of charge for non-commercial purposes; licensing and copyright notices may not be removed. Only the `master` and `develop` branches are licensed at all — https://github.com/nocodb/nocodb/blob/master/LICENSE.md · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** US · NocoDB Inc · non-EU
- **Domain:** Automation and data
- **Role:** Spreadsheet-style interface on top of a database
- **Last verified:** 2026-11-08 (2026.10.1) — over IPv4: the super-admin from `.env` signed in through the API before and after `down`/`up`, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

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
| **Access `access-vpn`, `limit-standard` and `headers-standard` defaults** | NocoDB cells commonly contain API keys, tokens, credentials → VPN-only makes sense |

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

## Version notes

- Moved to `2026.10.1` on 2026-11-05 (released 2026-10-29). Upstream lists no manual migration step; schema migrations run at
  start. Behaviour changes in 2026.09.1 to 2026.10.1: v3 API currency options
  are `currency_code` and `currency_locale`, and the form validators
  `minValue`, `maxValue` and `custom` are rejected; CSV currency exports drop the
  thousands separator; dates in API responses, webhook payloads and CSV exports
  carry milliseconds; a password change deletes the user's API tokens and
  disconnects OAuth apps; interfaces are renamed classic apps; the image moves
  to Node 24.22.1. `NC_ATTACHMENT_ACCESS_CONTROL_ENABLED` and
  `NC_ALLOW_LOCAL_EXTERNAL_DBS` change meaning or are new; neither is set here.
  Advisories fixed in 2026.10.0 and 2026.10.1 (published 2026-11-02), high:
  GHSA-hpmf-p392-q5j5, GHSA-xmfr-pc8j-4xh5, GHSA-mf7h-mwxr-38r5,
  GHSA-hm8p-622v-9c6j, GHSA-v279-4cwv-mrcj, GHSA-982h-vc99-prcr,
  GHSA-2xx9-r3gm-mw87, GHSA-fx53-qf4h-cx38; medium and low:
  GHSA-r872-6prr-v2jc, GHSA-9g75-jg2x-68m4, GHSA-jcc2-3vff-7867,
  GHSA-qgv3-m9j5-jph8, GHSA-9fp2-px3g-mggq, GHSA-2ggp-wwhj-f84q,
  GHSA-4wph-jpw9-43hh, GHSA-4j94-335x-8wjj, GHSA-ppvx-p9g2-5m37.

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
