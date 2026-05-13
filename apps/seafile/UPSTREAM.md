# Upstream Reference

## Source

- **Docs:** https://manual.seafile.com/13.0/docker/
- **Deploy manual (CE):** https://manual.seafile.com/13.0/docker/deploy_seafile_ce_with_docker/
- **Image (main):** https://hub.docker.com/r/seafileltd/seafile-mc
- **GitHub:** https://github.com/haiwen/seafile
- **License:** AGPL-3.0
- **Origin:** China · Seafile Ltd · non-EU
- **Note:** Chinese company: data stored on self-hosted instances is under your jurisdiction, but the vendor is subject to Chinese law.
- **Based on version:** Seafile CE `13.0.20` (multi-container distribution)
- **Last checked:** 2026-04-16

## What we use

- `seafileltd/seafile-mc` — main server (Seahub + file server + ccnet)
- `mariadb:10.11` LTS as backend
- `memcached:1.6-alpine` and `redis:7.4-alpine` for caching
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
| `ENABLE_GO_FILESERVER: "true"` | Seafile 13 default, but explicit — the Go file server is required for modern sync clients |
| MariaDB healthcheck includes `--mariadbupgrade --innodb_initialized` | Avoids the race where Seafile connects before MariaDB has finished a version upgrade on restart |

## Version / tag notes

- `seafileltd/seafile-mc:13.0.20` — pinned; main server is the most sensitive to schema migrations
- `sdoc-server:2.0-latest`, `notification-server:13.0-latest`, `md-server:13.0-latest`, `thumbnail-server:13.0-latest` — Seafile ships these with moving `:latest` tags inside a major line. For production, pin to the digest shown by `docker compose images`.

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

- `mariadb:10.11` — LTS, safe to update minor versions
- `redis:7.4-alpine`, `memcached:1.6-alpine` — safe to update minor versions
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
