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

After the browser-based setup, run these once to clear Nextcloud's default warnings and apply stable defaults:

```bash
# Fix data directory ownership
docker compose exec app chown -R www-data:www-data /var/www/html/data

# Maintenance window: run heavy background jobs at 01:00 UTC
docker compose exec -u www-data app php occ config:system:set maintenance_window_start --value=1 --type=integer

# Repair tasks (safe to run, clears stale warnings)
docker compose exec -u www-data app php occ maintenance:repair --include-expensive

# Set your region for phone number formatting
docker compose exec -u www-data app php occ config:system:set default_phone_region --value="AT"

# Log level: 2 = Warning. Lower values (0=Debug, 1=Info) produce very large logs.
docker compose exec -u www-data app php occ config:system:set loglevel --value=2 --type=integer
```

**If OnlyOffice is installed**, also run these immediately after enabling the app. See the [OnlyOffice integration notes](#onlyoffice-integration-notes) section for the full explanation:

```bash
# Disable OnlyOffice preview/thumbnail generation (keep document editing enabled)
docker compose exec -u www-data app php occ config:app:set onlyoffice preview --value="false"

# Verify
docker compose exec -u www-data app php occ config:app:get onlyoffice preview
# Expected output: false
```

**Conservative preview providers** — limit thumbnail generation to fast, safe formats. Avoid video, Office, and PDF providers that can block PHP-FPM workers:

```bash
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 0 --value="OC\\Preview\\Image"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 1 --value="OC\\Preview\\TXT"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 2 --value="OC\\Preview\\MarkDown"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 3 --value="OC\\Preview\\OpenDocument"

# Verify
docker compose exec -u www-data app php occ config:system:get enabledPreviewProviders
```

## Verify

```bash
# Container health and resource usage
docker stats --no-stream
docker compose ps

# Nextcloud installed and reachable
docker compose exec -u www-data app php occ status

# Confirm trusted proxies are set correctly
docker compose exec -u www-data app php occ config:system:get trusted_proxies

# Confirm Redis is reachable and the correct policy is active
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" CONFIG GET maxmemory-policy

# Confirm PHP-FPM pool config was applied
docker compose exec app php-fpm -tt 2>&1 | grep -E "max_children|pm ="

# Confirm MariaDB flags are active
docker compose exec db mariadb -u root -p"$(cat .secrets/db_root_pwd.txt)" \
  -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"

# Confirm OnlyOffice preview is disabled (if OnlyOffice is installed)
docker compose exec -u www-data app php occ config:app:get onlyoffice preview

# Confirm global preview setting
docker compose exec -u www-data app php occ config:system:get enable_previews
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

## Server sizing and tuning rationale

This configuration is tuned for a **Hetzner CPX32** (4 vCPU / 8 GB RAM / 160 GB SSD) running a small business collaboration workload: document editing via OnlyOffice, team folders, and normal file sync. It is not intended as a large public file hosting platform.

### Upload limits

`PHP_UPLOAD_LIMIT=128M` and `client_max_body_size 128M` are set conservatively. 128 MB covers all normal business document workflows. Keeping the limit low reduces abuse surface and memory pressure during concurrent uploads. Both values must always match — if you raise one, raise the other.

### PHP memory limit

`PHP_MEMORY_LIMIT=1024M` is generous for this use case. Normal Nextcloud requests use 100–300 MB. The higher limit provides headroom for preview generation and full-text indexing without risking per-request memory exhaustion.

### MariaDB

`--innodb-buffer-pool-size=1G` keeps frequently accessed Nextcloud tables (`oc_filecache`, `oc_activity`, `oc_share`) in memory and reduces read I/O. The Docker image default is 128 MB, which is too small for a Nextcloud database under normal load.

`--innodb-log-file-size=256M` — Nextcloud produces a high rate of small writes: every file access updates `oc_filecache`, every user action appends to `oc_activity`, and file locking generates continuous `INSERT`/`DELETE` cycles in `oc_locks`. The InnoDB redo log buffers these writes before they are flushed to the data files. When the log fills, InnoDB triggers a checkpoint (synchronous flush), which stalls all writes until the flush completes. The default in MariaDB 10.11 is approximately 96 MB. With Nextcloud's write pattern on an active team instance, this fills quickly and produces periodic I/O stalls. 256 MB extends the time between forced checkpoints and smooths write latency. **Operational impact:** on the first restart after adding this flag, MariaDB automatically resizes the redo log. This is safe and handled internally — no manual steps required. On a 160 GB SSD the resize takes a few seconds.

`--max-connections=200` — explicitly set to match the PHP-FPM pool size (10 workers, both app and cron) with significant headroom for monitoring and admin connections.

`--innodb-buffer-pool-instances` was **not** added — it was removed in MariaDB 10.11 and has no effect. Using it would generate a startup warning.

### PHP-FPM worker pool

The default Nextcloud Docker image ships with `pm.max_children=5`. On this server, cron jobs run every 5 minutes and consume 1–2 workers for 30–120 seconds (file scanning, preview generation, notifications). With only 5 workers, this exhausts the pool during cron execution and causes 502/504 errors that resolve 1–3 minutes later — the characteristic intermittent outage pattern.

`php-fpm/zz-nextcloud-pool.conf` overrides the pool to `pm.max_children=10`. This file is mounted read-only into both `app` and `cron`. It is loaded after the image's own `zz-docker.conf` (alphabetical order: `zz-nextcloud-pool.conf` > `zz-docker.conf`) so it takes precedence. See the file itself for the full sizing calculation.

**Verify the mount path before restarting:**
```bash
docker compose exec app ls /usr/local/etc/php-fpm.d/
# Expected: docker.conf  www.conf  zz-docker.conf  zz-nextcloud-pool.conf
```

### Redis

`maxmemory 512mb` — raised from the previous 256 MB. Nextcloud uses Redis for file locking, session storage, and transient cache. 512 MB provides adequate headroom for a small team workload without putting meaningful pressure on the 8 GB server.

`maxmemory-policy noeviction` — when Redis reaches its memory limit, it returns an error on new writes rather than silently evicting existing data. This is the stability-first choice:

- Nextcloud handles Redis OOM errors gracefully: it falls back to database-based locking and continues operating in a degraded but correct state.
- The alternative policies (`allkeys-lru`, `volatile-lru`) would silently remove active file locks or sessions under memory pressure, causing data races or unexpected logouts with no visible error.
- With 512 MB and a small team workload, the memory limit should not be reached under normal operation. If it is, the OOM error is a visible, actionable signal to increase `maxmemory`.

**AOF / append-only persistence** is not enabled. RDB persistence (default) is sufficient here. If Redis restarts, active PHP sessions are lost (users are logged out) and in-progress file locks expire. This is acceptable for a small team setup. Enabling AOF adds continuous fsync I/O overhead without a proportionate benefit for this use case.

### Traefik security profile

`APP_TRAEFIK_SECURITY=sec-3-spa` is the recommended default for Nextcloud, not the generic `sec-3`.

Nextcloud generates significant legitimate background traffic that does not fit the pattern of a standard web application:

- Sync clients poll OCS API endpoints continuously
- WebDAV and PROPFIND requests are issued for every mounted folder
- Activity, notifications, and dashboard widgets poll at regular intervals
- Mobile clients maintain persistent connections

`sec-3` uses `rl-soft` (100 req/s average, burst 50). This burst cap is too low for Nextcloud's combined sync + interactive traffic and returns HTTP 429 under normal load. `sec-3-spa` uses `rl-spa`, which allows the initial request burst while applying the same strict security headers and permissions-policy. The `.env.example` default reflects this.

## Recommended application set

For small business collaboration deployments, a minimal and stable application set avoids unnecessary background jobs and resource consumption.

**Keep enabled:**

| App | Reason |
|-----|--------|
| Files | Core — cannot disable |
| Group Folders | Team-shared folder management |
| Guests | External collaborator access |
| Activity | Audit trail and change notifications |
| OnlyOffice | Document editing (keep editing enabled, disable previews — see below) |

**Consider disabling** (not needed for document collaboration):

| App | Why |
|-----|-----|
| Photos | Runs background AI jobs; not needed if OnlyOffice previews are off |
| Recommendations | Background machine learning; adds load with no stability benefit |
| Contacts / ContactsInteraction | Only needed if Nextcloud is also your address book |
| First Run Wizard | Remove after initial setup |
| Support | Adds telemetry prompts |
| Survey Client | Phones home |
| Weather Status | External API calls from the server |

Disabling unused apps reduces background job load, reduces cron execution time, and keeps PHP-FPM worker usage predictable.

## OnlyOffice integration notes

OnlyOffice document **editing** works well and should remain enabled. The integration allows users to open and collaboratively edit `.docx`, `.xlsx`, `.pptx`, and similar formats directly in the browser.

OnlyOffice **preview and thumbnail generation** is a separate feature that causes significant stability problems and should be disabled for small business setups.

### Why preview generation causes problems

When a user opens a folder containing PDFs, Nextcloud requests a thumbnail for each file. With OnlyOffice acting as a preview provider, each PDF thumbnail triggers a `POST /converter` request to the OnlyOffice DocumentServer. OnlyOffice converts the PDF to JPEG using a headless document pipeline. This is slow, resource-intensive, and blocks:

- The PHP-FPM worker that initiated the request (held for up to 120 seconds per timeout)
- The nginx fastcgi slot waiting for a response
- The user's browser, which shows the folder as loading indefinitely

Observed log signatures:

```
# Nextcloud log (nextcloud.log or occ log:watch)
app: onlyoffice
message: getConvertedUri: from pdf to jpeg
POST https://office.<domain>/converter → 504 Gateway Timeout

# OnlyOffice / nginx log
POST /converter?shardKey=thumb_...
upstream timed out while reading response header from upstream
whole request cycle timeout: 2m
```

Neither PHP-FPM workers, MariaDB, Redis, CPU, nor RAM are at fault. The bottleneck is the OnlyOffice converter itself. Increasing timeouts makes the hang longer, not shorter.

### Recommended configuration

Disable OnlyOffice preview generation. Document editing is unaffected.

```bash
docker compose exec -u www-data app php occ config:app:set onlyoffice preview --value="false"

# Verify
docker compose exec -u www-data app php occ config:app:get onlyoffice preview
# Expected: false
```

Also restrict the global preview providers to fast, lightweight formats only:

```bash
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 0 --value="OC\\Preview\\Image"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 1 --value="OC\\Preview\\TXT"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 2 --value="OC\\Preview\\MarkDown"
docker compose exec -u www-data app php occ config:system:set enabledPreviewProviders 3 --value="OC\\Preview\\OpenDocument"
```

This leaves document editing fully functional. PDF and Office file thumbnails will not be generated.

### Stronger option: disable all previews

For deployments focused on file collaboration, team folders, or document repositories where thumbnail generation is not needed, disabling previews globally is a simpler and more stable option:

```bash
docker compose exec -u www-data app php occ config:system:set enable_previews --value=false --type=boolean

# Verify
docker compose exec -u www-data app php occ config:system:get enable_previews
# Expected: false
```

This disables all thumbnail generation regardless of which preview providers are configured. Appropriate when:
- Users share and edit documents but do not rely on image gallery or thumbnail views
- Stability is more important than visual previews
- The deployment is primarily used for team folders and document collaboration

Document editing via OnlyOffice is not affected by this setting.

### Follow-up

OnlyOffice DocumentServer performance itself (internal URL resolution, reverse proxy path, converter sizing) should be reviewed separately if document editing latency becomes a concern. Disabling previews is the stable workaround; it does not address the root cause of slow OnlyOffice conversion.

---

## Troubleshooting

### Nextcloud appears to hang when users open folders

**Symptoms:** Folder contents load very slowly or indefinitely. The browser spinner runs for 30–120 seconds. After the timeout, folders may load or Nextcloud may show an error.

**Before changing any configuration, check these in order:**

**Step 1 — Check `docker stats` first.** Confirm the bottleneck is not CPU or RAM exhaustion before assuming it is a configuration problem.

```bash
docker stats --no-stream
```

If all containers show low CPU and memory is not near the limit, the problem is not resource exhaustion.

**Step 2 — Check PHP-FPM worker availability.**

```bash
docker compose exec app php-fpm -tt 2>&1 | grep -E "max_children|pm ="
```

If workers are frequently at capacity, increase `pm.max_children` in `php-fpm/zz-nextcloud-pool.conf`. Do not blindly increase timeouts — they make the hang last longer, not shorter.

**Step 3 — Check the Nextcloud log for OnlyOffice preview requests.**

```bash
docker compose exec -u www-data app php occ log:watch
```

Look for:
```
app: onlyoffice
getConvertedUri: from pdf to jpeg
```

If this appears when users open folders, the problem is OnlyOffice preview generation. Apply the fix in the [OnlyOffice integration notes](#onlyoffice-integration-notes) section.

**Step 4 — Check the OnlyOffice / nginx log for converter timeouts.**

```
POST /converter?shardKey=thumb_...
upstream timed out while reading response header from upstream
whole request cycle timeout: 2m
```

If this appears, OnlyOffice is the bottleneck. Disabling OnlyOffice previews resolves this immediately without changing any timeout values.

---

## Known Issues

- **Admin overview warnings that are safe to ignore:**
  - `.well-known URLs` — CalDAV/CardDAV redirect works via Traefik middleware; Nextcloud's internal self-check does not detect the Traefik-level rewrite.
  - `X-Frame-Options` — Set by the security middleware chain, but Nextcloud checks its own PHP output and doesn't see the Traefik header.
  - `Email test`, `Second factor`, `AppAPI deploy daemon` — Configure when/if those features are needed.
- **First install is slow** — the healthcheck has `start_period: 120s` because the Nextcloud installer can take over a minute to run all migrations on first boot.
- **Large file uploads need matching limits on both sides**: `PHP_UPLOAD_LIMIT` and nginx's `client_max_body_size` in `nginx/nginx.conf`.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, post-install steps, upstream diff commands
