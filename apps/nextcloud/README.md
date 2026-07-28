# Nextcloud

> **Status: 🚧 v34.0.2** — install, mail and hardening verified on a live host;
> desktop and mobile client sync not yet exercised · 2026-07-29

Self-hosted file sync, calendar, contacts, and collaboration suite. This setup runs Nextcloud as **PHP-FPM behind nginx**, with MariaDB as database and Redis for file locking and session storage.

## Architecture

Five services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `nextcloud:34.0.2-fpm-alpine` | PHP-FPM — the Nextcloud application |
| `nginx` | `nginx:1.29-alpine-slim` | Web server, speaks HTTP to Traefik and FastCGI to `app` |
| `db` | `mariadb:10.11` | Primary data store |
| `redis` | `redis:7.4-alpine` | File locking + session cache |
| `cron` | `nextcloud:34.0.2-fpm-alpine` | Runs Nextcloud's scheduled jobs (`cron.php` every 5 minutes) |

Traefik routes to `nginx`, which proxies PHP requests to `app` via FastCGI on port 9000. `cron` uses the same image as `app` but with `entrypoint: /cron.sh` and no HTTP listener.

### Why FPM + nginx instead of Apache

The Alpine FPM image is lighter and gives nginx full control over static asset serving, caching headers, and the CalDAV/CardDAV redirects. The `-apache` variant is a supported alternative upstream; switching to it means dropping the `nginx` service, mounting the configuration into `app` instead, and moving the Traefik labels there with port 80.

## Setup

There is no setup wizard. `NEXTCLOUD_ADMIN_USER_FILE` and
`NEXTCLOUD_ADMIN_PASSWORD_FILE`, set together with the database values, make the
image's entrypoint run `occ maintenance:install` on first start. The installation
is therefore repeatable, reviewable, and there is no window in which an
unauthenticated setup form is reachable.

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, NC_TRUSTED_PROXIES, TZ, and the SMTP block

# 2. Find the correct NC_TRUSTED_PROXIES value — both families if IPv6 is enabled
docker network inspect proxy-public \
  --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}'

# 3. Generate the six secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -hex 32    | tr -d '\n' > .secrets/redis_pwd.txt
printf 'admin'                        > .secrets/admin_user.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/admin_pwd.txt
printf 'your-smtp-key'                > .secrets/smtp_pwd.txt
chmod 600 .secrets/*.txt

# 4. redis_pwd.txt and smtp_pwd.txt are read by PHP at runtime, so www-data
#    needs them. Grant through the group, so the file stays editable.
sudo chown "$USER":82 .secrets/redis_pwd.txt .secrets/smtp_pwd.txt
chmod 640 .secrets/redis_pwd.txt .secrets/smtp_pwd.txt

# 5. Read the administrator password once — it is generated, never displayed
cat .secrets/admin_pwd.txt

# 6. Start and watch the install run
docker compose up -d
docker compose logs -f app
```

Expect `Initializing nextcloud` followed by `Nextcloud was successfully
installed`.

Default access policy is `acc-private` + `sec-3e-spa` — reachable from LAN and
VPN, hardened headers with `SAMEORIGIN` framing, and the wider burst the sync
clients need. `acc-private` also covers the Docker gateway, which the instance
needs to run its own setup checks against itself.

Switch to `acc-public` once the instance is configured and verified.

> **If you plan to integrate OnlyOffice:** `APP_TRAEFIK_ACCESS=acc-public` is
> required. OnlyOffice makes server-to-server callbacks to Nextcloud over the
> public domain, and every restricted policy blocks them.

### Post-install

Run these once, before the first user. Each is idempotent.

```bash
# Region for phone number parsing in contacts
docker compose exec -u www-data app php occ config:system:set default_phone_region --value="AT"

# Heavy background jobs at 01:00 UTC
docker compose exec -u www-data app php occ config:system:set maintenance_window_start --value=1 --type=integer

# No example files in new accounts
docker compose exec -u www-data app php occ config:system:set skeletondirectory --value=""

# Bound preview generation — thumbnails are produced by PHP workers, and without
# a limit one large image occupies a worker long enough for users to notice
docker compose exec -u www-data app php occ config:system:set preview_max_x --value=2048 --type=integer
docker compose exec -u www-data app php occ config:system:set preview_max_y --value=2048 --type=integer
docker compose exec -u www-data app php occ config:system:set preview_max_filesize_image --value=25 --type=integer

# Restrict the administration settings to the networks you administer from.
# The rest of the instance stays reachable. These two ranges are Tailscale's —
# substitute your own, and confirm you can still reach /settings/admin.
docker compose exec -u www-data app php occ config:system:set allowed_admin_ranges 0 --value="100.64.0.0/10"
docker compose exec -u www-data app php occ config:system:set allowed_admin_ranges 1 --value="fd7a:115c:a1e0::/48"

# Send a test message before handing the instance to anyone
docker compose exec -u www-data app php occ user:welcome admin
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
docker compose exec redis sh -c \
  'redis-cli -a "$(cat /run/secrets/REDIS_PWD)" CONFIG GET maxmemory-policy'

# Confirm PHP can read the two runtime secrets as www-data — a permission problem
# here leaves the container healthy while mail and locking fail
docker compose exec -u www-data app php -r \
  'foreach (["REDIS_PWD","SMTP_PWD"] as $s) {
     printf("%s: %s\n", $s,
       @file_get_contents("/run/secrets/$s") === false ? "UNREADABLE" : "ok");
   }'

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
- `app-internal` — `app`, `db`, `redis`, `nginx`, `cron`; flagged `internal: true`, no route out
- `app-egress` — `app` and `cron` only; the narrow outbound path

The database and the cache hold everything worth stealing and reach `app-internal` alone. Only the two application containers can open outbound connections, and neither is reachable from outside — Traefik routes to `nginx`. See [Network exception](#network-exception--why-the-application-containers-reach-the-internet) for what that buys and what it costs.

### Per-service hardening

- `no-new-privileges:true` on `db`, `redis`, `nginx`
- **NOT** set on `app` and `cron` — the Nextcloud entrypoint runs as root to chown `config.php` before dropping to www-data; with `no-new-privileges` the file ends up owned by root and FPM gets a 503. Documented in the compose file.
- All six credentials → Docker Secrets (`.secrets/*.txt`): database, database root, Redis, administrator name and password, SMTP key. Nothing sensitive lives in `.env`.
- Redis reads its password from the secret at startup (`--requirepass "$(cat /run/secrets/REDIS_PWD)"`), so the value never appears in the process environment. Use `openssl rand -hex 32` — `+/=` characters break URL encoding in the PHP Redis session handler.
- `REDIS_PWD` and `SMTP_PWD` are read by PHP at request time, as `www-data`, so those two files need group access on the host. The other four are read by entrypoints running as root.

### Traefik middlewares

`nginx` carries the access and security chains and nothing else:

```text
${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file
```

`/.well-known/caldav` and `/.well-known/carddav` are handled by `nginx/nginx.conf`, which issues the `301` the project documents. An earlier Traefik middleware rewrote the path before nginx saw it, so the redirect never fired; adding one back reintroduces that.

## Network exception — why the application containers reach the internet

Every stack in this blueprint isolates its internal network. Nextcloud is a
documented exception: `app` and `cron` additionally join an egress network, while
`db` and `redis` stay isolated and cannot reach anything outside.

### What breaks without it

| Function | Needs outbound |
|---|---|
| Push notifications to the mobile apps | yes — routed via the project's push service |
| App Store, installing or updating apps from the UI | yes |
| Update notifications | yes |
| External storage mounts (S3, SMB, other clouds) | yes |
| Outgoing mail — password reset, share notifications | yes |
| Federation with other instances | yes |
| The instance's own setup checks | yes |

Without the exception, all of these fail, and every outbound attempt runs into a
timeout — the interface feels slow for a reason that has nothing to do with its
performance.

### What the exception costs, precisely

`app` and `cron` can open outbound connections. They are not reachable from
outside: only `nginx` is published through the proxy.

The data stays where it was. `db` and `redis` hold everything worth stealing and
remain on the isolated network with no route out. Verify at any time:

```bash
docker compose exec db sh -c 'timeout 4 sh -c "echo > /dev/tcp/1.1.1.1/443"' \
  && echo "unexpected: reachable" || echo "isolated"
```

### If you want it isolated anyway

Remove `app-egress` from the `app` and `cron` services. The stack runs. Accept
that mobile push, the app store, outgoing mail and external storage stop working,
that apps must be managed with `occ`, and that the interface will pause on
operations that attempt to reach the network.

That is a legitimate choice for an instance with no mobile clients and no outgoing
mail. It is not the default because most deployments need at least password reset.

### Setup checks while access is restricted

With `APP_TRAEFIK_ACCESS=acc-tailscale`, several checks report failures —
`WebdavEndpoint`, `SecurityHeaders`, `WellKnownUrls`, `OcxProviders`. The instance
calls itself through the proxy and the access policy denies it, which is the
policy working.

This is why the shipped default is `acc-private` rather than `acc-tailscale`: it
covers the Docker gateway as well as LAN and VPN, so the instance can reach
itself and the checks pass while the instance is still closed to the internet.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `nextcloud-db` · database `nextcloud` · user `nextcloud` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `db_data` (database) · `nextcloud_html` — includes `config/config.php` **and** the user data directory |
| **Reproducible** | `redis_data` — cache and file locks |
| **Quiescing** | **Maintenance mode.** Enable it before the file copy, or the database and the file tree can disagree about what exists. |

This stack uses **named volumes**; their host paths are
`/var/lib/docker/volumes/nextcloud_<name>/_data`.

```yaml
mariadb_databases:
    - name: nextcloud
      container: nextcloud-db
      username: nextcloud
      password: "{credential file /srv/docker/apps/nextcloud/.secrets/db_pwd.txt}"
```

```bash
docker compose exec -u www-data app php occ maintenance:mode --on
# … archive …
docker compose exec -u www-data app php occ maintenance:mode --off
```

**This is the stack in the repository where quiescing genuinely matters.**
Nextcloud's file index lives in the database and the files live on disk; capture
them at different moments under load and the restore shows files the index does
not know about, or index entries pointing at nothing. `occ files:scan` repairs the
first case and not the second.

`config/config.php` carries the instance secret and the passwordsalt. Restoring
the database against a regenerated config invalidates existing sessions and can
make encrypted content unreadable.

**Restore order:** database first, then the file tree, then the app — and leave
maintenance mode on until both halves are in place.

The flag itself is captured. `config.php` holds `'maintenance' => true` in any
archive taken while the quiescing hook was active, so a restored instance refuses
to serve until it is cleared:

```bash
docker compose exec -u www-data app php occ maintenance:mode --off
```

Working configuration, the run it produced and the restore rehearsal:
[`backup/borgmatic/`](../../backup/borgmatic/README.md).

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

`APP_TRAEFIK_SECURITY=sec-3e-spa`, not the generic `sec-3`. Two properties differ, and Nextcloud needs both — which is why this chain was added for it.

**Framing.** `sec-3` sets `X-Frame-Options: DENY`. Nextcloud's own setup checks require `SAMEORIGIN`, and several of its apps render in an iframe against the same origin. The `e` variants use `hdr-strict-embed`, identical to the strict headers apart from that one value.

**Burst.** Nextcloud generates continuous legitimate background traffic that does not fit a standard web application:

- Sync clients poll OCS API endpoints continuously
- WebDAV and PROPFIND requests are issued for every mounted folder
- Activity, notifications, and dashboard widgets poll at regular intervals
- Mobile clients maintain persistent connections

`rl-soft` allows 100 req/s average with a burst of 50; `rl-spa` allows the same 100 req/s average with a burst of 200. The sustained rate is unchanged — only the burst differs, so this is not a weaker limit, it is the same limit with room for a first page load that fetches a hundred assets at once.

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

```text
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

### A secret reads as `Permission denied` although the host file looks correct

```text
file_get_contents(/run/secrets/SMTP_PWD): Failed to open stream: Permission denied
```

Two distinct causes, and they look the same:

1. **Ownership.** `REDIS_PWD` and `SMTP_PWD` are read by PHP as `www-data`. Give
   the group access — `sudo chown "$USER":82` and `chmod 640`. Setting `uid` or
   `mode` on the secret in `docker-compose.yml` does nothing: Compose ignores
   both outside Swarm, and the host file's ownership is what appears in the
   container.
2. **The file was replaced.** Editors save by writing a new file and renaming it
   over the target. A bind-mounted single file resolves once, at container
   start, so the mount stays attached to the file that was replaced. `restart`
   does not re-resolve it:

   ```bash
   docker compose up -d --force-recreate app cron
   ```

   Writing in place — `printf '%s' "$KEY" > .secrets/smtp_pwd.txt` — avoids this
   entirely.

In both cases the container keeps reporting healthy. Confirm with the PHP read
test in [Verify](#verify).

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

```yaml
app: onlyoffice
getConvertedUri: from pdf to jpeg
```

If this appears when users open folders, the problem is OnlyOffice preview generation. Apply the fix in the [OnlyOffice integration notes](#onlyoffice-integration-notes) section.

**Step 4 — Check the OnlyOffice / nginx log for converter timeouts.**

```text
POST /converter?shardKey=thumb_...
upstream timed out while reading response header from upstream
whole request cycle timeout: 2m
```

If this appears, OnlyOffice is the bottleneck. Disabling OnlyOffice previews resolves this immediately without changing any timeout values.

---

## Known Issues

- **The admin overview is the acceptance test.** With this configuration it reports 60 checks passing, no warnings and no errors. Treat any warning as work to do rather than noise — the ones this stack used to carry (`.well-known URLs`, `X-Frame-Options`, `Email test`) were all real, and all three were configuration defects here rather than false positives.
- **`AppAPI deploy daemon` is unset by design** — it is needed only for external apps, which this stack does not deploy.
- **First install is slow** — the healthcheck has `start_period: 120s` because the Nextcloud installer can take over a minute to run all migrations on first boot.
- **Large file uploads need matching limits on both sides**: `PHP_UPLOAD_LIMIT` and nginx's `client_max_body_size` in `nginx/nginx.conf`.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, post-install steps, upstream diff commands
