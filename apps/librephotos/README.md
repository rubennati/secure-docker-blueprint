# LibrePhotos

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Self-hosted photo management with face recognition, object detection, location data, and similarity search. Fork of OwnPhotos. Four-service stack: nginx proxy, Django backend with ML workers, React frontend, and PostgreSQL.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `proxy` | `reallibrephotos/librephotos-proxy:latest` | nginx — routes `/api` → backend, `/` → frontend, serves media files |
| `backend` | `reallibrephotos/librephotos:latest` | Django + gunicorn + ML workers (face detection, CLIP, scene classification) |
| `frontend` | `reallibrephotos/librephotos-frontend:latest` | Static React build |
| `db` | `pgautoupgrade/pgautoupgrade:16-bookworm` | Postgres with automatic major-version upgrade on startup |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, SCAN_DIRECTORY, ADMIN_EMAIL, ADMIN_USERNAME

# 2. Generate DB secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Generate SECRET_KEY and ADMIN_PASSWORD
SECRET_KEY_VAL=$(openssl rand -base64 48 | tr -d '\n')
ADMIN_PWD_VAL=$(openssl rand -base64 24 | tr -d '\n')
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY_VAL}|" .env
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PWD_VAL}|" .env
echo "Initial admin password: ${ADMIN_PWD_VAL}"  # save this, then delete from .env

# 5. Create volume directories
mkdir -p volumes/db volumes/protected_media volumes/logs volumes/cache volumes/pictures

# 6. Start
docker compose up -d

# 7. Wait for first-run migrations + ML model download (~5 min)
docker compose logs backend --follow
# Watch for: "Listening at: http://0.0.0.0:8001"

# 8. Open UI and log in
# https://<APP_TRAEFIK_HOST>
# Credentials: ADMIN_USERNAME / ADMIN_PASSWORD from .env
```

## Verify

```bash
docker compose ps                              # four services up
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **`ADMIN_PASSWORD` is only read on first startup** — remove from `.env` after initial login and change it in the UI. Leaving it in `.env` is a secondary exposure.
- **`SECRET_KEY`** encrypts Django sessions and CSRF tokens. Rotating invalidates all logins (acceptable).
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **`pgautoupgrade` runs major-version Postgres upgrades automatically** — convenient, but means a `docker compose pull` can trigger a DB migration. Back up before updating.
- **`DEBUG=0`** — Django debug output off in production.
- **`CSRF_TRUSTED_ORIGINS` pinned to `https://${APP_TRAEFIK_HOST}`** — Django admin access requires this.
- **Postgres on `app-internal` (`internal: true`)** — not reachable from outside the app.
- **`SCAN_DIRECTORY` bind-mounted read-only into proxy** — proxy serves thumbnails directly from disk.
- **`no-new-privileges:true`** on all services.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run ML model download and Django bootstrap timing.
- **`DB_PWD_INLINE` duplicates the DB password** — LibrePhotos backend's `DB_PASS` env var has no `_FILE` support. The Postgres service reads `POSTGRES_PASSWORD_FILE` from a Docker Secret, but the backend needs the same value inline in `.env`. Setup step 3 syncs them. Mismatch = backend cannot connect.
- **`APP_TAG=latest` is not reproducible** — LibrePhotos publishes weekly builds under `latest`. Pin to a dated tag if upgrade discipline matters.
- **ML model download on first use** — face recognition and object detection pull ~1.5 GB of models into `volumes/cache/`.
- **Initial scan is slow** — LibrePhotos processes each photo through multiple ML pipelines (~1-2 seconds per photo). A 10 000-photo library takes several hours on a CPU-only machine.
- **MAPBOX_API_KEY is optional** — the map view is disabled if empty; no error is raised.
- **Proxy serves on port 80 inside container** — Traefik `server.port=80`.

## Details

- [UPSTREAM.md](UPSTREAM.md)
