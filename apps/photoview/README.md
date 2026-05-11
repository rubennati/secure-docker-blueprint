# Photoview

**Status: ✅ Ready — v2.4.0 · 2026-05-11**

Self-hosted photo gallery focused on RAW processing, EXIF-driven organization, and face recognition. Go-based server with MariaDB backend.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `photoview/photoview:2.4.0` | Web UI + GraphQL API + media indexer |
| `db` | `mariadb:11.4` | Index, albums, users, face data |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, MEDIA_ROOT
# MEDIA_ROOT is the host path to your photo library. Examples:
#   MEDIA_ROOT=./volumes/photos          # local subfolder (create it first)
#   MEDIA_ROOT=/mnt/nas/photos           # NAS/external mount
# The folder is mounted read-only into the container at /photos.

# 2. Generate DB secrets (alphanumeric only — DSN-safe)
mkdir -p .secrets
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/db_root_pwd.txt

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Create cache volume and fix ownership
mkdir -p volumes/media-cache volumes/mariadb
# Photoview runs as uid/gid 999 ('photoview') inside the container.
# The media-cache directory must be owned by that uid.
sudo chown -R 999:999 volumes/media-cache

# 5. Start
docker compose up -d

# 6. Wait for MariaDB init + Photoview bootstrap (~60 seconds)
docker compose logs app --follow
# Watch for: "Photoview API endpoint listening at http://0.0.0.0:80/api"

# 7. Open UI and complete the initial setup wizard
# https://<APP_TRAEFIK_HOST>
# Username / Password: choose your admin credentials
# Photo Path: /photos   ← always this value (container-internal mount point)
# Then go to Settings → Scan and trigger the first scan.
```

## Verify

```bash
docker compose ps                              # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **First-visit admin creation** — the setup wizard creates the admin user on first load. Open the UI yourself immediately after start so an attacker cannot claim it.
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **DB password restricted to `[A-Za-z0-9]`** — Photoview builds the DSN inline; `@`, `:`, `/`, `?`, `#` break parsing. Setup step 2 uses `openssl rand -hex` which is DSN-safe.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **Media library bind-mounted read-only** (`${MEDIA_ROOT}:/photos:ro`) — Photoview cannot modify originals.

## Known Issues

- **`DB_PWD_INLINE` duplicates the DB password** — Photoview's `PHOTOVIEW_MYSQL_URL` is a full DSN with the password embedded. The MariaDB service reads `MARIADB_PASSWORD_FILE` from a Docker Secret; Photoview needs the same value inline. Mismatch = connection refused.
- **Service worker MIME type error in browser console** — Photoview's `service-worker.js` returns `text/html` behind a reverse proxy (known upstream issue). The app works despite this; offline/PWA features are non-functional.
- **Manifest SVG icon warning** — Chrome cannot use an SVG as a PWA icon; cosmetic only.
- **Upstream `photoview-prepare` service dropped** — it ran `chown -R photoview:photoview` on the media-cache folder. Setup step 4 replicates this with `chown 999:999` — the `photoview` user inside the image has uid/gid 999, not 1000.
- **SQLite and PostgreSQL drivers are not wired up here** — upstream compose supported three backends. Only MySQL/MariaDB is imported. To switch, see upstream `docker-compose.yml` for `PHOTOVIEW_SQLITE_PATH` / `PHOTOVIEW_POSTGRES_URL`.
- **Watchtower dropped** — blueprint policy: explicit `APP_TAG` bumps.
- **Hardware transcoding requires device passthrough** — uncomment the `devices:` block in `docker-compose.yml` if using `qsv`/`vaapi`/`nvenc`.

## Details

- [UPSTREAM.md](UPSTREAM.md)
