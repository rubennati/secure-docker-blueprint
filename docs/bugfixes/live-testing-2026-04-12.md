# Cross-cutting bugs — 2026-04-12

Bugs encountered during early deployment runs, with root cause analysis and the
applied fix. Each item is phrased for a fork maintainer hitting the same issue.

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

## 14. OnlyOffice: Blocked by `X-Frame-Options: DENY`

**Symptom:** Clicking a `.docx` in Seafile opened a blank white iframe. Browser
console:

```
Refused to display 'https://office.example.com/' in a frame because it set
'X-Frame-Options' to 'deny'.
```

**Root cause:** All Traefik security middleware levels (`sec-1` through `sec-4`)
chain `sec-headers-basic`, which sets `frameDeny: true`. This adds
`X-Frame-Options: DENY` to every response — but OnlyOffice **must** be embedded
in iframes by Seafile/Nextcloud to function.

**Fix:** Replaced `APP_TRAEFIK_SECURITY` with a custom Docker-level middleware
(`onlyoffice-headers@docker`) that has the same protections as `sec-headers-basic`
but without `frameDeny`. Instead, iframe embedding is controlled via
`Content-Security-Policy: frame-ancestors`:

```yaml
# Custom security headers: same as sec-headers-basic but frameDeny=false
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.browserXssFilter=true"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.contentTypeNosniff=true"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.forceSTSHeader=true"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.stsSeconds=63072000"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-headers.headers.contentSecurityPolicy=frame-ancestors 'self' https://${ONLYOFFICE_ALLOWED_ORIGIN}"
```

`ONLYOFFICE_ALLOWED_ORIGINS` lists the domains allowed to embed OnlyOffice
(e.g. `https://files.example.com https://cloud.example.com`).

**Why not just disable `frameDeny` in `sec-headers-basic`?** That would weaken
security for all other services. The per-container middleware approach keeps the
exception isolated to OnlyOffice.

---

## 15. OnlyOffice: JWT authentication fails (`_FILE` not supported)

**Symptom:** Document opened in Seafile but showed "Download failed" with JWT
token error in OnlyOffice logs.

**Root cause:** OnlyOffice Document Server reads `JWT_SECRET` from environment
only — no `JWT_SECRET_FILE` or `_FILE` convention support.

**Fix:** Same pattern as Seafile services — created `config/entrypoint.sh` that
reads the Docker Secret and exports it as a plain env var:

```sh
#!/bin/bash
set -e
[ -f /run/secrets/ONLYOFFICE_JWT_SECRET ] && \
  export JWT_SECRET="$(cat /run/secrets/ONLYOFFICE_JWT_SECRET)"
exec "$@"
```

Original command determined via `docker inspect`:
`ENTRYPOINT=["/app/ds/run-document-server.sh"]`, `CMD=null`.

```yaml
entrypoint: ["/bin/bash", "/config/entrypoint.sh", "/app/ds/run-document-server.sh"]
```

---

## 16. OnlyOffice: "Download failed" — Mixed Content (HTTP URLs behind HTTPS proxy)

**Symptom:** Document opened but content wouldn't load. "Download failed" error
in OnlyOffice editor. Browser console:

```
Mixed Content: The page at 'https://files.example.com/...' was loaded over HTTPS,
but requested an insecure XMLHttpRequest endpoint
'http://office.example.com/cache/files/data/...'
This request has been blocked; the content must be served over HTTPS.
```

**Root cause:** OnlyOffice sits behind Traefik's TLS termination. Internally,
Traefik forwards traffic to the container over plain HTTP on port 80. OnlyOffice's
internal nginx uses `X-Forwarded-Proto` to determine the client-facing scheme.
Without this header, it defaults to `http://` and generates HTTP URLs for all file
cache/download endpoints — which browsers block as Mixed Content on HTTPS pages.

The relevant nginx config inside OnlyOffice:

```nginx
map $http_x_forwarded_proto $the_scheme {
    default $http_x_forwarded_proto;
    "" $scheme;
}
proxy_set_header X-Forwarded-Proto $the_scheme;
```

And in the Node.js backend (`utils.js → getBaseUrl()`):

```javascript
// Priority: X-Forwarded-Proto header → req.protocol → "http"
```

**Fix:** Added a Traefik middleware that explicitly sets `X-Forwarded-Proto: https`
and `X-Forwarded-Host` on every request to OnlyOffice:

```yaml
# Proxy headers: tell OnlyOffice it's behind TLS termination
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-proto.headers.customrequestheaders.X-Forwarded-Proto=https"
- "traefik.http.middlewares.${COMPOSE_PROJECT_NAME}-proto.headers.customrequestheaders.X-Forwarded-Host=${APP_TRAEFIK_HOST}"
```

Chained into the router middleware stack:

```yaml
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${COMPOSE_PROJECT_NAME}-proto@docker,${COMPOSE_PROJECT_NAME}-headers@docker"
```

**Why doesn't Traefik set this automatically?** Traefik does add forwarded headers
by default, but only when `entryPoints.websecure.forwardedHeaders` is configured
to trust the source. The explicit middleware approach is more reliable and
self-documenting — it works regardless of Traefik's global forwarded-headers
configuration.

**Alternative (workaround, not recommended):** Adding
`upgrade-insecure-requests` to the CSP header tells browsers to silently rewrite
HTTP sub-requests to HTTPS. This masks the problem but doesn't fix the root cause.

---

## 17. Paperless-ngx: Tika image tag `3.1` does not exist

**Symptom:** `docker compose up -d` failed immediately:

```
Error response from daemon: failed to resolve reference "docker.io/apache/tika:3.1": not found
```

**Root cause:** Apache Tika uses four-part version tags (`3.1.0.0`, `3.2.0.0`,
etc.). The shorthand `3.1` does not exist on Docker Hub.

**Fix:** Changed `.env.example`:

```env
# Before
TIKA_IMAGE=apache/tika:3.1
# After
TIKA_IMAGE=apache/tika:3.1.0.0
```

**Lesson:** Always verify that the exact image tag exists on the registry before
adding it to the blueprint. Use `docker pull` or check Docker Hub tags page.

---

## 18. Paperless-ngx: s6-overlay crash (`/run belongs to uid 0`)

**Symptom:** App container in restart loop. Log:

```
/package/admin/s6-overlay/libexec/preinit: fatal: /run belongs to uid 0 instead
of 1000, has insecure and/or unworkable permissions
s6-overlay-suexec: fatal: child failed with exit code 100
```

**Root cause:** The compose file set `user: "${USERMAP_UID}:${USERMAP_GID}"`
which forces the entire container to run as UID 1000 from the start. But
Paperless-ngx uses **s6-overlay** as its init system, which must start as root
to set up `/run`, `/tmp`, fix file permissions, etc. It then drops privileges
to the configured user internally via the `USERMAP_UID`/`USERMAP_GID`
environment variables.

The Docker `user:` directive bypasses this init process entirely.

**Fix:** Removed `user:` directive. Added `USERMAP_UID`/`USERMAP_GID` as
environment variables instead:

```yaml
# Before (broken)
user: "${USERMAP_UID}:${USERMAP_GID}"

# After (correct)
environment:
  USERMAP_UID: ${USERMAP_UID}
  USERMAP_GID: ${USERMAP_GID}
```

**Rule of thumb:** Never set `user:` in compose when the image uses s6-overlay,
supervisord, or any init system that needs root at startup. Check if the image
provides its own UID/GID mechanism via env vars.

---

## 19. Paperless-ngx: DB password authentication failed (trailing newline)

**Symptom:** App connected to PostgreSQL but authentication failed:

```
FATAL: password authentication failed for user "paperless_user"
```

Paperless also logged a warning:

```
[env-init] Your secret: PAPERLESS_DBPASS_FILE contains a trailing newline
and may not work as expected
```

**Root cause:** Secrets generated with `openssl rand -base64 32 > file.txt`
include a trailing newline (`\n`). PostgreSQL's `POSTGRES_PASSWORD_FILE` reads
the file **including** the newline and stores it as part of the password hash.
Paperless reads the same file but **strips** the newline before connecting →
password mismatch.

**Fix:**
1. Strip newlines from secret generation commands across all `.env.example` files:

```bash
# Before
openssl rand -base64 32 > secrets/db_pwd.txt
# After
openssl rand -base64 32 | tr -d '\n' > secrets/db_pwd.txt
```

2. For existing deployments, strip newlines from existing secrets and recreate
   the DB volume:

```bash
docker compose down
cd secrets && for f in *.txt; do printf '%s' "$(cat "$f")" > "$f"; done && cd ..
rm -rf volumes/postgres
docker compose up -d
```

**Applied to:** All 25 secret generation commands across 11 `.env.example` files.

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

6. **TLS-terminating proxies need explicit forwarded headers** — when a reverse
   proxy terminates TLS and forwards plain HTTP to backends, the backend must
   know the original scheme was HTTPS. Always set `X-Forwarded-Proto: https`
   explicitly via middleware rather than relying on automatic behavior.

7. **iframe-embedded services need custom security headers** — standard security
   middleware with `frameDeny: true` blocks iframe embedding. For services that
   must be embedded (OnlyOffice, collaborative editors), create a per-container
   middleware with `Content-Security-Policy: frame-ancestors` instead. Keep
   this exception isolated — don't weaken global security settings.

8. **Test the full chain, not just the UI** — OnlyOffice loading its editor
   iframe (Bug #14) was only step one. The actual document content is fetched
   via separate XHR requests (Bug #16) that can fail independently. Always
   test the complete workflow (open → edit → save) to catch all integration
   issues.

9. **Never set `user:` with s6-overlay images** — images using s6-overlay
   (Paperless, Linuxserver.io images) must start as root. They drop
   privileges internally via `USERMAP_UID`/`USERMAP_GID` or `PUID`/`PGID`
   env vars. Setting Docker's `user:` directive bypasses the init system.

10. **Always strip newlines from generated secrets** — `openssl rand -base64`
    appends `\n`. Some apps include it in the password, others strip it →
    mismatch. Use `| tr -d '\n'` on every secret generation command.

11. **Verify image tags on the registry** — not all projects use the same
    versioning scheme. Apache Tika uses four-part versions (`3.1.0.0`), not
    shorthand (`3.1`). Always `docker pull` or check the tags page first.
