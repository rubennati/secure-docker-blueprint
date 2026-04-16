# Paperless-ngx

Self-hosted document archive: scan → OCR → searchable PDF archive. Optimised for paperless offices with a "consume folder" + mobile scan workflow.

## Architecture

Five services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/paperless-ngx/paperless-ngx` | Django web app + Celery workers + consumer |
| `db` | `postgres:16` | Primary data store (documents, tags, correspondents, users) |
| `redis` | `redis:7-alpine` | Celery broker + worker heartbeat |
| `gotenberg` | `gotenberg/gotenberg` | Converts HTML/Office documents to PDF |
| `tika` | `apache/tika` | Text extraction from scanned PDFs, Office files, emails |

Paperless-ngx drives OCR, classification, and archiving itself; it delegates format conversion to Gotenberg and text extraction to Tika.

### Optional: SSO via Authentik

`sso.yml` overlays Authentik OpenID Connect on top of the standard compose. When active, regular username/password login is disabled and every request redirects to Authentik.

Enable via `COMPOSE_FILE` in `.env`:

```
COMPOSE_FILE=docker-compose.yml,sso.yml
```

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, PAPERLESS_OCR_LANGUAGE, USERMAP_UID/GID, TZ

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/secret_key.txt

# 3. Prepare volume ownership (Paperless drops to USERMAP_UID/GID)
mkdir -p volumes/{data,media,consume,export,postgres,redis}
sudo chown -R 1000:1000 volumes/data volumes/media volumes/consume volumes/export

# 4. Start
docker compose up -d

# 5. Wait for migrations + healthcheck
docker compose logs app --follow
# Look for: "Listening at: http://0.0.0.0:8000"

# 6. Create the first admin user
docker compose exec app python manage.py createsuperuser

# 7. Open the UI
# https://<APP_TRAEFIK_HOST>
```

Default access is `acc-tailscale` + `sec-3` — Paperless typically holds personal documents, so VPN-only with strict headers is the right baseline. Switch to `acc-public` only if you intentionally want it on the open internet (and then consider adding SSO via `sso.yml`).

### Enabling SSO (optional)

Authentik must be running with an OAuth2/OIDC provider configured for Paperless.

1. **In Authentik:**
   - Create an Application (slug `paperless`)
   - Create an OAuth2/OIDC Provider bound to that application
   - Redirect URI: `https://<APP_TRAEFIK_HOST>/accounts/oidc/<SSO_PROVIDER_ID>/login/callback/`
   - Copy the Client ID + Client Secret

2. **In Paperless `.env`:**
   ```
   COMPOSE_FILE=docker-compose.yml,sso.yml
   SSO_PROVIDER_ID=authentik
   SSO_PROVIDER_NAME=Single Sign-On
   SSO_CLIENT_ID=<from authentik>
   SSO_CLIENT_SECRET=<from authentik>
   SSO_SERVER_URL=https://auth.example.com/application/o/paperless/.well-known/openid-configuration
   ```

3. `docker compose up -d` — regular login is now disabled and the login page redirects to Authentik.

## Verify

```bash
docker compose ps                                  # All five services healthy
docker compose exec app python manage.py check    # Django check passes
```

Drop a PDF into `./volumes/consume/` and watch the logs — it should be consumed, OCR'd, and appear in the UI within a few seconds.

## Security Model

- Database, Redis, Gotenberg, and Tika are on `app-internal` (`internal: true`) — none reachable from outside
- `db` credentials, `SECRET_KEY` → Docker Secrets (files under `./.secrets/`)
- Gotenberg runs with JavaScript disabled (`--chromium-disable-javascript`) and only allowed to read from `/tmp` — defence against malicious uploaded HTML
- Redis runs `read_only: true` with tmpfs — no writable root filesystem
- `no-new-privileges:true` on every service
- Default access is VPN-only (`acc-tailscale`)

## Known Issues

- **`USERMAP_UID` / `USERMAP_GID` must match the host owner of `./volumes/`.** Wrong UID = permission errors on consume/media. The default (1000:1000) works for most Debian/Ubuntu users.
- **`user:` cannot be set on the app service.** Paperless uses s6-overlay which requires root for `/run` setup before dropping privileges. Adding `user:` breaks startup.
- **`SSO_CLIENT_SECRET` lives in `.env`, not in `.secrets/`.** `sso.yml` builds a JSON configuration string (`PAPERLESS_SOCIALACCOUNT_PROVIDERS`) and Paperless doesn't support `_FILE` for values embedded inside a JSON env var. This is a Paperless limitation, not a blueprint choice.
- **First OCR of a large document is slow.** Tesseract loads language data lazily; subsequent OCR on the same language is cached and fast.
- **Trailing newlines in secret files break auth.** Use `tr -d '\n'` when generating — Paperless compares `"password\n"` vs `"password"` and rejects logins.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, consume/classify tuning
- [sso.yml](sso.yml) — Authentik OIDC overlay
