# BookStack

> **Status: ✅ Ready** — v25.02 · 2026-05-03

Self-hosted wiki / knowledge base. Three-level structure: Shelves → Books → Chapters → Pages. Built on Laravel (PHP) with a MariaDB backend.

## Architecture

Two services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `lscr.io/linuxserver/bookstack:version-v25.02` | BookStack web app (LSIO build with Apache + PHP 8) |
| `db` | `mariadb:11.4` | Primary data store (pages, users, revisions, attachments metadata) |

Attachments and images live in `./volumes/config/www/uploads/` (inside the LSIO `/config` mount).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID

# 2. Generate Laravel APP_KEY (one-time)
docker run --rm --entrypoint /bin/bash lscr.io/linuxserver/bookstack:version-v25.02 appkey
# Copy the 'base64:...' output into APP_KEY in .env

# 3. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 4. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 5. Volume ownership (LSIO image drops to PUID/PGID)
mkdir -p volumes/config volumes/mysql
sudo chown -R 1000:1000 volumes/config

# 6. Start
docker compose up -d

# 7. Wait for first-run migrations
docker compose logs app --follow
# Watch for: "Starting Apache web server"

# 8. Open UI and log in with default credentials
# https://<APP_TRAEFIK_HOST>
# Default: admin@admin.com / password — CHANGE IMMEDIATELY
```

## Verify

```bash
docker compose ps                              # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/login    # 200 OK
```

## Security Model

- **Default admin credentials must be changed on first login** — BookStack ships with `admin@admin.com` / `password`. Change in the UI immediately after setup.
- **`APP_KEY`** encrypts sessions and password-reset tokens. Rotating invalidates all existing sessions (acceptable).
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **MariaDB is on `app-internal` (`internal: true`)** — not reachable from outside the app.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add` (CHOWN, SETUID, SETGID, DAC_OVERRIDE).
- **`no-new-privileges:true`** on both services.
- **LSIO s6-overlay** — container starts as root for init, drops to PUID/PGID. Do **not** set `user:` (would break s6).

## Known Issues

- **`DB_PWD_INLINE` duplicates the DB password** — BookStack's `DB_PASSWORD` env var has no `_FILE` support. The DB service reads `MYSQL_PASSWORD_FILE` from a Docker Secret (`.secrets/db_pwd.txt`), but BookStack needs the same value inline in `.env`. Setup step 4 syncs them. Mismatch = BookStack can't connect to DB.
- **First boot is slow** — Laravel migrations run on first start (~60-90 seconds). Second start is fast.
- **Upstream LSIO tag format** — `version-vXX.XX` tracks BookStack's semver (e.g. `v25.02` = BookStack 25.02). Alternatively `latest` for rolling updates (not recommended for reproducibility).

## Details

- [UPSTREAM.md](UPSTREAM.md)
