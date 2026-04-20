# Immich

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Self-hosted photo and video backup with machine-learning–based search, facial recognition, and mobile apps for iOS/Android. Four-service stack: web server, ML worker, Postgres (with pgvectors/vectorchord extensions for embeddings), and Valkey (Redis-compatible).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/immich-app/immich-server:v2` | Web UI + REST API + upload handler |
| `machine-learning` | `ghcr.io/immich-app/immich-machine-learning:v2` | CLIP embeddings, face detection, object recognition |
| `db` | `ghcr.io/immich-app/postgres:14-vectorchord…` | Postgres with vector extensions for similarity search |
| `redis` | `valkey/valkey:8` | Background job queue (Bull/BullMQ) |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, UPLOAD_LOCATION

# 2. Generate DB secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '/+=\n' > .secrets/db_pwd.txt
# Immich restricts DB_PASSWORD to [A-Za-z0-9] — no special chars.
# The tr above strips +/= produced by base64.

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Create volume directories
mkdir -p volumes/postgres volumes/redis volumes/model-cache volumes/library

# 5. Start
docker compose up -d

# 6. Wait for first-run migrations (~2 minutes)
docker compose logs app --follow
# Watch for: "Immich Server is listening on..."

# 7. Open UI and create the admin account
# https://<APP_TRAEFIK_HOST>
# First user to sign up becomes admin.
```

## Verify

```bash
docker compose ps                              # all four services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/api/server/ping   # 200 OK, {"res":"pong"}
```

## Security Model

- **First-user-wins admin** — the first registered account becomes admin. Register immediately after start so an attacker cannot claim it.
- **`DB_PASSWORD` restricted to `[A-Za-z0-9]`** — Immich does not support special characters in the DB password. Keep generation aligned (see Setup step 2).
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **Postgres on `app-internal` (`internal: true`)** — only the Immich services can reach it.
- **`no-new-privileges:true`** on all services.
- **Redis is `read_only: true` + tmpfs** — persistence via `/data` volume only.
- **ML container** — downloads models to `./volumes/model-cache/` on first use (~2-3 GB).

## Known Issues

- **Live-tested: no.** Expect minor surprises around first-run permissions and ML model download.
- **`DB_PWD_INLINE` duplicates the DB password** — Immich-server's `DB_PASSWORD` env var has no `_FILE` support. The Postgres service reads `POSTGRES_PASSWORD_FILE` from a Docker Secret, but immich-server needs the same value inline in `.env`. Setup step 3 syncs them. Mismatch = connection refused.
- **Custom Postgres image is required** — the vector extensions (pgvectors, vectorchord) used for photo similarity search are Immich-specific. Do NOT substitute a stock `postgres:14` image.
- **Upload volume** — `UPLOAD_LOCATION` can be an NFS/SMB share. The `db` volume must be local storage (Postgres corrupts on network filesystems).
- **Hardware acceleration** — transcoding and ML inference can use GPU/NPU. See [Immich hwaccel docs](https://docs.immich.app/features/ml-hardware-acceleration) — add the `extends:` block and change the image tag (e.g. `v2-cuda`).
- **First ML inference is slow** — CLIP model downloads on first photo upload (~5-10 min on slow links).

## Details

- [UPSTREAM.md](UPSTREAM.md)
