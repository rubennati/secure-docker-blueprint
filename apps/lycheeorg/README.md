# Lychee

**Status: 🚧 Draft**

Self-hosted photo gallery focused on fast browsing and clean presentation. Three-service stack: Laravel app, MariaDB backend, Redis cache.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `lycheeorg/lychee:v7` | PHP/Laravel app + Apache |
| `db` | `mariadb:11.4` | Primary store (albums, photo metadata, users) |
| `redis` | `redis:7-alpine` | Cache + session driver |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID

# 2. Generate Laravel APP_KEY (one-time)
APP_TAG=$(grep '^APP_TAG=' .env | cut -d= -f2)
docker run --rm lycheeorg/lychee:${APP_TAG} php artisan key:generate --show
# Copy the 'base64:...' output into APP_KEY in .env

# 3. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 4. Volume ownership (Lychee entrypoint drops to PUID/PGID)
mkdir -p volumes/{conf,uploads,sym,logs,tmp,mysql,redis}
sudo chown -R 1000:1000 volumes/conf volumes/uploads volumes/sym volumes/logs volumes/tmp

# 5. Start
docker compose up -d

# 6. Wait for first-run migrations (~60 seconds — note the STARTUP_DELAY=30)
docker compose logs app --follow
# Watch for: "Started Apache"

# 7. Open UI and create the admin account on first visit
# https://<APP_TRAEFIK_HOST>
# The first-visit wizard creates the admin user.
```

## Verify

```bash
docker compose ps                              # three services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **First-visit admin creation** — the first time the web UI is opened, Lychee prompts for admin credentials. Open it yourself immediately after `docker compose up -d` so an attacker cannot claim the account.
- **`APP_KEY`** encrypts Laravel sessions and signed URLs. Rotating invalidates all sessions (acceptable).
- **`DB_PASSWORD_FILE` is supported natively** — Lychee reads the password from `/run/secrets/DB_PWD`. No inline duplication needed.
- **`MYSQL_PASSWORD_FILE` + `MYSQL_ROOT_PASSWORD_FILE`** — MariaDB also reads secrets from files.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add` (CHOWN, SETUID, SETGID, DAC_OVERRIDE).
- **`no-new-privileges:true`** on all services.
- **Redis is `read_only: true` + tmpfs /tmp** — persistence via `/data` volume.
- **MariaDB + Redis on `app-internal` (`internal: true`)** — not reachable from outside the app.
- **`TRUSTED_PROXIES: "*"`** — required behind Traefik so Laravel trusts `X-Forwarded-*` headers.

## Known Issues

- **Image tag `v6` does not exist** — Lychee is on v7. The correct tag is in `.env.example` (`APP_TAG=v7.x.x`). The `key:generate` command reads the tag from `.env`, not hardcoded.
- **`STARTUP_DELAY=30`** — Lychee waits 30 s for MariaDB before starting. Leave as-is unless your DB is unusually slow.
- **WebAuthn is enabled by default** — disable via `DISABLE_WEBAUTHN=true` if you do not want passkey support.
- **Redis password is not configured here** — Redis runs on the internal network only. If you expose it or move it off-host, add a password.

## Details

- [UPSTREAM.md](UPSTREAM.md)
