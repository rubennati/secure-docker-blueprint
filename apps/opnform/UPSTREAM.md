# Upstream Reference

## Source

- **OpnForm project:** https://opnform.com/
- **GitHub:** https://github.com/JhumanJ/OpnForm
- **Docker images:** `jhumanj/opnform-api` + `jhumanj/opnform-client` on ghcr.io and Docker Hub
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** France · Julien Nahum · EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Form builder with shareable forms and submissions
- **Based on version:** `2.8.1`
- **Last checked:** 2026-04-17

## What we use

- Upstream `jhumanj/opnform-api` (Laravel)
- Upstream `jhumanj/opnform-client` (Nuxt)
- Official `postgres:16-alpine`
- Official `redis:7.4-alpine`
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
| **Access `access-public`, `limit-standard` and `headers-standard` defaults** | Forms are meant to be filled by external users; `access-vpn` would be OK if your forms are internal-only |

## Version notes

- Moved to `2.8.1` on 2026-11-05, not run on a host at this tag. Not 2.8.3:
  `jhumanj/opnform-api` carries 2.8.2 and 2.8.3, but `jhumanj/opnform-client`
  stops at 2.8.1 on Docker Hub — the release pipeline runs for both tags were
  cancelled — and `APP_TAG` names both images. Move to 2.8.3 once the client
  tag exists (2.8.2 and 2.8.3 tighten webhook and PDF image URL filtering and
  add no migration). In the range: 2.6.0 and 2.7.0 carry database migrations,
  which the API image runs at start — back up first. 2.7.0 stops sending
  answers to an embedding page by default, revokes sessions and tokens on a
  password change, requires public HTTPS endpoints without redirects for OIDC,
  a TXT proof for new custom domains, and `X-AI-Completion-Token` when polling
  an AI completion. 2.6.1 routes `/api/_nuxt_icon/` to the client in nginx;
  `docker/nginx.conf` already carries it. 2.8.1 adds the optional
  `PUBLIC_UPLOADS_MAX_FILE_SIZE` (50 MB default for temporary uploads), 2.6.0
  the optional `EMAIL_TRACKING_SNS_TOPICS`. Security: 2.6.1 rebuilds on PHP
  8.3.36 for CVE-2026-109618 and CVE-2026-109619 and disables PHP session upload
  progress; 2.7.0 hardens password resets, credential revocation, OAuth/OIDC,
  domain ownership and file signing. No GHSA is published.
- nginx moved to `1.31` on 2026-11-05, not run on a host at this tag.
  1.29.7 enables upstream keepalive by default and makes `proxy_http_version`
  default to 1.1 without a `Connection` header; `docker/nginx.conf` sets both
  explicitly on its proxied locations. 1.31.0 rejects HTTP/2 and HTTP/3
  requests carrying connection-specific headers; this nginx listens on plain
  HTTP/1.1 behind Traefik. Security fixes in the range include CVE-2026-27654
  (1.29.7), CVE-2026-1642 (1.29.5), CVE-2026-42945, CVE-2026-42926,
  CVE-2026-40460 (1.31.0), CVE-2026-9256 (1.31.1), CVE-2026-42530 (1.31.2),
  CVE-2026-56434 (1.31.3), CVE-2026-90439 (1.31.6), CVE-2026-15176,
  CVE-2026-93479, CVE-2026-95101, CVE-2026-97629 and CVE-2026-97205 (1.31.7).

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
