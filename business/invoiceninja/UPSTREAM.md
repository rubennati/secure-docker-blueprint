# Upstream Reference

## Source

- **Repo:** https://github.com/invoiceninja/dockerfiles (branch: `debian`)
- **Docs:** https://invoiceninja.github.io/docs/self-host/self-host-installation
- **License:** Elastic License 2.0
- **Origin:** US · Invoice Ninja LLC · non-EU
- **Note:** Elastic License 2.0 is not OSI-approved — source-available, not open source. Self-hosting permitted; providing it as a managed service to others is restricted.
- **Based on version:** 5.13.24
- **Last checked:** 2026-06-14

## Pinned Versions

| Component | Tag | Notes |
|---|---|---|
| Invoice Ninja | `5.13.24` | Verified stable on Docker Hub 2026-06-14 |
| MySQL | `8.4` | LTS — upstream target DB |
| Redis | `8.6-alpine` | |
| Nginx | `1.29-alpine` | |

## What We Use From Upstream

| File | Status | Notes |
|---|---|---|
| `docker-compose.yml` | Adapted | Added Traefik labels, Blueprint naming conventions |
| `.env` | Adapted | Restructured, passwords as placeholders, section headers |
| `nginx/laravel.conf` | 1:1 copy | Server block: Laravel routes + FastCGI to app:9000 |
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
| Healthchecks do not test actual service responsiveness | `php -r "echo 'ok';"` tests the PHP binary only; `nginx -t` tests config only. | Improve once tooling in the pinned images is confirmed |
| Named volumes instead of bind mounts | Upstream pattern; harder to inspect on host but simpler to set up. | Migrate to `./volumes/` bind mounts in a future cleanup |

## Known Issues

- **502 on start**: MySQL init causes a brief connection failure from the app container — normal, resolves within ~30s. The `depends_on: condition: service_healthy` mitigates but does not fully prevent this.
- **No Docker Secrets**: Laravel does not support `_FILE` env vars for most variables. All secrets are in `.env` (gitignored, never committed).
- **First boot race**: If `APP_KEY` is not set on first boot, the app starts but generates an error. Always set `APP_KEY` before `docker compose up -d` on a fresh install, or follow the two-step startup in README.md.

## Backup

**Back up before every upgrade.** Invoice Ninja data is split across the MySQL database and the `app_storage` named volume.

### Database backup

```bash
# Dump the ninja database to a timestamped SQL file
docker exec invoiceninja-mysql mysqldump \
  -u root -p"$(grep '^DB_ROOT_PASSWORD=' .env | cut -d= -f2)" ninja \
  > backup-db-$(date +%Y%m%d-%H%M).sql
```

### Storage backup (invoices, attachments, logos, templates)

```bash
# Dump app_storage volume contents via a helper container
docker run --rm \
  -v invoiceninja_app_storage:/data:ro \
  -v "$(pwd)":/out \
  alpine tar czf /out/backup-storage-$(date +%Y%m%d-%H%M).tar.gz -C /data .
```

### .env backup

```bash
cp .env .env.backup-$(date +%Y%m%d)
```

### What must be backed up

| Item | Why critical |
|---|---|
| MySQL `ninja` database | All invoices, clients, payments, settings |
| `app_storage` volume | Attachments, uploaded logos, generated PDFs, encryption keys |
| `.env` (especially `APP_KEY`) | Without `APP_KEY` you cannot decrypt any stored data |

## Restore

### Restore database

```bash
# 1. Bring up only MySQL
docker compose up -d mysql
docker compose exec mysql sh -c 'mysql -u root -p"${MYSQL_ROOT_PASSWORD}" ninja' < backup-db-YYYYMMDD-HHMM.sql
```

### Restore storage

```bash
# Restore into the named volume via a helper container
docker run --rm \
  -v invoiceninja_app_storage:/data \
  -v "$(pwd)":/in \
  alpine sh -c "cd /data && tar xzf /in/backup-storage-YYYYMMDD-HHMM.tar.gz"
```

### Restore .env

```bash
cp .env.backup-YYYYMMDD .env
```

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
