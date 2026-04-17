# Photoview

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Self-hosted photo gallery focused on RAW processing, EXIF-driven organization, and face recognition. Go-based server with MariaDB backend.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `photoview/photoview:2` | Web UI + GraphQL API + media indexer |
| `db` | `mariadb:lts` | Index, albums, users, face data |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, MEDIA_ROOT

# 2. Generate DB secrets (alphanumeric only — DSN-safe)
mkdir -p .secrets
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/db_root_pwd.txt

# 3. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Create cache volume
mkdir -p volumes/media-cache volumes/mariadb
# Photoview runs as UID 1000 internally. Ensure the cache is writable.
sudo chown -R 1000:1000 volumes/media-cache

# 5. Start
docker compose up -d

# 6. Wait for MariaDB init + Photoview bootstrap (~60 seconds)
docker compose logs app --follow
# Watch for: "Photoview is listening on :80"

# 7. Open UI and complete the initial setup wizard
# https://<APP_TRAEFIK_HOST>
# Set root media path to /photos, create the admin account.
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

- **Live-tested: no.** Expect minor surprises, especially first-run MariaDB ownership.
- **`DB_PWD_INLINE` duplicates the DB password** — Photoview's `PHOTOVIEW_MYSQL_URL` is a full DSN with the password embedded. The MariaDB service reads `MARIADB_PASSWORD_FILE` from a Docker Secret; Photoview needs the same value inline. Mismatch = connection refused.
- **`APP_TAG=2` tracks the 2.x line** — no minor-version pin; breaking changes can arrive on a rebuild. Pin a specific release for reproducibility.
- **Upstream `photoview-prepare` service dropped** — it ran `chown` on the media-cache folder. Setup step 4 does the same thing once; simpler than keeping a one-shot service.
- **SQLite and PostgreSQL drivers are not wired up here** — upstream compose supported three backends. Only MySQL/MariaDB is imported. To switch, see upstream `docker-compose.yml` for `PHOTOVIEW_SQLITE_PATH` / `PHOTOVIEW_POSTGRES_URL`.
- **Watchtower dropped** — blueprint policy: explicit `APP_TAG` bumps.
- **Hardware transcoding requires device passthrough** — uncomment the `devices:` block in `docker-compose.yml` if using `qsv`/`vaapi`/`nvenc`.

## Details

- [UPSTREAM.md](UPSTREAM.md)
