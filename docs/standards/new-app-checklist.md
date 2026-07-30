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

Copy the reference app — it is the canonical structure, and it runs:

```bash
cp -r apps/_reference apps/my-app
cd apps/my-app
```

Then replace the stand-in images (`nginx` for the app, `postgres` for the database)
and delete what your app does not need. The reference deliberately shows both secret
patterns at once — native `_FILE` support on the database, an entrypoint wrapper on
the app — so keep whichever matches your image and drop the other.

Check your work at any point with:

```bash
python3 scripts/ci/check-structure.py
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
| Secret with trailing newline | Always `\| tr -d '\n'` in generation command |

---

## 5. Write Custom Entrypoint (if needed)

Only when the image doesn't support `_FILE` env vars:

```sh
#!/bin/sh
set -e

# --- Secrets to env vars ---
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use intermediate
# variables so set -e correctly aborts if the secret file is missing.
_pwd="$(cat /run/secrets/db_pwd)"   # set -e fires here if cat fails
export DATABASE_PASSWORD="$_pwd"
unset _pwd

# Wrong pattern — set -e does NOT catch a failing cat:
# export DATABASE_PASSWORD="$(cat /run/secrets/db_pwd)"  ← silent failure!

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

## 7. Fill in `UPSTREAM.md`

It already came with the reference app — replace every `__REPLACE_ME__`. It tracks
where the setup comes from and how to upgrade:

- [ ] **Source** — Upstream repo URL, branch, version the setup is based on
- [ ] **What we use** — Which files are 1:1 copies vs adapted
- [ ] **What we changed** — Every deviation from upstream with reason
- [ ] **Upgrade checklist** — Steps to follow when bumping the version
- [ ] **Diff commands** — How to compare our config against upstream

The `Last verified: YYYY-MM-DD (vX.Y.Z)` line is what `scripts/ci/lifecycle-report.py`
reads and what the ✅ in the README rests on — set it only once the app was actually
verified on a clean install. A filled-in example: `apps/dashy/UPSTREAM.md`.

Two fields are read by a second checker and cannot be left blank:

- [ ] **`- **License:**`** — from the project's own `LICENSE` file, in its
      spelling. If it is genuinely split, say both halves.
- [ ] **`- **Origin:**`** — `Country · Entity · EU|non-EU`, from the project's
      imprint or legal page. If it states no country, write that — an honest
      blank beats a plausible guess.

`scripts/ci/sovereignty-report.py --check` fails on a missing field or an
unrecognised licence spelling, so a new licence forces a decision about which
class it belongs to. See [Provenance](../sovereignty/provenance.md).

---

## 8. Write the `## Backup` section

The app README carries a `## Backup` section — the template came with the
reference app. Fill in which database, which volumes hold state, which are
reproducible, and whether the app needs quiescing before a dump.

- [ ] Database engine, container name, database name, user
- [ ] Path to the password file under `.secrets/`
- [ ] Which volumes are state, which are cache
- [ ] A copy-pasteable borgmatic block
- [ ] Restore order, if it is anything other than "database, then app"

This is not paperwork: it is what makes `/etc/borgmatic/config.yaml` assemblable
from the apps instead of reverse-engineered from compose files during an
incident. Keep the heading exactly `## Backup` — `lifecycle-report.py` reads it.

## 9. Document

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
| Vikunja | No | Entrypoint wrapper — image is `FROM scratch`, add busybox utilities via multi-stage build |
