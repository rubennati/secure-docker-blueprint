# Seafile

Self-hosted file sync + team collaboration server. This setup runs Seafile Community Edition 13 as a **multi-container stack**, split across five compose files so optional components can be toggled on or off without touching the core.

## Architecture

Seafile 13 is a collection of cooperating services, not a single container. The main server (`seafile`) is mandatory; everything else is optional and picked via the `COMPOSE_FILE` variable in `.env`.

| File | Services | Required? | Purpose |
|------|----------|-----------|---------|
| `seafile-server.yml` | `db`, `memcached`, `redis`, `seafile` | Yes | Core server + its backing services |
| `seadoc.yml` | `seadoc` | Optional | Collaborative document editor (sdoc files) |
| `notification-server.yml` | `notification-server` | Optional | Push notifications for file changes |
| `md-server.yml` | `seafile-md-server` | Optional | File metadata / extended properties |
| `thumbnail-server.yml` | `thumbnail-server` | Optional | Image and video thumbnails |

### Why split into five files

`docker compose` merges files passed via `COMPOSE_FILE` into one effective config. Each YAML is responsible for one feature and redeclares only the shared networks/secrets it actually uses. Disabling a component = remove its filename from `COMPOSE_FILE`, run `docker compose up -d`, done.

### Traefik routing

Multiple services are exposed under the same host:

- `/` → `seafile` (main UI + API)
- `/socket.io/` → `seadoc` (real-time collaboration)
- `/sdoc-server` → `seadoc` (sdoc API, prefix stripped)
- `/notification` → `notification-server` (WebSocket push)
- `/thumbnail` → `thumbnail-server`

All routers share `APP_TRAEFIK_HOST`. OnlyOffice is _not_ routed through here — it has its own domain (`ONLYOFFICE_HOST`).

### Secret handling

Seafile's init scripts (`utils.py`, `bootstrap.py`, Go binaries) don't consistently support the `_FILE` suffix. Instead, every service is started through a shared wrapper:

```text
config/entrypoint.sh  →  read /run/secrets/*  →  export as env vars  →  exec original command
```

The same `entrypoint.sh` is mounted into every Seafile service. Each secret export is conditional (`[ -f ... ] &&`), so services only see the secrets they actually need. The wrapper replaces the blueprint block in `seahub_settings.py` on every container start (skipped on first boot if the file doesn't exist yet).

Full details: [config/README.md](config/README.md).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, SEAFILE_ADMIN_EMAIL, ONLYOFFICE_HOST, TIMEZONE

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/seafile_db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/seafile_admin_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/redis_pwd.txt

# 3. SMTP secret file — always required (mounted unconditionally by compose)
# SMTP disabled:
touch .secrets/smtp_pwd.txt
# SMTP enabled (run instead of touch):
# printf '%s' '<smtp-password-or-api-key>' > .secrets/smtp_pwd.txt

# 4. (Optional) If you use OnlyOffice, reuse its JWT secret
cp ../../core/onlyoffice/.secrets/jwt_secret.txt .secrets/onlyoffice_jwt_secret.txt

# 5. Start
docker compose up -d

# 6. First startup takes 2–4 minutes (DB init, Django migrations)
docker compose logs seafile --follow
# Wait for: "Seafile server started" and Seahub to come up

# 7. Inject the blueprint custom block (always required after a fresh first boot)
# On first boot, seahub_settings.py is created by Seafile AFTER entrypoint exits,
# so the custom block (SMTP, OnlyOffice, Metadata, etc.) is always absent until
# a second container start. Recreate once:
docker compose up -d --force-recreate seafile

# 8. Verify the block is now present
docker compose exec seafile bash -lc \
  'grep -n "# --- Blueprint custom settings ---" /shared/seafile/conf/seahub_settings.py \
   || echo "STILL MISSING — check entrypoint logs"'

# 9. Open the UI and log in as SEAFILE_ADMIN_EMAIL
# Password is the value in .secrets/seafile_admin_pwd.txt
```

### First-boot blueprint injection

After the very first startup, `seahub_settings.py` exists but the blueprint
block is always absent — `entrypoint.sh` ran before Seafile generated the file.
Custom settings (SMTP, OnlyOffice, Metadata, Thumbnail) are not active until
the second container start (setup step 7 above).

**Symptom:** "Email service is not properly configured", OnlyOffice unavailable,
or metadata/thumbnail features missing immediately after a fresh install.

**Fix** (this is setup step 7):

```bash
docker compose up -d --force-recreate seafile
```

**Verify all custom settings were injected:**

```bash
docker compose exec seafile bash -lc \
  'grep -n "# --- Blueprint custom settings ---\|EMAIL_\|DEFAULT_FROM_EMAIL\|ONLYOFFICE_\|ENABLE_METADATA_MANAGEMENT\|ENABLE_VIDEO_THUMBNAIL" \
   /shared/seafile/conf/seahub_settings.py'
```

### SMTP

SMTP is configured through four layers:

```text
.env (SEAFILE_SMTP_*)
  → .secrets/smtp_pwd.txt  (Docker secret SEAFILE_SMTP_PWD)
    → entrypoint.sh        (exports SEAFILE_SMTP_PASSWORD)
      → seahub_custom.py   (replaces EMAIL_* block in seahub_settings.py on each start)
```

The entrypoint replaces the blueprint block in `seahub_settings.py` on every container start. On a fresh install the block is skipped if `seahub_settings.py` doesn't exist yet; it is injected after the first boot when you recreate the container.

#### SMTP disabled

Leave `SEAFILE_SMTP_HOST` empty in `.env`. No `EMAIL_*` settings are written.

The Docker secret file must still exist because compose mounts it unconditionally:

```bash
touch .secrets/smtp_pwd.txt
```

#### Enable SMTP during first setup

Do this **before** the first `docker compose up`.

**1. Fill in `.env`:**

```env
SEAFILE_SMTP_HOST=smtp-relay.example.com
SEAFILE_SMTP_PORT=587
SEAFILE_SMTP_USER=example-user
SEAFILE_SMTP_USE_TLS=true
SEAFILE_SMTP_FROM=Seafile <seafile@example.com>
```

For implicit SSL on port 465: set `SEAFILE_SMTP_PORT=465` and `SEAFILE_SMTP_USE_TLS=false`.

**2. Write the password:**

```bash
printf '%s' '<smtp-password-or-api-key>' > .secrets/smtp_pwd.txt
```

**3. Start the stack:**

```bash
docker compose up -d
```

**4. Inject and verify** — the blueprint block is always absent after the first boot. Run setup steps 7–8 to inject it (recreate + verify), then see [Verify SMTP](#verify-smtp).

#### Enable or change SMTP after first boot

**1. Update `.env` and/or `.secrets/smtp_pwd.txt` with the new values.**

**2. Recreate the container** — entrypoint replaces the custom block automatically on start:

```bash
docker compose up -d --force-recreate seafile
```

**3. Verify** — see below.

#### Verify SMTP

Check injected mail settings:

```bash
docker compose exec seafile bash -lc \
  'grep -n "EMAIL_\|DEFAULT_FROM_EMAIL\|SERVER_EMAIL" /shared/seafile/conf/seahub_settings.py'
```

Check the password line without exposing it:

```bash
docker compose exec seafile bash -lc \
  'grep -n "EMAIL_HOST_PASSWORD" /shared/seafile/conf/seahub_settings.py | sed "s/=.*/= ***hidden***/"'
```

Check container env and mounted secrets:

```bash
docker compose exec seafile bash -lc 'env | grep SEAFILE_SMTP'
docker compose exec seafile bash -lc 'find /run/secrets -maxdepth 1 -type f -printf "%f bytes=%s\n"'
```

Test TCP reachability from inside the container:

```bash
docker compose exec seafile bash -lc 'python3 - <<EOF
import os, socket
host = os.environ.get("SEAFILE_SMTP_HOST")
port = int(os.environ.get("SEAFILE_SMTP_PORT", "587"))
if not host:
    raise SystemExit("SEAFILE_SMTP_HOST is empty")
socket.create_connection((host, port), timeout=10).close()
print("OK connected")
EOF'
```

Watch Seahub logs for delivery status:

```bash
docker compose exec seafile bash -lc 'tail -f /shared/seafile/logs/seahub.log'
```

End-to-end test — trigger a real delivery to confirm the full chain works:

- **Add a user:** Seahub admin panel → System Admin → Users → Add User (sends invitation email)
- **Password reset:** click "Forgot password?" on the login page and enter a valid address

If the email arrives, SMTP is fully configured end-to-end.

#### Troubleshooting

If the UI shows **"Email service is not properly configured"**, check in order:

- `SEAFILE_SMTP_HOST` is set in `.env`
- `.secrets/smtp_pwd.txt` exists and is not empty
- `/run/secrets/SEAFILE_SMTP_PWD` is present inside the container (check with `find /run/secrets` above)
- `SEAFILE_SMTP_PASSWORD` is exported (`env | grep SEAFILE_SMTP`)
- `EMAIL_*` settings exist in `seahub_settings.py` (check with `grep` above)
- If `EMAIL_*` settings are missing from `seahub_settings.py`:
  - Fresh install: block was skipped on first boot — `docker compose up -d --force-recreate seafile` injects it
  - After a settings change: same command — entrypoint replaces the block automatically
- SMTP host and port are reachable (TCP test above)
- Provider accepts the sender address or domain — check `/shared/seafile/logs/seahub.log`

### WebDAV

> **WebDAV is a compatibility interface, not a primary access path.** Seafile officially recommends WebDAV only for occasional access. For normal use, prefer the Seafile Sync Client, SeaDrive, or the mobile apps — they are significantly faster and more reliable.

Enable in `.env`:

```env
SEAFILE_ENABLE_WEBDAV=true
```

Then restart:

```bash
docker compose up -d --force-recreate seafile
```

> `seafdav.conf` is generated on first boot. WebDAV takes effect from the **second start**.

Mount in macOS Finder: **Go → Connect to Server** → `https://<APP_TRAEFIK_HOST>/seafdav/`.

#### Authentication

WebDAV and Seahub (the web UI) use different authentication paths. What works in the browser does not necessarily work in WebDAV.

**Use these credentials:**

- **Username**: Seafile login email (e.g. `user@example.com`)
- **Password**: account password — **not** the WebDAV token shown in the profile UI

**The WebDAV token (`ENABLE_WEBDAV_SECRET`) shown in the Seafile profile is unreliable in Seafile 13 Docker setups.** Community reports confirm it does not work consistently. The token is intended for 2FA/SSO scenarios where Basic Auth cannot do interactive authentication. For standard setups, use the account password.

If login fails, work through this matrix:

| Try | Username | Password |
|-----|----------|----------|
| 1 | email address | account password ← most likely to work |
| 2 | login ID / user ID | account password |
| 3 | email address | app password (if configured) |
| 4 | email address | WebDAV token (from profile) |

Also check: is the account local, LDAP, OAuth, or Guest? WebDAV Basic Auth only works reliably with local accounts. Guest accounts are blocked.

#### Diagnosis

```bash
# Check seafdav is running
docker compose exec seafile ps aux | grep dav

# Check seafdav config
docker compose exec seafile cat /shared/seafile/conf/seafdav.conf

# Watch auth failures live
docker compose exec seafile tail -f /shared/seafile/logs/seafdav.log
```

#### When not to use WebDAV

Avoid WebDAV for:

- large uploads
- many small files
- permanent network drive mounts
- performance-sensitive workflows

Use instead: **Seafile Sync Client**, **SeaDrive**, mobile app, or web UI.

### Turning components off

```bash
# In .env, remove the files you don't want:
COMPOSE_FILE=seafile-server.yml,thumbnail-server.yml
# Then:
docker compose up -d --remove-orphans
```

## Verify

```bash
docker compose ps                           # All configured services Up
docker compose logs seafile --tail 100      # Django + FastCGI started
docker compose logs db --tail 20            # MariaDB ready for connections
curl -fsSI https://<APP_TRAEFIK_HOST>/      # 302 to /accounts/login/
```

Test SeaDoc (if enabled):

```bash
curl -fsSI https://<APP_TRAEFIK_HOST>/sdoc-server/
```

Test notification-server (if enabled):

```bash
curl -fsSI https://<APP_TRAEFIK_HOST>/notification/
```

## Security Model

- Database, Redis, and Memcached are only on `app-internal` (which is `internal: true`). None of them can reach the outside network directly.
- The `seafile` main container is on both `proxy-public` (for Traefik) and `app-internal` (for DB + Redis). The optional web-facing services (`seadoc`, `notification-server`, `thumbnail-server`) follow the same pattern.
- Most secrets live as Docker Secrets under `./.secrets/`. The wrapper entrypoint converts them to env vars inside the container. **Exception:** `thumbnail-server` does not use the entrypoint wrapper, so `JWT_PRIVATE_KEY` and `SEAFILE_MYSQL_DB_PASSWORD` must be set as direct environment variables in `.env` matching the secret file contents.
- `no-new-privileges:true` on every service.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `seafile-db` · **three databases**: `ccnet_db`, `seafile_db`, `seahub_db` · user `seafile` |
| **Password** | `.secrets/seafile_db_pwd.txt` |
| **State** | `./volumes/mysql` (databases) · **`./volumes/seafile-data`** — the file store · `./volumes/seadoc-data` |
| **Reproducible** | `./volumes/redis` (cache) · `./volumes/seafile-data/seafile/logs` |
| **Quiescing** | Not needed for the dumps. Seafile writes content-addressed blocks, so a file captured mid-write is a new block rather than a corrupted one. |

```yaml
mariadb_databases:
    - name: ccnet_db
      container: seafile-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile/.secrets/seafile_db_pwd.txt}"
    - name: seafile_db
      container: seafile-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile/.secrets/seafile_db_pwd.txt}"
    - name: seahub_db
      container: seafile-db
      username: seafile
      password: "{credential file /srv/docker/apps/seafile/.secrets/seafile_db_pwd.txt}"
```

**Three databases, not one.** Backing up only `seafile_db` is the classic mistake
here: it holds the file metadata, while `ccnet_db` holds users and groups and
`seahub_db` holds the web layer, shares and links. Any one missing produces a
restore that starts and is unusable.

`volumes/seafile-data` holds the blocks the metadata points at. Restore the
databases and the block store from the same archive — a newer block store with an
older database means files exist that no library references.

**Restore order:** databases first, then the block store, then the app.

## Access policy — OnlyOffice + SeaDoc require `acc-private`

`acc-tailscale` blocks server-to-server callbacks from Docker containers (their IPs are RFC1918, not Tailscale). This breaks both OnlyOffice document editing and SeaDoc collaborative editing:

- **OnlyOffice**: fetches and saves files via callback to Seafile's URL. The OnlyOffice container IP is not a Tailscale IP → Traefik blocks it → documents fail to open/save.
- **SeaDoc**: makes internal API calls back to Seafile for token validation and file content. Same issue.

**Fix: set `ACC_TAILSCALE` → `acc-private` in `.env`:**

```env
APP_TRAEFIK_ACCESS=acc-private
```

`acc-private` = Tailscale/VPN + LAN (RFC1918). Docker container IPs (172.x.x.x) fall into the LAN range and pass. External internet still blocked.

> If you run Seafile without OnlyOffice and without SeaDoc, `acc-tailscale` works fine.

## Thumbnail server

The thumbnail server has one important difference from every other Seafile service in this blueprint: it does **not** use the shared `entrypoint.sh` wrapper. This means Docker Secrets `_FILE` paths are never read inside that container. `JWT_PRIVATE_KEY` and `SEAFILE_MYSQL_DB_PASSWORD` must be supplied as direct environment variables, which means they must be in `.env`.

### Thumbnail 403 Forbidden

If `/thumbnail/...` requests return 403, there are two independent root causes:

1. **Missing `JWT_PRIVATE_KEY`** — the thumbnail container started without the key. Verify without printing the secret:

   ```bash
   docker compose exec thumbnail-server sh -lc 'printenv JWT_PRIVATE_KEY | wc -c'
   # Expected: non-zero byte count (e.g. 65)
   # If 0: JWT_PRIVATE_KEY is not in .env, or .env was not loaded
   docker compose exec thumbnail-server sh -lc 'printenv SEAFILE_MYSQL_DB_PASSWORD | wc -c'
   # Expected: non-zero byte count
   ```

2. **Traefik router priority** — the main `seafile` router (catch-all for `Host(…)`) intercepts `/thumbnail/…` before the dedicated thumbnail router. Verify:

   ```bash
   docker inspect seafile-thumbnail \
     --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
     | grep -E "traefik.http.routers.*(rule|priority)"
   # Expected: priority=100 on the thumbnail router

   docker inspect seafile-app \
     --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
     | grep -E "traefik.http.routers.*(rule|priority)"
   # Expected: priority=1 on the main router
   ```

### Production rollout

If applying this fix to a running deployment:

1. Back up `.env` and the compose files.
2. Add `JWT_PRIVATE_KEY` and `SEAFILE_MYSQL_DB_PASSWORD` to `.env` (values must match `.secrets/jwt_key.txt` and `.secrets/seafile_db_pwd.txt`).
3. Validate the merged compose config:

   ```bash
   docker compose config --quiet
   ```

4. Recreate only the affected containers:

   ```bash
   docker compose up -d --force-recreate seafile thumbnail-server
   ```

5. Verify the key is now present (non-zero byte count, no secret printed):

   ```bash
   docker compose exec thumbnail-server sh -lc 'printenv JWT_PRIVATE_KEY | wc -c'
   ```

6. Test thumbnail generation — request a thumbnail URL in the browser and confirm it no longer returns 403.

## Known Issues

- **MariaDB `Aborted connection` / `Got an error reading communication packets` warnings** — MariaDB 10.11 logs these during normal Seafile operation (browsing, uploads, thumbnail generation). They appear because Seafile's sidecar services and Django workers do not always close DB connections with a clean MySQL-protocol shutdown. `Aborted_connects = 0` confirms no authentication failures. `Max_used_connections` well below `max_connections` confirms no exhaustion. Classify as known background noise; monitor the `Aborted_clients` growth rate before tuning anything. Full analysis: [docs/bugfixes/seafile-ce-mariadb-aborted-connections-2026-06-15.md](../../docs/bugfixes/seafile-ce-mariadb-aborted-connections-2026-06-15.md).

- **Redis `WARNING Memory overcommit must be enabled`** — Redis logs this warning on Docker hosts where `vm.overcommit_memory` is not set to 1. It does not prevent Redis from starting but can cause data loss under memory pressure. Fix on the Docker host:

  ```bash
  # Immediate (survives until next reboot)
  sudo sysctl vm.overcommit_memory=1

  # Permanent
  echo 'vm.overcommit_memory = 1' | sudo tee /etc/sysctl.d/99-redis-overcommit.conf
  sudo sysctl --system
  ```

- **First boot is slow** (2–4 min). The main server's healthcheck uses `start_period: 180s` for this reason.
- **SeaDoc + Notification server images are tagged `:13.0-latest` / `:2.0-latest`.** These are moving tags; pin to a concrete digest in production if you want reproducible builds.
- **`seahub_custom.py` is always skipped on first boot.** `seahub_settings.py` doesn't exist when `entrypoint.sh` runs; Seafile generates it after `exec` exits into the init system. After first startup completes, run `docker compose up -d --force-recreate seafile` (setup step 7) to inject the block. See [config/README.md](config/README.md).
- **Env var naming is inconsistent with the rest of the repo.** `.env.example` still uses `APP_IMAGE=…:tag` (not split into `*_TAG`) and `TIMEZONE` (not `TZ`). Unifying this would touch all five YAMLs simultaneously — left for a dedicated refactor with testing, not mixed into a documentation pass.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, version notes
- [config/README.md](config/README.md) — entrypoint wrapper mechanics and `seahub_custom.py` injection
