# Invoice Ninja

Self-hosted invoicing, quotes, expenses, and time-tracking.

## Services

| Service | Image | Purpose |
|---|---|---|
| app | invoiceninja-debian | PHP-FPM + Supervisor (queue + scheduler) |
| nginx | nginx | Web server (FastCGI proxy to app) |
| mysql | mysql | Database |
| redis | redis | Cache/Queue/Sessions |

## Quick Start

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set HOST_DOMAIN, IN_USER_EMAIL

# 2. Generate passwords
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^IN_PASSWORD=.*|IN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
# Fix MYSQL_ references
DB_PWD=$(grep '^DB_PASSWORD=' .env | cut -d= -f2)
DB_ROOT=$(grep '^DB_ROOT_PASSWORD=' .env | cut -d= -f2)
sed -i "s|^MYSQL_PASSWORD=.*|MYSQL_PASSWORD=${DB_PWD}|" .env
sed -i "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=${DB_ROOT}|" .env

# 3. Start
docker compose up -d

# 4. Generate APP_KEY
docker compose run --rm app php artisan key:generate --show
# Copy to .env: APP_KEY=base64:...

# 5. Restart with key
docker compose down && docker compose up -d
```

## Verify

```bash
docker compose ps        # All healthy
curl -sI https://your-domain/  # 200 or 302
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upgrade checklist, known issues
