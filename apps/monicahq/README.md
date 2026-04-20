# Monica

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Monica is a personal CRM — remember everything about your friends, family, and business contacts. Built on Laravel (PHP) with a MariaDB backend.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `monica:5-apache` | Laravel app + Apache + PHP |
| `db` | `mariadb:11.4` | Primary store (contacts, relationships, activities, journal) |

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate Laravel APP_KEY (one-time)
docker run --rm monica:5-apache php artisan key:generate --show
# Copy the 'base64:...' output into APP_KEY in .env

# 3. Generate DB secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt

# 4. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 5. Create volumes
mkdir -p volumes/mysql volumes/data

# 6. Start
docker compose up -d

# 7. Wait for first-run migrations (~60 seconds)
docker compose logs app --follow
# Watch for: "apache2 -D FOREGROUND"

# 8. Open UI and register the first account (it becomes admin)
# https://<APP_TRAEFIK_HOST>
```

## Verify

```bash
docker compose ps                              # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **First-user-wins admin** — open the UI and sign up immediately after start.
- **`APP_KEY`** encrypts sessions and password-reset tokens. Rotating invalidates all logins (acceptable).
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **`APP_TRUSTED_PROXIES: "*"`** — required so Laravel honours `X-Forwarded-Proto=https` from Traefik (otherwise Monica generates `http://` absolute URLs).
- **MariaDB `MYSQL_RANDOM_ROOT_PASSWORD=true`** — no root password is stored. Root access is only possible while the container is running.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **MariaDB on `app-internal` (`internal: true`)** — not reachable from outside.
- **Default access `acc-tailscale` + `sec-3`** — Monica holds very personal data (contacts, health, journal). VPN-only is a safer default than public.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run permissions on `volumes/data/`.
- **`DB_PWD_INLINE` duplicates the DB password** — Monica's Laravel config reads `DB_PASSWORD` from env only. MariaDB side uses `MYSQL_PASSWORD_FILE`; Monica needs the same value inline.
- **`MYSQL_RANDOM_ROOT_PASSWORD`** — if you need to run maintenance as `root`, exec a shell while the container is up and read `/tmp/mariadb-root-password` or dump via a user with sufficient grants.
- **2FA, reminders, SMTP** — not configured here. Enable in the UI or add `MAIL_*` env vars.

## Details

- [UPSTREAM.md](UPSTREAM.md)
