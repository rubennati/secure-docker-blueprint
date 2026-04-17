# Upstream Reference

## Source

- **LibrePhotos project:** https://www.librephotos.com/
- **GitHub:** https://github.com/LibrePhotos/librephotos
- **Docker Hub:** https://hub.docker.com/u/reallibrephotos
- **License:** MIT
- **Based on version:** `latest` weekly build (2026-04-17)
- **Last checked:** 2026-04-17

## What we use

- Upstream `reallibrephotos/librephotos-proxy`, `librephotos-frontend`, `librephotos` (backend)
- `pgautoupgrade/pgautoupgrade:16-bookworm` for Postgres (upstream default)
- Docker Secrets for Postgres password + inline duplicate for backend
- Bind-mount `./volumes/db`, `./volumes/protected_media`, `./volumes/logs`, `./volumes/cache`
- Configurable `SCAN_DIRECTORY` for photo source

## What we changed and why

| Change | Reason |
|--------|--------|
| **camelCase env vars → SCREAMING_SNAKE_CASE** — inbox used `dbUser`, `dbPass`, `scanDirectory`, `shhhhKey`, etc. | Blueprint convention; also fixes shell-escape hazards |
| **Default DB password `AaAa1234` replaced with Docker Secret + `DB_PWD_INLINE`** | Inbox hardcoded weak password; now generated + stored outside git |
| **Traefik labels instead of `ports: 3000:80`** on proxy | Blueprint routes via Traefik; also `httpPort=8024` in inbox `.env` removed (host-port leak not relevant behind Traefik) |
| **`CSRF_TRUSTED_ORIGINS` auto-derived from `APP_TRAEFIK_HOST`** | Inbox left it blank, which breaks Django admin behind a reverse proxy |
| **`app-internal` network (`internal: true`)** added | Isolate DB + backend + frontend from host; only proxy bridges to `proxy-public` |
| **`security_opt: no-new-privileges`** on all services | Baseline hardening |
| **Container names standardized** — `librephotos-proxy/backend/frontend/db` instead of bare `proxy/backend/frontend/db` | Project-scoped names avoid collision with other stacks |
| **`DB_TAG` / `APP_TAG` as variables** | Blueprint pinning convention |
| **`DEBUG=0` explicit** | Inbox had it inline; kept for clarity |
| **`data=` path renamed to individual bind mounts** (`./volumes/protected_media`, `./volumes/logs`, `./volumes/cache`, `./volumes/db`) | Inbox used a single `${data}` root variable that mixed DB and media; separating them makes backups and permissions cleaner |
| **Access `acc-public` + security `sec-2` defaults** | Wiki-style access; consider `acc-tailscale` for family-only galleries |

## Upgrade checklist

LibrePhotos publishes weekly builds under `latest`. Major DB upgrades are handled by `pgautoupgrade` on the next start.

1. Check [LibrePhotos releases](https://github.com/LibrePhotos/librephotos/releases)
2. Back up:
   ```bash
   docker compose exec -T db sh -c \
     'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' \
     > librephotos-db-$(date +%Y%m%d).sql
   tar czf librephotos-media-$(date +%Y%m%d).tgz volumes/protected_media/
   ```
3. Bump `APP_TAG` and/or `DB_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch for Django migrations and Postgres auto-upgrade output:
   ```bash
   docker compose logs --follow
   ```
6. Verify: log in, browse timeline, run a face-recognition job, open the map view (if `MAPBOX_API_KEY` set)

### Rollback

Restore DB dump and `volumes/protected_media/`, revert `APP_TAG`.
Note: once `pgautoupgrade` has upgraded the DB to a newer Postgres major, you cannot downgrade without the SQL dump.

## Useful commands

```bash
# Shell into the backend (for manage.py commands)
docker compose exec backend bash

# Django shell
docker compose exec backend python manage.py shell

# Trigger a full rescan
docker compose exec backend python manage.py scan

# Rebuild face-recognition index
docker compose exec backend python manage.py rebuild_face_embeddings

# Manual DB backup (pg_dump)
docker compose exec -T db sh -c \
  'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' > dump.sql

# Restore DB
cat dump.sql | docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Not imported from inbox

The inbox contained the full LibrePhotos source tree (backend/, frontend/, proxy/, k8s/, e2e/, etc.) cloned from upstream. Only the production `docker-compose.yml` + `.env` / `librephotos.env` files were needed for this deployment. Everything else (Dockerfiles for building from source, Kubernetes manifests, dev-container configs, GitHub workflows) is available in the upstream repository for anyone who wants to build from source instead of using the prebuilt images.
