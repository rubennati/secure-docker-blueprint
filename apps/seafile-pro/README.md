# Seafile Pro

> **Status: ✅ Ready** — v13.0 · 2026-04-13

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
nano .env  # Set APP_TRAEFIK_HOST, SEAFILE_ADMIN_EMAIL, ONLYOFFICE_HOST, TZ

# 2. Generate passwords
sed -i "s|^INIT_SEAFILE_MYSQL_ROOT_PASSWORD=.*|INIT_SEAFILE_MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^SEAFILE_MYSQL_DB_PASSWORD=.*|SEAFILE_MYSQL_DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^INIT_SEAFILE_ADMIN_PASSWORD=.*|INIT_SEAFILE_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^JWT_PRIVATE_KEY=.*|JWT_PRIVATE_KEY=$(openssl rand -base64 48 | tr -d '\n')|" .env
sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$(openssl rand -hex 32)|" .env
# OnlyOffice JWT secret — copy from the OnlyOffice server (must match exactly):
#   sed -i "s|^ONLYOFFICE_JWT_SECRET=.*|ONLYOFFICE_JWT_SECRET=<paste-value>|" .env

# 3. Pull images
docker compose pull

# 4. Start
docker compose up -d

# 5. Wait for app healthy (first boot initialises databases — takes ~3 min)
docker compose ps

# 6. Inject Blueprint configs (runs once — see Passwords section)
docker compose restart app

# 7. Build search index
docker exec seafile-pro-app /opt/seafile/seafile-server-latest/pro/pro.py search --update
```

## Verify

```bash
docker compose ps                                          # All services up
docker exec seafile-pro-app grep "SEASEARCH" /shared/seafile/conf/seafevents.conf  # Search configured
docker exec seafile-pro-app grep "virus_scan" /shared/seafile/conf/seafile.conf    # Antivirus configured
curl -s https://your-domain/notification/ping              # {"ret": "pong"}
```

## OnlyOffice

OnlyOffice integration requires the OnlyOffice server to be able to reach Seafile's public URL to fetch and save documents. If Seafile is access-restricted (e.g. Tailscale-only), the OnlyOffice server must also be reachable on the same network or have a direct path to Seafile.

On the OnlyOffice server, add the Seafile domain to `ONLYOFFICE_ALLOWED_ORIGINS` so browsers can embed the editor in an iframe. See `core/onlyoffice/.env.example`.

## Passwords

Passwords are stored in `.env` (gitignored). Docker Secrets are not used because Seafile's init system (`my_init`) doesn't preserve exported environment variables. See UPSTREAM.md for the technical explanation.

## Config injection

`config/seahub_custom.py` is appended to `seahub_settings.py` **once** — on the container start after first boot creates the config files. After that initial injection, the marker prevents it from running again.

Settings that use `os.environ.get()` (OnlyOffice URL, SMTP host, etc.) are evaluated at Django startup on every restart, so changing those values in `.env` takes effect after `docker compose restart app` — no re-injection needed.

Adding a brand-new setting that was absent from `seahub_custom.py` at injection time requires either editing `seahub_settings.py` directly in the volume, or removing the marker line (`# --- Blueprint custom settings ---`) and everything after it, updating `config/seahub_custom.py`, then restarting.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Full setup guide, troubleshooting, upgrade checklist
- [docs/bugfixes/seafile-pro-2026-04-13.md](../../docs/bugfixes/seafile-pro-2026-04-13.md) — Known issues and fixes
