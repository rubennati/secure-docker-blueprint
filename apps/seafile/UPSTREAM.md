# Upstream Reference

## Source

- **Docs:** https://manual.seafile.com/13.0/docker/
- **Deploy manual (CE):** https://manual.seafile.com/13.0/docker/deploy_seafile_ce_with_docker/
- **Image (main):** https://hub.docker.com/r/seafileltd/seafile-mc
- **GitHub:** https://github.com/haiwen/seafile
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** China · Seafile Ltd · non-EU
- **Domain:** Files, wiki and collaboration
- **Role:** File sync and share, community edition
- **Note:** Chinese company: data stored on self-hosted instances is under your jurisdiction, but the vendor is subject to Chinese law.
- **Based on version:** Seafile CE `13.0.29` (multi-container distribution)
- **Last verified:** 2026-11-02 (13.0.20) — step 8 lab host behind Traefik 3.7.17 on its edge network, all five compose files (sdoc-server 2.0.9, notification-server 13.0.10, md-server and thumbnail-server 13.0.20), installed by the README: API login, libraries, a 10 MB and a 300 MB upload and download with identical checksums, the sync protocol the desktop client uses (`download-info`, `commit/HEAD`, `fs-id-list`, `pack-fs`, the permission checks; a wrong repo token 403), WebDAV PROPFIND/PUT/GET/DELETE, the notification WebSocket delivering `repo-update` after an upload, SeaDoc's document fetch from Seahub over the internal network and its WebSocket, browser-session thumbnails, an anonymous share-link download — through lab scripts, no official client run, OnlyOffice's callbacks and SMTP not run; the restore rehearsal in backup/borgmatic/RESTORE.md (docs/labs/ingress/2026-11-01-results.md). Earlier: `Last checked` 2026-04-16

## What we use

- `seafileltd/seafile-mc` — main server (Seahub + file server + ccnet)
- `mariadb:10.11.19` LTS as backend
- `memcached:1.6.45-alpine` and `redis:8.10.3-alpine` for caching
- Optional: `sdoc-server`, `notification-server`, `seafile-md-server`, `thumbnail-server` (all official Seafile images)
- Upstream's reference compose as a starting point, then adapted to Blueprint conventions

## What we changed and why

| Change | Reason |
|--------|--------|
| Split into five compose files (core + 4 optional) | Components are independent features; users should be able to toggle each on/off without editing a single giant compose file |
| Custom shared entrypoint (`config/entrypoint.sh`) | Seafile's internal init scripts don't consistently honour `_FILE` env vars; the wrapper reads `/run/secrets/*` and exports them to match whatever var name each service expects |
| `seahub_custom.py` injection mechanism | Avoids replacing Seafile's auto-generated `seahub_settings.py` while still allowing blueprint-local overrides (TLS-aware URLs, proxy trust, etc.) |
| `app-internal` network with `internal: true` | DB, Redis, Memcached have no outbound reachability — standard hardening |
| Traefik routers for `/`, `/sdoc-server`, `/socket.io/`, `/notification`, `/thumbnail` | Upstream docs show nginx vhost blocks for this; the same paths work 1:1 through Traefik routers + one stripprefix middleware |
| `priority=1` on main router, `priority=100` on sub-service routers | Without explicit priorities, Traefik's catch-all `Host(…)` router intercepts `/thumbnail`, `/notification`, and `/sdoc-server` paths before the dedicated sub-service routers. Upstream uses nginx with location blocks that have implicit specificity; Traefik requires explicit priority. |
| `JWT_PRIVATE_KEY` and `SEAFILE_MYSQL_DB_PASSWORD` as direct env vars for `thumbnail-server` | Unlike other services, the thumbnail-server image does not use the shared `entrypoint.sh` wrapper — it runs its own init without reading Docker Secrets. Passing `_FILE` paths works for the main `seafile` container (wrapper reads them) but silently fails in the thumbnail container, causing 403 on all thumbnail requests. Upstream's reference stack avoids this by running all services under the same nginx process with a shared env. |
| `ENABLE_GO_FILESERVER: "true"` | Seafile 13 default, but explicit — the Go file server is required for modern sync clients |
| `APP_TRAEFIK_LIMIT=limit-sync` | The sync client runs three upload and three download threads and issues one request per block, through the main router. Above the 125 requests per second of `limit-standard` a sync of many small files is answered `429` and fails; `limit-sync` allows 1000 |
| MariaDB healthcheck includes `--mariadbupgrade --innodb_initialized` | Avoids the race where Seafile connects before MariaDB has finished a version upgrade on restart |
| `SEAFILE_SERVER_HOSTNAME: 127.0.0.1:8000` in `docker-compose.local.yml` | First-boot setup (`setup-seafile-mysql.py`, 13.0.20) accepts only a host name that contains a dot. On `localhost:8000` it exits with status 255 before it writes a file or opens the database, Seahub never starts, and the stack answers `502`. Seahub builds `SERVICE_URL` and `FILE_SERVER_ROOT` from this value, so the local stack is opened at the same address |

## Version / tag notes

- `seafileltd/seafile-mc:13.0.29` — pinned; main server is the most sensitive to schema migrations
- `sdoc-server:2.0.11`, `notification-server:13.0.29`, `md-server:13.0.28`, `thumbnail-server:13.0.29` — pinned to exact releases; upstream's compose files use moving `-latest` tags inside a major line.

### Version notes

- Moved to `13.0.29` on 2026-11-05, not run on a host at this tag. From
  `seafile-mc` 13.0.20, `notification-server` 13.0.10, `seafile-md-server` 13.0.20,
  `thumbnail-server` 13.0.20 and `sdoc-server` 2.0.9 to `seafile-mc` 13.0.29,
  `notification-server` 13.0.29, `seafile-md-server` 13.0.28 (the newest 13.0 tag
  of that image), `thumbnail-server` 13.0.29 and `sdoc-server` 2.0.11 (newest 2.0
  tag, the line the Seafile 13 manual names with `2.0-latest`). The 13.0.20 images
  carried CRITICAL Trivy findings, mostly in OS packages; the 13.0.29 image is
  built on a newer Ubuntu 24.04 base. Breaking changes: none listed. The changelog
  (https://plus.seafile.com/wiki/publish/seafile-wiki/5L80/) names no
  configuration change, renamed or removed variable, manual step or migration
  between 13.0.21 and 13.0.29 apart from a new, unnamed md-server option for the
  profile feature (13.0.24), not set here. Behaviour changes to know: the Go file
  server removes unfinished temporary uploads (13.0.21), deactivated users can no
  longer authenticate with a WebDAV password (13.0.25), read-only repository API
  tokens can no longer batch-write (13.0.28). Upgrade steps: the checklist below;
  schema changes run on the first start. Advisories, from upstream's security
  page (https://plus.seafile.com/wiki/publish/seafile-wiki/O50D/): 13.0.29 fixes
  cross-site scripting, privilege bypass, unauthorised access and resource
  exhaustion, an SQL injection in the API, an SSRF in the markdown-to-SDoc
  conversion, and a flaw that allowed filesystem objects to be overwritten and
  the folder-share boundary to be bypassed; 13.0.28, 13.0.27 (SAML
  authentication, CAN-2026-2034155), 13.0.25, 13.0.23 and 13.0.22 carry earlier
  fixes this move also takes in. No CVE IDs are given for 13.0.29. Seafile 14.0 is
  not taken: the changelog lists its only release as "14.0.9 beta (2026-10-14)",
  so the stack stays on the stable 13 line.
- Moved `redis` from `7.4-alpine` to `8.10.3-alpine` on 2026-11-05, a new major, not
  run on a host at this tag; the tag follows the 8.10 patch releases (8.10.3,
  2026-10-26). Redis 8 is offered under RSALv2, SSPLv1 or AGPLv3 at the user's
  choice (7.4: RSALv2 or SSPLv1). The image bundles the Query Engine, JSON, time
  series and probabilistic data types as modules, which the image's entrypoint loads
  at start on amd64 and arm64; this stack uses none of them. 8.x reads the 7.4 data
  files in place, but Redis does not load files written by a newer version, so a
  rollback needs the backup of the Redis data. The one potentially breaking change
  upstream lists: `GETRANGE` with an out-of-range negative end returns an empty
  string. Security fixes in the 8.10 line: CVE-2026-62356 (8.10.1, heap write when
  loading a Count-min sketch from an RDB file), queued `MULTI` commands keeping
  access to keys whose ACL permission was revoked (8.10.2), and a cluster-bus
  overflow that needs cluster mode (8.10.3). The 7.4 line still receives fixes
  (7.4.12, 2026-10-26); the move is to the newest stable line, not away from an
  unmaintained one. Seafile 13's compose uses the untagged `redis` image, which
  already resolves to 8.x. `REDIS_IMAGE` in `.env.example` and `REDIS_TAG` in
  `.env.local.example` both move. This service's command starts with `sh`, so the
  image's entrypoint neither drops privileges nor loads the modules and Redis runs
  as root, as it did on 7.4; no compose change. Sources:
  https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://manual.seafile.com/latest/setup/setup_ce_by_docker/

## Upgrade checklist

Seafile 13's schema migrations are forward-only. Back up before upgrading.

1. Read the changelog for the target version: https://manual.seafile.com/13.0/changelog/server-changelog/
2. Back up:

   ```bash
   # Database
   docker compose exec db sh -c \
     'mariadb-dump -u root -p"$MARIADB_ROOT_PASSWORD" --all-databases --single-transaction' \
     > seafile-db-$(date +%Y%m%d).sql
   # Data volume
   tar czf seafile-data-$(date +%Y%m%d).tgz ./volumes/seafile-data
   ```

3. Bump `APP_IMAGE` (and the related `*_IMAGE` tags) in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch startup:

   ```bash
   docker compose logs seafile --follow
   ```

   Expect schema migration output on the first start after the bump.
6. Verify: log in, upload/download a file, open an existing SeaDoc doc.

### Rollback

Downgrades are **not** supported once Seahub has written a newer schema. Rollback = restore `seafile-data-*.tgz` + `seafile-db-*.sql` and revert image tags.

## Related images to keep in sync

- `mariadb:10.11.19` — LTS, safe to update minor versions
- `redis:8.10.3-alpine`, `memcached:1.6.45-alpine` — safe to update minor versions
- `sdoc-server`, `notification-server`, `md-server`, `thumbnail-server` — should track the same Seafile major line as the main `seafile-mc` image

## Useful commands

```bash
# Status and version
docker compose exec seafile bash -c \
  'cat /opt/seafile/seafile-server-*/VERSION 2>/dev/null || /opt/seafile/seafile-server-latest/seaf-server -v'

# Run a Django management command
docker compose exec seafile bash -c \
  '/opt/seafile/seafile-server-latest/seahub.sh python_env manage.py <command>'

# Full Seafile setup check
docker compose exec seafile bash -c \
  '/opt/seafile/seafile-server-latest/seahub.sh python_env manage.py check'

# Tail all services at once
docker compose logs --follow

# Manual DB backup
docker compose exec db sh -c \
  'mariadb-dump -u root -p"$MARIADB_ROOT_PASSWORD" --all-databases --single-transaction' \
  > dump.sql
```
