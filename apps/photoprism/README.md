# PhotoPrism

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

AI-powered self-hosted photo manager with TensorFlow-based classification, face recognition, and location enrichment. Go-based server with MariaDB backend.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `photoprism/photoprism:latest` | Web UI + API + TensorFlow + WebDAV |
| `db` | `mariadb:11` | Primary store (index, albums, users, sidecar metadata) |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID, ORIGINALS_PATH, SITE_TITLE

# 2. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Generate ADMIN_PASSWORD (8-72 chars)
ADMIN_PWD_VAL=$(openssl rand -base64 24 | tr -d '\n')
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PWD_VAL}|" .env
echo "Initial admin password: ${ADMIN_PWD_VAL}"  # save this, then delete from .env after first login

# 5. Create volumes
mkdir -p volumes/database volumes/storage volumes/originals

# 6. Start
docker compose up -d

# 7. First run downloads TensorFlow models (~1 GB) — takes a few minutes
docker compose logs app --follow
# Watch for: "server started successfully"

# 8. Open UI and log in
# https://<APP_TRAEFIK_HOST>
# Credentials: ADMIN_USER / ADMIN_PASSWORD from .env
```

## Verify

```bash
docker compose ps                                    # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/api/v1/status  # 200 OK
```

## Security Model

- **`ADMIN_PASSWORD` only read on first startup** — remove from `.env` afterwards and rotate in the UI.
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **`PHOTOPRISM_DISABLE_TLS: "true"` + `DEFAULT_TLS: "false"`** — Traefik terminates TLS. PhotoPrism's internal TLS (part of `PHOTOPRISM_INIT: https`) was removed.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add` (CHOWN, SETUID, SETGID, DAC_OVERRIDE).
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside the app.
- **`PHOTOPRISM_UID` / `PHOTOPRISM_GID`** — app drops to these after init. Must match owner of `ORIGINALS_PATH`.
- **WebDAV is enabled by default** — Finder/iOS can mount `/originals` via `https://<HOST>/originals/`. Disable via `PHOTOPRISM_DISABLE_WEBDAV: "true"` if not needed.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run TensorFlow model download on slow links.
- **`DB_PWD_INLINE` duplicates the DB password** — PhotoPrism's `PHOTOPRISM_DATABASE_PASSWORD` env var has no `_FILE` support. MariaDB side uses `MARIADB_PASSWORD_FILE` from a Docker Secret; PhotoPrism needs the same value inline.
- **Memory** — PhotoPrism's indexer can spike to several GB when processing large RAW/video files. Provision at least 4 GB swap. Do not set memory limits or the indexer gets OOM-killed.
- **MariaDB seccomp/apparmor workaround** — upstream uses `seccomp:unconfined + apparmor:unconfined` due to an [io_uring bug with older kernels](https://github.com/MariaDB/mariadb-docker/issues/434). Left at defaults; uncomment the block in `docker-compose.yml` if MariaDB crashes.
- **Activation code** — PhotoPrism has a [membership program](https://www.photoprism.app/kb/activation) to unlock some features. Store any activation code in `.env` (gitignored) — never commit it.
- **`APP_TAG=latest` is not reproducible** — pin to a specific version for stable deployments. Use `photoprism/photoprism:preview` to test preview builds.
- **Ollama + Watchtower dropped** — the upstream compose included optional Ollama (vision LLM) and Watchtower (auto-update) profiles. Not imported here; add back if wanted.

## Details

- [UPSTREAM.md](UPSTREAM.md)
