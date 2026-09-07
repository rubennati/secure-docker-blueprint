# Seafile Pro

> **Backup and restore are untested** for this stack.

Cloud file storage with collaboration, search, and antivirus scanning.

## Services

| Service | Image | Purpose |
|---|---|---|
| seafile-pro-app | seafile-pro-mc | Main Seafile server |
| db | mariadb | Database |
| redis | redis | Cache/Sessions |
| seafile-pro-seadoc | sdoc-server | Collaborative document editing |
| seafile-pro-notification | notification-server | Real-time file change updates |
| md-server | seafile-md-server | File metadata management |
| seafile-pro-thumbnail | thumbnail-server | Image/video previews |
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
docker compose restart seafile-pro-app

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

OnlyOffice needs a server-to-server network path to Seafile's configured hostname (`APP_TRAEFIK_HOST`). This path can be public internet, Tailscale, or any direct route. If DNS for `APP_TRAEFIK_HOST` resolves to a Tailscale address on the OnlyOffice server, traffic routes via Tailscale automatically — no public internet exposure required.

**`APP_TRAEFIK_ACCESS` is a Traefik middleware setting, not a network exposure setting.** `acc-public` removes Traefik's source-IP allowlist; it does not bypass upstream firewalls. `acc-tailscale` enforces a source-IP allowlist but may reject Tailscale-routed traffic if Docker bridge masquerades the source IP before Traefik sees it — see `UPSTREAM.md` and `TROUBLESHOOTING.md §4.4` for the known caveat and investigation steps.

On the OnlyOffice server, add the Seafile domain to `ONLYOFFICE_ALLOWED_ORIGINS` so browsers can embed the editor in an iframe — see `core/onlyoffice/.env.example`. **Changes to `ONLYOFFICE_ALLOWED_ORIGINS` require container recreation** (`docker compose up -d --force-recreate` on the OnlyOffice server), not just restart — the value is baked into a Traefik label at container creation time.

## Passwords

Passwords are stored in `.env` (gitignored). Docker Secrets are not used because Seafile's init system (`my_init`) doesn't preserve exported environment variables. See UPSTREAM.md for the technical explanation.

## Config injection

`config/seahub_custom.py` is appended to `seahub_settings.py` **once** — on the container start after first boot creates the config files. After that initial injection, the marker prevents it from running again.

Settings that use `os.environ.get()` (OnlyOffice URL, SMTP host, etc.) are evaluated at Django startup on every restart, so changing those values in `.env` takes effect after `docker compose restart seafile-pro-app` — no re-injection needed.

Adding a brand-new setting that was absent from `seahub_custom.py` at injection time requires either editing `seahub_settings.py` directly in the volume, or removing the marker line (`# --- Blueprint custom settings ---`) and everything after it, updating `config/seahub_custom.py`, then restarting.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `seafile-pro-db` · **three databases**: `ccnet_db`, `seafile_db`, `seahub_db` · user `seafile` |
| **Password** | `SEAFILE_MYSQL_DB_PASSWORD` in `.env`. **This stack creates no `.secrets/` file** — see Passwords above — so the borgmatic snippet below needs one written for it: `printf '%s' "$SEAFILE_MYSQL_DB_PASSWORD" > .secrets/seafile_db_pwd.txt`. Borgmatic reads credentials from a file, a container, KeePassXC or systemd; there is no form that reads a `.env` entry directly |
| **State** | `./volumes/mysql` (databases) · **`./volumes/seafile-data`** — the file store · `./volumes/seadoc-data` |
| **Reproducible** | `./volumes/redis` (cache) · the Elasticsearch volume · `./volumes/seasearch-data` — both search indexes, rebuildable |
| **Quiescing** | Not needed for the dumps. Content-addressed blocks tolerate a mid-write copy. |

```yaml
mariadb_databases:
    - name: ccnet_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
    - name: seafile_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
    - name: seahub_db
      container: seafile-pro-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile-pro/.secrets/seafile_db_pwd.txt}"
```

**Three databases, not one** — `ccnet_db` for users and groups, `seafile_db` for
file metadata, `seahub_db` for the web layer and shares. Any one missing restores
to something that starts and does not work.

The two search indexes are excluded deliberately and cost a reindex after a
restore. Until it completes, search returns nothing while every file is present —
which looks like data loss and is not.

**Restore order:** databases first, then the block store, then the app, then
trigger the reindex.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Full setup guide, troubleshooting, upgrade checklist
- [docs/bugfixes/seafile-pro-2026-04-13.md](../../docs/bugfixes/seafile-pro-2026-04-13.md) — Known issues and fixes
