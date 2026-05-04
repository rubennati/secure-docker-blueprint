# Nextcloud

> **Status: ✅ Ready** — v32 · 2026-04-13

Self-hosted file sync, calendar, contacts, and collaboration suite. This setup runs Nextcloud as **PHP-FPM behind nginx**, with MariaDB as database and Redis for file locking and session storage.

## Architecture

Five services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `nextcloud:32-fpm-alpine` | PHP-FPM — the Nextcloud application |
| `nginx` | `nginx:alpine-slim` | Web server, speaks HTTP to Traefik and FastCGI to `app` |
| `db` | `mariadb:10.11` | Primary data store |
| `redis` | `redis:7-alpine` | File locking + session cache |
| `cron` | `nextcloud:32-fpm-alpine` | Runs Nextcloud's scheduled jobs (`cron.php` every 5 minutes) |

Traefik routes to `nginx`, which proxies PHP requests to `app` via FastCGI on port 9000. `cron` uses the same image as `app` but with `entrypoint: /cron.sh` and no HTTP listener.

### Why FPM + nginx instead of Apache

The Alpine FPM image is lighter and gives nginx full control over static asset serving, caching headers, and the CalDAV/CardDAV path rewrites. The `.env.example` documents the fallback to the `-apache` variant if this architecture causes issues.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, NC_TRUSTED_PROXIES, TZ
# Generate REDIS_PASSWORD: openssl rand -hex 32

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 3. Find the correct NC_TRUSTED_PROXIES value
docker network inspect proxy-public --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
# Update NC_TRUSTED_PROXIES in .env with that subnet

# 4. Start
docker compose up -d

# 5. Complete setup in the browser
# https://<APP_TRAEFIK_HOST>
# Admin user + password are created here — there's no pre-seeded admin account.
```

Default access policy is `acc-public` + `sec-3` — public-facing, hardened headers, standard rate limiting.

> **If you plan to integrate OnlyOffice:** keep `APP_TRAEFIK_ACCESS=acc-public`. OnlyOffice makes server-to-server callbacks to Nextcloud over the public domain; `acc-tailscale` would block them.

### Post-install (recommended)

After the browser-based setup, run these once to clear Nextcloud's default warnings:

```bash
docker compose exec app chown -R www-data:www-data /var/www/html/data
docker compose exec -u www-data app php occ config:system:set maintenance_window_start --value=1 --type=integer
docker compose exec -u www-data app php occ maintenance:repair --include-expensive
docker compose exec -u www-data app php occ config:system:set default_phone_region --value="AT"
```

## Verify

```bash
docker compose ps                              # All five services healthy
docker compose exec -u www-data app php occ status
docker compose exec -u www-data app php occ config:system:get trusted_proxies
```

Check the admin overview at `https://<APP_TRAEFIK_HOST>/settings/admin/overview` — it should show no warnings about reverse proxy or cache configuration.

## Security Model

### Network layout

- `proxy-public` — only `nginx` joins; this is where Traefik routes in
- `app-internal` — `app`, `db`, `redis`, `nginx`, `cron`; not flagged `internal: true`

`app-internal` is intentionally **not** marked `internal: true`. Nextcloud's `app` container is not on `proxy-public` (only nginx is), so without outbound routing via `app-internal`, the PHP process could not reach the Nextcloud app store, the update server, or external preview services. The `db` and `redis` containers also gain outbound reachability from this, which is a conscious trade-off.

If you don't use the app store or update checks, you can harden the setup by adding `internal: true` to `app-internal`.

### Per-service hardening

- `no-new-privileges:true` on `db`, `redis`, `nginx`
- **NOT** set on `app` and `cron` — the Nextcloud entrypoint runs as root to chown `config.php` before dropping to www-data; with `no-new-privileges` the file ends up owned by root and FPM gets a 503. Documented in the compose file.
- Database credentials, DB root password → Docker Secrets (`.secrets/*.txt`)
- Redis password → `.env` (passed via `--requirepass` flag; the Redis CLI needs it as a literal string, not a file path). Use `openssl rand -hex 32` to avoid `+/=` characters that break URL encoding in the PHP Redis session handler.

### Traefik middlewares

`nginx` carries two middlewares in addition to access + security chains:

```
${COMPOSE_PROJECT_NAME}-dav@docker,${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file
```

The `-dav` middleware rewrites `/.well-known/caldav` and `/.well-known/carddav` to `/remote.php/dav/` so mobile clients auto-discover correctly.

## Known Issues

- **Admin overview warnings that are safe to ignore:**
  - `.well-known URLs` — CalDAV/CardDAV redirect works via Traefik middleware; Nextcloud's internal self-check does not detect the Traefik-level rewrite.
  - `X-Frame-Options` — Set by the security middleware chain, but Nextcloud checks its own PHP output and doesn't see the Traefik header.
  - `Email test`, `Second factor`, `AppAPI deploy daemon` — Configure when/if those features are needed.
- **First install is slow** — the healthcheck has `start_period: 120s` because the Nextcloud installer can take over a minute to run all migrations on first boot.
- **Large file uploads need matching limits on both sides**: `PHP_UPLOAD_LIMIT` and nginx's `client_max_body_size` in `nginx/nginx.conf`.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, post-install steps, upstream diff commands
