# Upstream Reference

## Source

- **LibrePhotos project:** https://www.librephotos.com/
- **GitHub:** https://github.com/LibrePhotos/librephotos
- **Docker Hub:** https://hub.docker.com/u/reallibrephotos
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** Community · no single company · no single jurisdiction
- **Domain:** Photos
- **Role:** Photo library with face recognition and search
- **Based on version:** `1.5.1` (upstream moved from weekly builds to semver)
- **Last checked:** 2026-04-17

## What we use

- Upstream `reallibrephotos/librephotos-proxy`, `librephotos-frontend`, `librephotos` (backend)
- `pgautoupgrade/pgautoupgrade:18.6-trixie` for Postgres (upstream runs `latest`, 18 on Alpine)
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
| **`shm_size: 256mb` on `db`** | Upstream's compose sets it from 1.5.0; with Docker's default 64 MB `/dev/shm`, large libraries fail with "could not resize shared memory segment" |
| **`UPDATE_CHECK: "false"` on the backend** | From 1.5.0 the backend asks GitHub daily for a newer release; pins move through this repository |
| **Access `access-public`, `limit-standard` and `headers-standard` defaults** | Wiki-style access; consider `access-vpn` for family-only galleries |

## Version / tag notes

- **Upstream moved from weekly build tags to semver.** The pin was `2026w25`, a dated
  weekly build. Releases now carry semver tags (`1.0.0`, `1.1.0`), so the comparison a
  sweep makes changes shape with this bump. Moved to `1.1.0` on 2026-09-13.
- Moved to `1.2.1` on 2026-10-04. The six advisories upstream has published — among them
  any authenticated user trashing, restoring, unpublishing or hiding another user's public
  photos — name `1.1.0` as the last affected version.
- `1.2.0` combines the first 100 database migrations. An installation on `2026w10` or
  later, every `1.x` included, upgrades directly; an older one starts `1.1.0` once first.
- The backend healthcheck calls upstream's liveness endpoint `/api/healthz` with the command
  from upstream's own compose file (`deploy/compose/docker-compose.e2e.yml`). The `1.2.x`
  backend image ships no `curl`.
- Moved to `1.5.1` on 2026-11-05 (released 2026-10-31), not run on a host at this
  tag; 1.3.0, 1.4.0 and 1.5.0 lie between. Backend, frontend and proxy share
  `APP_TAG` and all three exist at `1.5.1`. Changes:
  - 1.3.0: OpenCLIP ViT-B/32 replaces the separate tagging and CLIP models; a
    background job re-embeds and re-tags every photo once.
  - 1.4.0: `DEFAULT_FAVORITE_MIN_RATING` is no longer read (not set here); the
    log file is `librephotos.log`; the generated secret key moves to
    `protected_media/secret.key` (copy it back before going below 1.4.0); list
    endpoints of the API page by 100 with one envelope.
  - 1.5.0: PostgreSQL 15 or newer is required (`DB_TAG` is 16); the backend
    checks GitHub daily for a newer release (`UPDATE_CHECK`, off here); public
    links show only what **Settings > Public Sharing Defaults** allows; upstream's
    compose gives `db` 256 MB of `/dev/shm` (added here); Python 3.14 and
    Django 6.1; `reallibrephotos/librephotos-gpu` is no longer built (not used);
    API list endpoints drop the 1.4.0 pagination fields and `?size=`.
  - 1.5.1: SQLite repairs only; PostgreSQL installs are not affected.
  - Upstream's healthcheck moved to `/api/healthz/ready` with a 15-minute
    `start_period`; this stack keeps `/api/healthz`.

  After the upgrade: run `docker compose exec backend python manage.py
  strip_thumbnail_metadata` once — thumbnails made by 1.2.1 and older keep the
  original EXIF and XMP, GPS included, and public links serve them; open
  **Account menu > Admin Area** and let the **Finish the upgrade** card run its
  tasks; rescan the photos once (**Account menu > Library**, arrow next to
  **Scan** > **Rescan**). The first start takes longer than usual while data is
  repaired. Advisories fixed: GHSA-x465-w9j9-42rp (code execution through
  ExifTool), GHSA-cgq8-jvp9-r3j7, GHSA-cf3f-2fmg-mjj6, GHSA-j84j-mc98-7wq3,
  GHSA-xq77-cj4c-42qr (1.3.0); GHSA-f7vw-q3m9-4998 (1.4.0); public page and
  sharing fixes and Pillow 13 (1.5.0). Upstream lists GHSA-975v-mx44-9jxq,
  GHSA-6367-m327-c4pf and GHSA-hq2w-x39h-8wmp with no patched release.
- Moved `pgautoupgrade/pgautoupgrade` from `16-bookworm` to `18-trixie` on
  2026-11-05, not run on a host at this tag. LibrePhotos states no maximum;
  1.5.0 requires PostgreSQL 15 or newer, and upstream's compose
  (https://github.com/LibrePhotos/librephotos-docker) runs
  `pgautoupgrade/pgautoupgrade:latest`, which is PostgreSQL 18. 18 is built on
  Debian trixie only; there is no bookworm build. The mount stays
  `./volumes/db:/var/lib/postgresql`, the layout PostgreSQL 18 expects:
  pgautoupgrade looks for the old cluster in `/var/lib/postgresql/data`,
  upgrades it with `pg_upgrade --link` to `/var/lib/postgresql/18/docker` and
  removes the old cluster
  (https://github.com/pgautoupgrade/docker-pgautoupgrade). Check first where the
  16 cluster lives: the 16 image declares `VOLUME /var/lib/postgresql/data`, so
  under this mount the cluster can sit in an anonymous volume rather than in
  `./volumes/db/data` (`docker inspect` on the `db` container lists the mounts).
  If `./volumes/db/data` is empty, the 18 image starts an empty cluster. Take
  the `pg_dump` from the upgrade checklist before the tag changes in either
  case, and restore it into the new cluster if the upgrade does not find the
  data. Downgrade is only a restore of that dump.

## Upgrade checklist

LibrePhotos publishes semver releases (see Version / tag notes). Major DB upgrades are handled by `pgautoupgrade` on the next start.

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

6. Run the post-upgrade steps the release notes name (see Version / tag notes) and the **Finish the upgrade** card in the Admin Area
7. Verify: log in, browse timeline, run a face-recognition job, open the map view (if `MAPBOX_API_KEY` set)

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
