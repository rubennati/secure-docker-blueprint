# Upstream Reference

## Source

- **Repo:** https://github.com/invoiceninja/dockerfiles (branch: `debian`)
- **Docs:** https://invoiceninja.github.io/docs/self-host/self-host-installation
- **License:** Elastic License 2.0
- **Origin:** US · Invoice Ninja LLC · non-EU
- **Note:** Elastic License 2.0 is not OSI-approved — source-available, not open source. Self-hosting permitted; providing it as a managed service to others is restricted.
- **Based on version:** 5.13.26
- **Last checked:** 2026-06-14

## Pinned Versions

| Component | Tag | Notes |
|---|---|---|
| Invoice Ninja | `5.13.26` | Latest release 2026-07-26 |
| MySQL | `8.4` | LTS — upstream target DB |
| Redis | `8.6-alpine` | |
| Nginx | `1.29-alpine` | |

## What We Use From Upstream

| File | Status | Notes |
|---|---|---|
| `docker-compose.yml` | Adapted | Added Traefik labels, Blueprint naming conventions |
| `.env` | Adapted | Restructured, passwords as placeholders, section headers |
| `nginx/laravel.conf` | Modified | Server block: Laravel routes + FastCGI to app:9000; FastCGI timeouts added (see deviations) |
| `nginx/invoiceninja.conf` | 1:1 copy | Global nginx settings: gzip, buffers, body size, server_tokens |

## What We Changed and Why

| Change | Reason |
|--------|--------|
| Traefik labels on nginx | Blueprint uses Traefik, not exposed ports |
| certresolver commented out | crt.sh privacy |
| Network `name:` added | Blueprint naming (`invoiceninja-internal`) |
| Container names via `CONTAINER_NAME_*` variables | Blueprint standard |
| Image tags pinned (not floating) | Reproducibility; `latest` is never used |
| `COMPOSE_PROJECT_NAME` instead of `STACK_NAME` | Docker Compose standard variable |
| `APP_TRAEFIK_HOST` / `APP_TRAEFIK_ACCESS` etc. | Blueprint Traefik variable naming convention |
| `MYSQL_PASSWORD` / `MYSQL_ROOT_PASSWORD` removed from `.env` | Compose expands `${DB_PASSWORD}` / `${DB_ROOT_PASSWORD}` inline — no separate variables needed |
| `REDIS_PASSWORD=` (empty) instead of `null` | `null` was passed as a literal string; empty means no auth, matching the Redis container's no-auth config |
| Section header style `# ---` instead of `###` | Aligns with blueprint `.env.example` convention |
| `security_opt: no-new-privileges:true` on all services | Blueprint security baseline |
| `deploy.resources` limits on all services | Baseline resource constraints |
| `REQUIRE_HTTPS=true` | Correct behind Traefik |
| `APP_DEBUG=false` | Production safety |
| `NINJA_ENVIRONMENT=selfhost` added | Explicit self-host mode |
| MySQL healthcheck uses app-user `SELECT 1` | `mysqladmin ping` marks MySQL healthy before user/DB init completes, causing first-boot race. App-user check gates the app container on a real usable connection. |
| App container memory limit raised to 1G | Snappdf/Chromium PDF rendering requires more than 512M. The previous limit caused OOM on live preview and complex PDF renders. |
| nginx FastCGI timeouts set to 300s in `laravel.conf` | nginx default 60s is insufficient for Chromium PDF renders via `/api/v1/live_design` and `/api/v1/live_preview`, causing 504 errors. |
| APP_KEY generated before first boot via `openssl` | Starting without APP_KEY causes an error during migration and requires a two-step restart. Offline key generation removes the race. |

## What We Kept From Upstream

- `env_file: ./.env` — Invoice Ninja reads many env vars directly at runtime
- Named Docker volumes (not bind mounts) — upstream pattern; simplifies first-boot
- Service names: `app`, `nginx`, `mysql`, `redis`
- nginx config files — 1:1 from upstream
- All app env vars (`FILESYSTEM_DISK`, `CACHE_DRIVER`, `PDF_GENERATOR`, etc.)
- MySQL 8 — Invoice Ninja upstream officially targets MySQL 8; MariaDB works but is not tested here

## Known Deviations

| Deviation | Details | Future plan |
|---|---|---|
| Passwords in `.env` | Laravel has no `_FILE` support for most variables including `APP_KEY` and `DB_PASSWORD`. Secrets are in the gitignored `.env`. | Custom entrypoint for Docker Secrets injection (Phase 2) |
| `TRUSTED_PROXIES=*` | Wildcard trusts any IP as proxy. Safe when Traefik is the only path to nginx, but is technically too permissive. | Tighten to Traefik container IP or internal CIDR |
| MySQL instead of MariaDB | Upstream requirement; blueprint default is MariaDB for other stacks. | No change planned — stays MySQL |
| App healthcheck does not test PHP-FPM or queue liveness | `php -r "echo 'ok';"` tests the PHP binary only; `nginx -t` tests config only. MySQL healthcheck now uses an app-user SELECT which is accurate. | Improve app/nginx checks once tooling in the pinned images is confirmed |
| Named volumes instead of bind mounts | Upstream pattern; harder to inspect on host but simpler to set up. | Migrate to `./volumes/` bind mounts in a future cleanup |

## Known Issues

- **No Docker Secrets**: Laravel does not support `_FILE` env vars for most variables. All secrets are in `.env` (gitignored, never committed).
- **App healthcheck is not a full liveness check**: `php -r "echo 'ok';"` verifies the PHP binary is callable but not that PHP-FPM is accepting connections or that supervisor processes (queue workers, scheduler) are running. Use `supervisorctl status` inside the container to verify those.
- **PDF rendering memory**: Snappdf/Chromium can spike past 1G on complex invoices or many concurrent renders. If rendering fails consistently, increase `memory:` on the app service and restart.

## Backup and restore

Owned by [`README.md`](README.md#backup) — what must be captured, the borgmatic
block, and the manual dump/restore commands. Kept there because that is where
the per-app backup pattern lives and what `lifecycle-report.py` reads.

## Rollback

If an upgrade causes problems:

```bash
# 1. Stop all containers
docker compose down

# 2. Restore .env with the previous APP_TAG
cp .env.backup-YYYYMMDD .env

# 3. Restore the database
docker compose up -d mysql
docker exec -i invoiceninja-mysql mysql -u root \
  -p"$(grep '^DB_ROOT_PASSWORD=' .env | cut -d= -f2)" ninja \
  < backup-db-YYYYMMDD-HHMM.sql

# 4. Restore storage if needed
docker run --rm \
  -v invoiceninja_app_storage:/data \
  -v "$(pwd)":/in \
  alpine sh -c "cd /data && tar xzf /in/backup-storage-YYYYMMDD-HHMM.tar.gz"

# 5. Bring back up on the previous image
docker compose up -d
```

## Upgrade Checklist

1. Check [Invoice Ninja releases](https://github.com/invoiceninja/invoiceninja/releases)
2. Check [dockerfiles repo](https://github.com/invoiceninja/dockerfiles/tree/debian) for any nginx or compose changes
3. **Backup first** — database dump + storage + `.env` (see Backup section above)
4. Bump `APP_TAG` in `.env`
5. `docker compose pull`
6. `docker compose up -d`
7. Watch migrations: `docker compose logs app --follow`
8. Verify: `curl -sI https://your-domain/` → 200 or 302
9. Log in and confirm data is intact

Invoice Ninja v5 runs `php artisan migrate --force` automatically on startup. No manual migration step is needed. Within the v5 series, upgrades are cumulative and do not require intermediate version stops.
