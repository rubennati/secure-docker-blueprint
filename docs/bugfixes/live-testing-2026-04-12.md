# Live Testing Bug Fixes — 2026-04-12

First deployment of the blueprint to a live server. This document captures every
bug found during testing, root cause analysis, and the applied fix.

---

## 1. Traefik TLS options not found (`tls-basic@docker`)

**Symptom:** Traefik dashboard showed `unknown TLS options: tls-basic@docker` for
every router. Services were unreachable via HTTPS.

**Root cause:** All compose files had `tls.options=${APP_TRAEFIK_TLS_OPTION}`
without the `@file` suffix. Traefik looked in its docker provider (where the
option doesn't exist) instead of the file provider where `tls-basic`, `tls-aplus`
and `tls-modern` are defined.

**Fix:** Added `@file` suffix to every TLS options label across all 12+ compose
files:

```yaml
# Before (broken)
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}"
# After (fixed)
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
```

**Affected files:** All `docker-compose.yml` in `apps/`, `core/`, `docs/templates/`.

---

## 2. Certresolver commented out (wildcard certificate)

**Symptom:** N/A — preemptive fix. The server uses a wildcard certificate managed
outside of Traefik, so `tls.certresolver` must be disabled.

**Fix:** Commented out certresolver in all compose files:

```yaml
#- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
```

**Note:** The variable `APP_TRAEFIK_CERT_RESOLVER` remains in `.env.example` for
users who need per-domain certificates. Uncomment the label to activate.

---

## 3. Whoami healthcheck fails (no curl/wget in image)

**Symptom:** `traefik/whoami` container stuck in `health: starting`, eventually
marked unhealthy.

**Root cause:** Healthcheck used `wget` but the whoami image is a minimal Go
binary with no shell tools (no wget, no curl, no sh).

**Fix:** Removed healthcheck entirely:

```yaml
# No healthcheck — minimal Go binary without curl/wget.
```

---

## 4. Dockhand healthcheck fails (wget not found)

**Symptom:** `dockhand` container stuck in `health: starting`.

**Root cause:** Healthcheck used `wget` but the `fnsys/dockhand` image ships
`curl` (at `/usr/sbin/curl`) not `wget`.

**Fix:** Switched to curl:

```yaml
test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1 || exit 1"]
```

**Lesson:** Always verify which HTTP client is available in the target image
before writing healthchecks.

---

## 5. HAProxy `normalize-uri` requires experimental directive

**Symptom:** `tecnativa/docker-socket-proxy` crashed on start. HAProxy log:

```
'normalize-uri' requires 'expose-experimental-directives'
```

**Root cause:** HAProxy 3.2.4 (bundled in the proxy image) moved `normalize-uri`
behind an experimental flag. The blueprint's HAProxy config template used this
directive without the required opt-in.

**Fix:** Added `expose-experimental-directives` to the HAProxy global section in
`core/traefik/ops/templates/haproxy.cfg.template.tmpl`:

```
global
    expose-experimental-directives
    log stdout format raw daemon "${DSP_LOG_LEVEL}"
```

---

## 6. Seafile: Missing Redis service (500 error)

**Symptom:** Seafile web UI returned HTTP 500. Seahub log:

```
redis.exceptions.ConnectionError: Error 111 connecting to redis:6379.
Connection refused.
```

**Root cause:** Seafile 13 requires Redis (new dependency vs v12). Our initial
compose had no Redis service.

**Fix:** Added Redis service to `seafile-server.yml` with password authentication
via Docker Secret:

```yaml
redis:
  image: ${REDIS_IMAGE}
  command: ["sh", "-c", "redis-server --requirepass \"$$(cat /run/secrets/REDIS_PWD)\""]
  secrets:
    - REDIS_PWD
```

Added cache env vars to seafile service:

```yaml
CACHE_PROVIDER: redis
REDIS_HOST: redis
REDIS_PORT: "6379"
```

---

## 7. Seafile: Passwords not injected (`_FILE` not supported)

**Symptom:** Seafile couldn't connect to DB on first boot. Init scripts failed
with empty password.

**Root cause:** Seafile's Python init scripts (`utils.py`, `bootstrap.py`) use
`os.environ.get()` only — they have no `_FILE` suffix support. Setting
`DB_PASSWORD_FILE` did nothing; the actual `SEAFILE_MYSQL_DB_PASSWORD` env var
remained empty.

**Fix:** Created `config/entrypoint.sh` — a shared wrapper script that reads
Docker Secrets from `/run/secrets/` and exports them as plain environment
variables before exec'ing the original service command:

```sh
#!/bin/sh
set -e
[ -f /run/secrets/SEAFILE_DB_PWD ] && \
  export SEAFILE_MYSQL_DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)"
  export DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)"
[ -f /run/secrets/JWT_KEY ] && \
  export JWT_PRIVATE_KEY="$(cat /run/secrets/JWT_KEY)"
# ... more secrets ...
exec "$@"
```

Used by **all** Seafile services (main, seadoc, notification, md-server).

---

## 8. Seafile: Healthcheck start_period too short

**Symptom:** Container marked unhealthy during first boot while Seafile was still
running database migrations.

**Root cause:** `start_period: 60s` is not enough for initial setup (DB creation,
migrations, etc.).

**Fix:** Increased to `start_period: 180s` and `retries: 10`.

---

## 9. Seafile: Missing v13 environment variables

**Symptom:** Various features not working after initial boot. 500 errors from
Redis connection failures.

**Root cause:** Our compose was based on incomplete configuration. The official
Seafile 13 compose includes several new env vars not present in v12.

**Fix:** Added all missing v13 env vars to `seafile-server.yml`:

```yaml
CACHE_PROVIDER: redis
REDIS_HOST: redis
REDIS_PORT: "6379"
ENABLE_GO_FILESERVER: "true"
INNER_NOTIFICATION_SERVER_URL: http://notification-server:8083
SEAFILE_MYSQL_DB_HOST: db
SEAFILE_MYSQL_DB_USER: ${SEAFILE_DB_USER}
```

---

## 10. Notification & Metadata servers: `_FILE` env vars not supported

**Symptom:** Both services crashed in restart loops immediately after start.
Metadata server log:

```
[ERROR] The Metadata server only can run with Redis!
```

Notification server exited with code 1 (no log output).

**Root cause:** These are Go binaries / bash-wrapped services — they read env vars
directly (no `_FILE` suffix support). Our config used `SEAFILE_MYSQL_DB_PASSWORD_FILE`
and `JWT_PRIVATE_KEY_FILE` which were silently ignored, leaving the actual
variables empty.

**Fix:** Removed all `_FILE` env vars. Instead, mounted the shared `entrypoint.sh`
and overrode entrypoint/command to wrap the original service binary:

```yaml
# notification-server (Go binary)
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
command: ["/opt/seafile/notification-server", "-c", "/opt/seafile", "-l", "/shared/seafile/logs/notification-server.log"]

# md-server (bash script)
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
command: ["bash", "-c", "/opt/scripts/entrypoint.sh"]
```

Original commands determined via `docker inspect --format='{{json .Config.Cmd}}'`.

Added `CACHE_PROVIDER`, `REDIS_HOST`, `REDIS_PORT` to md-server (required for
Redis cache), plus `depends_on: redis` with health condition.

---

## 11. SeaDoc: 403 on document load (`_FILE` not supported + wrong image)

**Symptom:** Opening `.sdoc` files showed "Load doc content error". Browser
console: `403` on `/sdoc-server/api/v1/...`.

**Root cause:** Two issues:
1. SeaDoc also doesn't support `_FILE` env vars. `JWT_PRIVATE_KEY_FILE` was
   ignored → JWT validation failed → 403.
2. Image version `1.0-latest` was outdated. Seafile 13 requires `2.0-latest`.

**Fix:**
- Same `entrypoint.sh` wrapper as other services
- Updated image to `seafileltd/sdoc-server:2.0-latest`
- Separated Traefik routing: dedicated router for `/socket.io/` (no path
  stripping) and `/sdoc-server` (with strip prefix middleware)

---

## 12. Metadata server: Feature not visible in UI

**Symptom:** Metadata server running, but no "Extended properties" option in
Library Settings dialog.

**Root cause:** Metadata management must be explicitly enabled in
`seahub_settings.py` — it's not an env var that Docker maps automatically:

```python
ENABLE_METADATA_MANAGEMENT = True
METADATA_SERVER_URL = 'http://seafile-md-server:8084'
```

**Fix:** Created `config/seahub_custom.py` with custom settings, mounted into
the container. The `entrypoint.sh` appends these settings to the auto-generated
`seahub_settings.py` on first boot (marker-based, runs only once):

```sh
MARKER="# --- Blueprint custom settings ---"
if ! grep -q "$MARKER" "$SEAHUB_CONF" 2>/dev/null; then
    printf '\n%s\n' "$MARKER" >> "$SEAHUB_CONF"
    cat "$CUSTOM_CONF" >> "$SEAHUB_CONF"
fi
```

After enabling globally, the feature must also be activated **per Library**
(Library → Settings → "Enable extended properties").

---

## 13. Seafile satellite files: Missing Traefik fixes

**Symptom:** SeaDoc, notification-server, and thumbnail-server still had
`certresolver` active (not commented) and missing `@file` on `tls.options`.

**Root cause:** These files use `.yml` extension (not `docker-compose.yml`) and
were missed during the initial bulk fix.

**Fix:** Applied same Traefik label fixes to all satellite files:
- Commented out `certresolver`
- Added `tls.options=${APP_TRAEFIK_TLS_OPTION}@file`

---

## Key Lessons

1. **Always check official docs for the exact version** — Seafile 13 has
   significant changes vs v12 (Redis requirement, new env vars, new image tags).

2. **Never assume `_FILE` support** — only images that explicitly implement it
   (usually via shell entrypoint scripts) support reading secrets from files.
   Go binaries and many Python apps do not.

3. **Verify healthcheck tools** — don't assume curl or wget exist. Check with
   `docker exec <container> which curl wget` before writing healthchecks.

4. **Traefik provider suffixes matter** — `@file` and `@docker` are not
   interchangeable. Options defined in file provider need `@file`.

5. **Entrypoint wrapper pattern** — a shared script that reads secrets and
   exports env vars before `exec "$@"` is a reliable pattern for images without
   native `_FILE` support.
