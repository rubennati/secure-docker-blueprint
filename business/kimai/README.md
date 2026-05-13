# Kimai

**Status: ✅ Ready — v2.56.0 · 2026-05-11**

Self-hosted time-tracking for freelancers and small teams. Project/customer hierarchy, timesheet approval, invoicing via plugins, REST API. PHP/Symfony app with MariaDB.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `kimai/kimai2:apache-2.56.0` | PHP/Symfony + Apache + cron |
| `db` | `mariadb:11.4` | Timesheets, users, customers, projects |

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, ADMIN_EMAIL

mkdir -p .secrets volumes/mysql volumes/data volumes/plugins

# DSN-safe passwords
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -hex 32 > .secrets/db_root_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# App secret
sed -i "s|^APP_SECRET=.*|APP_SECRET=$(openssl rand -hex 32)|" .env

# Admin password
ADMIN_PWD=$(openssl rand -base64 16 | tr -d '\n')
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PWD}|" .env
echo "Admin password: ${ADMIN_PWD}"

docker compose up -d
docker compose logs app --follow
# Watch for: "Kimai is ready" then "apache2 -D FOREGROUND"

# https://<APP_TRAEFIK_HOST>
# Log in with ADMIN_EMAIL / ADMIN_PASSWORD
```

## Security Model

- **`ADMIN_PASSWORD` only read on first boot** — change in the UI, remove from `.env`.
- **`DB_PWD_INLINE` duplicates the DB password** — Kimai's `DATABASE_URL` is inline DSN, no `_FILE` support.
- **DSN-safe password** — `@`, `:`, `/`, `?`, `#` break parsing. `openssl rand -hex` is safe.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add`.
- **`no-new-privileges:true`** on both services.
- **Default access `acc-tailscale` + `sec-3`** — Kimai holds customer, project, and billing data. VPN-only default.

## Known Issues

- **Healthcheck uses `Host` header override** — the image's built-in healthcheck hits `127.0.0.1:8001` with `Host: 127.0.0.1`, which Symfony rejects as untrusted. The compose healthcheck is overridden to pass `Host: APP_TRAEFIK_HOST` instead.
- **`APP_TAG` uses `apache-X.Y.Z` format** — Kimai images are tagged `apache-2.56.0`, `fpm-2.56.0`, etc. Update `APP_TAG` in `.env.example` on upgrades.
- **Plugins** land in `volumes/plugins/` as extracted archives. Back up together with the DB dump.
- **Invoice plugin** ships separately — requires installation via UI after first boot.

## Integration with Invoice Ninja

Kimai exports timesheets as CSV/JSON per project. Typical flow:
1. Team tracks time in Kimai
2. End of month: Admin → Export → Invoice Ninja
3. Invoice Ninja generates the actual invoice

Via n8n for automation:
- Kimai webhook (Admin → Webhooks) → n8n → Invoice Ninja API
