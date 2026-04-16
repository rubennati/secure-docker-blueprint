# Seafile

Self-hosted file sync + team collaboration server. This setup runs Seafile Community Edition 13 as a **multi-container stack**, split across five compose files so optional components can be toggled on or off without touching the core.

## Architecture

Seafile 13 is a collection of cooperating services, not a single container. The main server (`seafile`) is mandatory; everything else is optional and picked via the `COMPOSE_FILE` variable in `.env`.

| File | Services | Required? | Purpose |
|------|----------|-----------|---------|
| `seafile-server.yml` | `db`, `memcached`, `redis`, `seafile` | Yes | Core server + its backing services |
| `seadoc.yml` | `seadoc` | Optional | Collaborative document editor (sdoc files) |
| `notification-server.yml` | `notification-server` | Optional | Push notifications for file changes |
| `md-server.yml` | `seafile-md-server` | Optional | File metadata / extended properties |
| `thumbnail-server.yml` | `thumbnail-server` | Optional | Image and video thumbnails |

### Why split into five files

`docker compose` merges files passed via `COMPOSE_FILE` into one effective config. Each YAML is responsible for one feature and redeclares only the shared networks/secrets it actually uses. Disabling a component = remove its filename from `COMPOSE_FILE`, run `docker compose up -d`, done.

### Traefik routing

Multiple services are exposed under the same host:

- `/` → `seafile` (main UI + API)
- `/socket.io/` → `seadoc` (real-time collaboration)
- `/sdoc-server` → `seadoc` (sdoc API, prefix stripped)
- `/notification` → `notification-server` (WebSocket push)
- `/thumbnail` → `thumbnail-server`

All routers share `APP_TRAEFIK_HOST`. OnlyOffice is _not_ routed through here — it has its own domain (`ONLYOFFICE_HOST`).

### Secret handling

Seafile's init scripts (`utils.py`, `bootstrap.py`, Go binaries) don't consistently support the `_FILE` suffix. Instead, every service is started through a shared wrapper:

```
config/entrypoint.sh  →  read /run/secrets/*  →  export as env vars  →  exec original command
```

The same `entrypoint.sh` is mounted into every Seafile service. Each secret export is conditional (`[ -f ... ] &&`), so services only see the secrets they actually need. The wrapper also appends `seahub_custom.py` to Seafile's auto-generated `seahub_settings.py` once per installation.

Full details: [config/README.md](config/README.md).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, SEAFILE_ADMIN_EMAIL, ONLYOFFICE_HOST, TIMEZONE

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/seafile_db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/seafile_admin_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/redis_pwd.txt

# 3. If you use OnlyOffice, reuse its JWT secret
cp ../../core/onlyoffice/.secrets/jwt_secret.txt .secrets/onlyoffice_jwt_secret.txt

# 4. Start
docker compose up -d

# 5. First startup takes 2–4 minutes (DB init, Django migrations)
docker compose logs seafile --follow
# Wait for: "Seafile server started" and Seahub to come up

# 6. Open the UI and log in as SEAFILE_ADMIN_EMAIL
# Password is the value in .secrets/seafile_admin_pwd.txt
```

### Turning components off

```bash
# In .env, remove the files you don't want:
COMPOSE_FILE=seafile-server.yml,thumbnail-server.yml
# Then:
docker compose up -d --remove-orphans
```

## Verify

```bash
docker compose ps                           # All configured services Up
docker compose logs seafile --tail 100      # Django + FastCGI started
docker compose logs db --tail 20            # MariaDB ready for connections
curl -fsSI https://<APP_TRAEFIK_HOST>/      # 302 to /accounts/login/
```

Test SeaDoc (if enabled):

```bash
curl -fsSI https://<APP_TRAEFIK_HOST>/sdoc-server/
```

Test notification-server (if enabled):

```bash
curl -fsSI https://<APP_TRAEFIK_HOST>/notification/
```

## Security Model

- Database, Redis, and Memcached are only on `app-internal` (which is `internal: true`). None of them can reach the outside network directly.
- The `seafile` main container is on both `proxy-public` (for Traefik) and `app-internal` (for DB + Redis). The optional web-facing services (`seadoc`, `notification-server`, `thumbnail-server`) follow the same pattern.
- All secrets are Docker Secrets under `./.secrets/`. The wrapper entrypoint converts them to env vars inside the container — they never land in `.env`.
- `no-new-privileges:true` on every service.

## Known Issues

- **First boot is slow** (2–4 min). The main server's healthcheck uses `start_period: 180s` for this reason.
- **SeaDoc + Notification server images are tagged `:13.0-latest` / `:2.0-latest`.** These are moving tags; pin to a concrete digest in production if you want reproducible builds.
- **`seahub_custom.py` is appended only once.** If you change it after the first successful boot, the old block stays in `seahub_settings.py`. The procedure to re-inject is in [config/README.md](config/README.md).
- **Env var naming is inconsistent with the rest of the repo.** `.env.example` still uses `APP_IMAGE=…:tag` (not split into `*_TAG`) and `TIMEZONE` (not `TZ`). Unifying this would touch all five YAMLs simultaneously — left for a dedicated refactor with testing, not mixed into a documentation pass.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, version notes
- [config/README.md](config/README.md) — entrypoint wrapper mechanics and `seahub_custom.py` injection
