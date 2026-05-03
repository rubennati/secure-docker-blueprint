# Upstream Reference

## Source

- **PhotoPrism project:** https://www.photoprism.app/
- **GitHub:** https://github.com/photoprism/photoprism
- **Docker Hub:** https://hub.docker.com/r/photoprism/photoprism
- **Compose docs:** https://docs.photoprism.app/getting-started/docker-compose/
- **License:** AGPL-3.0
- **Origin:** Germany · PhotoPrism AG · EU
- **Based on version:** `latest`
- **Last checked:** 2026-04-17

## What we use

- Upstream `photoprism/photoprism`
- Official `mariadb:11` as backend
- Docker Secrets for MariaDB password + root password
- Bind-mount `./volumes/database`, `./volumes/storage`
- Configurable `ORIGINALS_PATH` for photo source

## What we changed and why

| Change | Reason |
|--------|--------|
| **Real IP + hardcoded admin password removed** — inbox had an RFC1918 URL in `PHOTOPRISM_SITE_URL` and `PHOTOPRISM_ADMIN_PASSWORD="admin"` | Prevent leak; now `https://${APP_TRAEFIK_HOST}/` + generated admin password via `.env` |
| **`insecure` DB passwords replaced** — inbox had `PHOTOPRISM_DATABASE_PASSWORD`, `MARIADB_PASSWORD`, `MARIADB_ROOT_PASSWORD` all set to `"insecure"` | Now Docker Secrets (`.secrets/db_pwd.txt`, `.secrets/db_root_pwd.txt`) + `DB_PWD_INLINE` duplicate for PhotoPrism |
| **Traefik labels instead of `ports: 8009:2342`** | Blueprint routes via Traefik |
| **`PHOTOPRISM_DISABLE_TLS=true` + `DEFAULT_TLS=false`** | Traefik terminates TLS; PhotoPrism's internal HTTPS stack not needed |
| **`PHOTOPRISM_INIT: "tensorflow"`** — dropped `https` | Init used to download a Let's Encrypt cert for internal TLS — not needed behind Traefik |
| **`security_opt: seccomp:unconfined + apparmor:unconfined` → `no-new-privileges:true`** on app | The unconfined profile was upstream-specific to an old MariaDB issue, not PhotoPrism itself. Kept as commented fallback on DB service only |
| **`cap_drop: ALL` + minimal `cap_add` on MariaDB** | Baseline hardening |
| **`app-internal` network (`internal: true`)** | Isolate DB from host |
| **Ollama service dropped** | Upstream opt-in profile for vision-LLM captioning. Not imported; add back if needed |
| **Watchtower service dropped** | Blueprint policy: explicit `APP_TAG` bump + `docker compose pull`, no auto-updates |
| **`ADMIN_USER / ADMIN_PASSWORD` via `.env`** | Inbox hardcoded both; now configurable + documented as only read on first boot |
| **Site metadata as variables** (`SITE_TITLE`, `SITE_CAPTION`, `DEFAULT_LOCALE`, `PLACES_LOCALE`) | Inbox hardcoded "PhotoPrism / AI-Powered Photos App / en / local" |
| **`PUID` / `PGID`** wired to `PHOTOPRISM_UID / GID` | Inbox had both commented out — app ran as root |
| **Container names standardized** — `photoprism-app/db` | Project-scoped naming |
| **Volume paths** — inbox used `./Pictures`, `./storage`, `./database` | Now `${ORIGINALS_PATH}` (default `./volumes/originals`), `./volumes/storage`, `./volumes/database` |
| **Access `acc-public` + security `sec-2` defaults** | Consider `acc-tailscale + sec-3` for family-only galleries |

## Upgrade checklist

1. Check [PhotoPrism release notes](https://docs.photoprism.app/release-notes/) — PhotoPrism ships frequent breaking changes on `latest`
2. Back up:
   ```bash
   # DB dump
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism' \
     > photoprism-db-$(date +%Y%m%d).sql
   # Storage (sidecars, cache, settings)
   tar czf photoprism-storage-$(date +%Y%m%d).tgz volumes/storage/
   ```
3. Bump `APP_TAG` in `.env` (consider pinning to a dated tag)
4. `docker compose pull && docker compose up -d`
5. Watch logs:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: log in, browse library, trigger a rescan, confirm face-recognition still works

### Rollback

Restore DB dump and `volumes/storage/`, revert `APP_TAG`.

## Useful commands

```bash
# Shell into the app
docker compose exec app bash

# CLI — index originals
docker compose exec app photoprism index

# CLI — import a folder into originals
docker compose exec app photoprism import /photoprism/import

# CLI — reset password for a user
docker compose exec app photoprism users reset-password <username>

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'mariadb -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" photoprism'
```

## Optional profiles (not included)

The upstream compose included two optional service profiles worth mentioning:

- **Ollama** — runs a local vision LLM for photo captioning via the `PHOTOPRISM_VISION_*` options. Requires a GPU for reasonable performance. Add back with `profiles: ["ollama"]` on an `ollama/ollama:latest` service and set `PHOTOPRISM_VISION_URI` / `PHOTOPRISM_VISION_KEY`.
- **Watchtower** — auto-updates PhotoPrism on a schedule. Blueprint policy avoids this; prefer explicit `APP_TAG` bumps with a backup step.
