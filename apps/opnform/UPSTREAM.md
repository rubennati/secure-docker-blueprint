# Upstream Reference

## Source

- **OpnForm project:** https://opnform.com/
- **GitHub:** https://github.com/JhumanJ/OpnForm
- **Docker images:** `jhumanj/opnform-api` + `jhumanj/opnform-client` on ghcr.io and Docker Hub
- **License:** AGPL-3.0
- **Origin:** France · Julien Nahum · EU
- **Based on version:** `latest`
- **Last checked:** 2026-04-17

## What we use

- Upstream `jhumanj/opnform-api` (Laravel)
- Upstream `jhumanj/opnform-client` (Nuxt)
- Official `postgres:16-alpine`
- Official `redis:7-alpine`
- Docker Secret for Postgres password + inline duplicate for Laravel
- Bind-mount `./volumes/postgres`, `./volumes/redis`, `./volumes/api-storage`

## What we built vs. upstream

The inbox directory was empty — no inbox compose to diff against. This is assembled from:

- OpnForm's upstream `docker-compose.yml` in their GitHub repo
- Blueprint defaults (Docker Secrets, Traefik labels, `app-internal`, etc.)

Key design choices:

| Decision | Reason |
|---|---|
| **Path-based Traefik split on a single hostname** | OpnForm's UI and API share the same domain in upstream. Two Traefik routers on the same `Host(...)` rule with different `PathPrefix` matches + priority ordering |
| **API router priority 100 / UI priority 1** | API paths must match before the UI catch-all. Patterns: `/api`, `/open` (public form submission), `/storage` (uploads) |
| **`POST /forms/*` → API** | Public form submission posts go to the API, but the UI serves `GET /forms/*` for form-filling pages. Method-qualified rule separates them |
| **`POSTGRES_PASSWORD_FILE` used** | Postgres supports `_FILE` natively |
| **`DB_PASSWORD` inline** (as `DB_PWD_INLINE`) | Laravel config reads from env only. Same pattern as Monica, BookStack, Immich |
| **Redis read-only + tmpfs on /tmp** | Hardening consistent with Paperless-ngx, Lychee |
| **`SELF_HOSTED=true`** | Hides billing / cloud-only UI elements |
| **`REGISTRATION_DISABLED=true`** default | Avoids stranger signup on the public form endpoint |
| **Mail driver defaults to `log`** | Safe default — user sets SMTP explicitly |
| **`app-internal` network (`internal: true`)** | Isolate Postgres + Redis |
| **`security_opt: no-new-privileges`** on all services | Baseline |
| **Access `acc-public` + security `sec-2` defaults** | Forms are meant to be filled by external users; sec-3 would be OK if your forms are internal-only |

## Upgrade checklist

1. Check [OpnForm releases](https://github.com/JhumanJ/OpnForm/releases) — note schema migrations in the changelog
2. Back up:
   ```bash
   # DB dump
   docker compose exec -T db sh -c \
     'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > opnform-db-$(date +%Y%m%d).sql
   # API storage (uploaded files, form logos)
   tar czf opnform-storage-$(date +%Y%m%d).tgz volumes/api-storage/
   ```
3. Bump `APP_TAG` in `.env` (use the same tag for both `api` and `client`)
4. `docker compose pull && docker compose up -d`
5. Watch Laravel migration output:
   ```bash
   docker compose logs api --follow
   ```
6. Verify: log in, open an existing form, submit a test response, check the response lands in Postgres

### Rollback

Restore DB dump and `volumes/api-storage/`, revert `APP_TAG`.

## Useful commands

```bash
# Shell into the API
docker compose exec api bash

# Laravel artisan
docker compose exec api php artisan <command>

# Run pending migrations manually
docker compose exec api php artisan migrate --force

# Rotate APP_KEY (invalidates sessions + encrypted response data)
docker compose exec api php artisan key:generate --show

# Manual DB backup
docker compose exec -T db sh -c \
  'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Integration patterns

### OpnForm → n8n / NocoDB

OpnForm supports outgoing webhooks per form:

1. Form settings → **Integrations → Webhook**
2. Target URL: `https://<n8n-host>/webhook/<path>` (or NocoDB's webhook URL — though usually n8n sits in between for transformation)
3. Payload contains the submission as JSON plus the form metadata

This pattern gives you: external user fills OpnForm → webhook fires → n8n normalises / enriches → NocoDB inserts the row. All on your infrastructure, no cloud.

### OpnForm → SMTP

To send confirmation emails to respondents, set:
```env
MAIL_MAILER=smtp
MAIL_HOST=smtp-relay.brevo.com   # or your own
MAIL_PORT=587
MAIL_USERNAME=<username>
MAIL_PASSWORD=<api key>
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=forms@example.com
```

Brevo (ex-Sendinblue) free tier covers typical self-hosted form volume.
