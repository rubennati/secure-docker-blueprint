# Seafile Pro

Cloud file storage with collaboration, search, and antivirus scanning.

## Services

| Service | Image | Purpose |
|---|---|---|
| app | seafile-pro-mc | Main Seafile server |
| db | mariadb | Database |
| redis | redis | Cache/Sessions |
| seadoc | sdoc-server | Collaborative document editing |
| notification-server | notification-server | Real-time file change updates |
| md-server | seafile-md-server | File metadata management |
| thumbnail-server | thumbnail-server | Image/video previews |
| seasearch | seasearch | Full-text search |
| clamav | clamav | Antivirus scanning |

## Quick Start

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set domain, admin email, etc.

# 2. Generate passwords
sed -i "s|^INIT_SEAFILE_MYSQL_ROOT_PASSWORD=.*|INIT_SEAFILE_MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^SEAFILE_MYSQL_DB_PASSWORD=.*|SEAFILE_MYSQL_DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^INIT_SEAFILE_ADMIN_PASSWORD=.*|INIT_SEAFILE_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^JWT_PRIVATE_KEY=.*|JWT_PRIVATE_KEY=$(openssl rand -base64 48 | tr -d '\n')|" .env
sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^ONLYOFFICE_JWT_SECRET=.*|ONLYOFFICE_JWT_SECRET=$(cat /path/to/core/onlyoffice/.secrets/jwt_secret.txt)|" .env

# 3. Start
docker compose up -d

# 4. Wait for healthy, then inject configs
docker compose restart app

# 5. Build search index
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update
```

## Verify

```bash
docker compose ps                                          # All services up
docker exec seafile-pro-app grep "SEASEARCH" /shared/seafile/conf/seafevents.conf  # Search configured
docker exec seafile-pro-app grep "virus_scan" /shared/seafile/conf/seafile.conf    # Antivirus configured
curl -s https://your-domain/notification/ping              # {"ret": "pong"}
```

## Features requiring acc-public

OnlyOffice integration requires `APP_TRAEFIK_ACCESS=acc-public` because OnlyOffice calls back to Seafile via the public domain.

## Passwords

Passwords are stored in `.env` (gitignored). Docker Secrets are not used because Seafile's init system (`my_init`) doesn't preserve exported environment variables.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Full setup guide, troubleshooting, upgrade checklist
- [docs/bugfixes/seafile-pro-2026-04-13.md](../../docs/bugfixes/seafile-pro-2026-04-13.md) — Known issues and fixes
