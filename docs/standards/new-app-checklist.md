# New App Checklist

Step-by-step checklist when adding a new app to the blueprint.
Each item links to the relevant standard or lesson learned.

---

## 1. Research the Image

Before writing any YAML, answer these questions:

- [ ] **What is the exact image tag?** Check Docker Hub / GHCR for the correct
  version format. Some projects use non-standard tags (e.g. `apache/tika:3.1.0.0`
  not `3.1`). Always verify the tag exists with `docker pull`.

- [ ] **Does the image support `_FILE` env vars?** Check the image docs or
  entrypoint script. If not, you need a custom entrypoint wrapper.
  See [Security Baseline > Pattern 2](security-baseline.md).
  *Known unsupported:* OnlyOffice, Seafile (all services), Vaultwarden, Dockhand.

- [ ] **What init system does it use?** Check for s6-overlay, supervisord, or
  similar. If present, **never** set `user:` in compose — the init system must
  start as root and drops privileges via env vars (`USERMAP_UID`/`USERMAP_GID`
  or `PUID`/`PGID`).

- [ ] **What tools are available inside the container?** For healthchecks, check
  if `curl`, `wget`, or other tools exist. Minimal/distroless images may have
  nothing. Run `docker run --rm <image> which curl wget` to verify.

- [ ] **What is the original ENTRYPOINT/CMD?** If you need a custom entrypoint,
  you must know the original command to pass through. Check with:
  ```bash
  docker inspect --format='{{json .Config.Entrypoint}} {{json .Config.Cmd}}' <image>
  ```

- [ ] **Does the app need to be embedded in iframes?** (OnlyOffice, collaborative
  editors). If yes, you cannot use standard `sec-*` middlewares (they set
  `frameDeny: true`). Create a custom Docker-level middleware with
  `frame-ancestors` CSP instead.

- [ ] **Does the app generate URLs?** If it sits behind a TLS-terminating proxy,
  it may generate `http://` URLs. Check if it respects `X-Forwarded-Proto` and
  add the proto middleware if needed.

---

## 2. Create the Directory Structure

```bash
# Copy from template
cp -r apps/_template apps/my-app

# Or create manually
mkdir -p apps/my-app/{config,secrets,volumes}
touch apps/my-app/{docker-compose.yml,.env.example}
echo "secrets/" >> apps/my-app/.gitignore
echo "volumes/" >> apps/my-app/.gitignore
```

---

## 3. Write `.env.example`

Follow [Env Structure](env-structure.md) for section order:

- [ ] Header comment with app name and instructions
- [ ] `# --- Images ---` with pinned version (never `:latest`)
- [ ] `# --- Container ---` with `CONTAINER_NAME_*` variables
- [ ] `# --- General ---` with `TIMEZONE` and `COMPOSE_PROJECT_NAME`
- [ ] `# --- Database ---` if applicable
- [ ] `# --- App Configuration ---` for app-specific values
- [ ] `# --- Traefik Routing ---` with all standard Traefik vars
- [ ] `# --- Secrets ---` with generation commands

**Secret generation — always strip newlines:**

```bash
openssl rand -base64 32 | tr -d '\n' > secrets/db_pwd.txt
```

Never `openssl rand ... > file` without `| tr -d '\n'` — trailing newlines cause
auth mismatches between services that handle them differently.

---

## 4. Write `docker-compose.yml`

Follow [Compose Structure](compose-structure.md) for block order per service:

- [ ] **Identity** — image via `${VAR}`, container_name via `${VAR}`, `restart: unless-stopped`
- [ ] **Security** — `no-new-privileges:true` (mandatory), `read_only` if supported
- [ ] **Configuration** — env vars (map format), secrets
- [ ] **Storage** — bind mounts (`./volumes/`), config mounts with `:ro`
- [ ] **Networking** — `proxy-public` for web, `app-internal` for databases
- [ ] **Traefik** — labels with `@file` suffixes for file-provider resources
- [ ] **Health** — healthcheck with appropriate tools and timing

### Common Pitfalls

| Pitfall | How to Avoid |
|---------|-------------|
| `user:` with s6-overlay image | Use `USERMAP_UID`/`USERMAP_GID` env vars instead |
| `_FILE` env vars ignored | Check if image supports them; if not, use entrypoint wrapper |
| `tls.options` without `@file` | Always append `@file` for file-provider resources |
| Healthcheck with missing tools | Verify `curl`/`wget` exists in the image first |
| `frameDeny` blocking iframes | Use custom Docker middleware with `frame-ancestors` CSP |
| HTTP URLs behind TLS proxy | Add `X-Forwarded-Proto=https` middleware |
| Image tag doesn't exist | Verify on Docker Hub before adding |
| Secret with trailing newline | Always `| tr -d '\n'` in generation command |

---

## 5. Write Custom Entrypoint (if needed)

Only when the image doesn't support `_FILE` env vars:

```sh
#!/bin/sh
set -e

# --- Secrets to env vars ---
[ -f /run/secrets/DB_PWD ] && \
  export DATABASE_PASSWORD="$(cat /run/secrets/DB_PWD)"

# --- (Optional) One-time config injection ---
# See Seafile's seahub_custom.py pattern for marker-based append

exec "$@"
```

Mount and wire up:

```yaml
entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
command: ["original-command", "--with-args"]  # from docker inspect
volumes:
  - ./config/entrypoint.sh:/config/entrypoint.sh:ro
```

---

## 6. Test on a Live Server

- [ ] `docker compose config` — syntax check (catches missing vars)
- [ ] `docker compose up -d` — all containers start without errors
- [ ] `docker compose ps` — all services healthy (no restart loops)
- [ ] Check logs for warnings (`trailing newline`, `_FILE not supported`, etc.)
- [ ] Access via browser — page loads over HTTPS
- [ ] Test the full workflow, not just the landing page
- [ ] Check Traefik dashboard — router and middleware status green

---

## 7. Document

- [ ] Update app's `README.md` if there are special setup steps
- [ ] Add any bugs found to `docs/bugfixes/` with root cause and fix
- [ ] Update this checklist if you discovered a new pitfall

---

## Quick Reference: Init System Detection

| Init System | How to Detect | `user:` allowed? | UID/GID mechanism |
|---|---|---|---|
| s6-overlay | `/package/admin/s6-overlay` in logs, `s6-rc` messages | **No** | `USERMAP_UID` / `USERMAP_GID` |
| supervisord | `supervisord` process, `/etc/supervisord.conf` | **No** | Usually none (runs as root) |
| tini / dumb-init | Simple PID 1 wrapper, no privilege management | **Yes** | Docker `user:` directive |
| None (direct exec) | App is PID 1 directly | **Yes** | Docker `user:` directive |

## Quick Reference: Secret Support

| Image | `_FILE` supported? | Pattern |
|---|---|---|
| PostgreSQL | Yes | `POSTGRES_PASSWORD_FILE` |
| MariaDB / MySQL | Yes | `MYSQL_ROOT_PASSWORD_FILE` |
| Paperless-ngx | Yes | `PAPERLESS_DBPASS_FILE`, `PAPERLESS_SECRET_KEY_FILE` |
| Redis | No | `command: redis-server --requirepass "$(cat /run/secrets/...)"` |
| OnlyOffice | No | Entrypoint wrapper |
| Seafile (all) | No | Entrypoint wrapper |
| Vaultwarden | No | Entrypoint wrapper |
| Ghost | No (partial) | Entrypoint wrapper |
