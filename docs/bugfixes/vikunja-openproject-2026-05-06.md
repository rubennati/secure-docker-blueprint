# Live-test findings: Vikunja + OpenProject CE — 2026-05-06

Initial live-test of both `business/vikunja` and `business/openproject` on a Debian host. All bugs were found and fixed during this session.

---

## OpenProject CE

### Bug 1 — Base64 password breaks `postgres://` URL

**Symptom**: seeder exited with code 2, no log output, runtime ~335 ms. No obvious error.

**Root cause**: The OpenProject entrypoint builds `DATABASE_URL` in the form `postgres://user:password@host/db`. Base64 passwords contain `+`, `/`, and `=` — all URL-special characters. The `+` is interpreted as a space, `/` splits the path segment, and `=` breaks query string parsing. The postgres driver silently received a malformed URL and returned a non-zero exit without a useful message.

**Fix**: URL-encode the password with `sed` before embedding it in the URL:
```sh
_enc="$(printf '%s' "${_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
export DATABASE_URL="postgres://...:${_enc}@..."
```

**File**: `business/openproject/config/entrypoint.sh`

---

### Bug 2 — DB takes ~3 min to initialize on first `docker compose up`

**Symptom**: `web` and `seeder` containers timed out waiting for `db` to become healthy on the very first run. Running `docker compose up -d` again (after DB was healthy) worked fine.

**Root cause**: PostgreSQL initializes its data directory (`initdb`) on first start, which takes longer than the default `start_period`. By the time the healthcheck retries were exhausted, the DB was still initializing.

**Fix / workaround**: `docker compose up -d` a second time. The DB is already running and healthy by then; `seeder` and `web` start immediately. No code change needed — documented in README.

---

## Vikunja

### Bug 1 — Healthcheck fails every time: `vikunja healthcheck` lacks env vars

**Symptom**: Container showed `(unhealthy)` despite the server running correctly (HTTP :3456 up, migrations passed). Health log showed:
```
Running migrations…
pq: password authentication failed for user "vikunja"
Migration failed: pq: password authentication failed for user "vikunja"
```

**Root cause**: The `vikunja healthcheck` subcommand is a fresh process spawned by Docker. It does not inherit environment variables set by the entrypoint — it starts with a clean environment. The entrypoint sets `VIKUNJA_DATABASE_PASSWORD` for the main server process, but the healthcheck subprocess has no password and fails DB auth every time.

**Fix**: Replace the healthcheck subcommand with an HTTP check using `wget` (added to the image via busybox):
```yaml
healthcheck:
  test: ["CMD", "/bin/wget", "-qO-", "http://localhost:3456/api/v1/info"]
```
**Files**: `business/vikunja/Dockerfile` (add `/bin/wget`), `business/vikunja/docker-compose.yml`

---

### Bug 2 — `export VAR=$(cmd)` silently swallows `cat` failures with `set -e`

**Symptom**: If a secret file is missing or unreadable, the container starts with an empty env var instead of aborting. The server then fails to connect to the DB (auth error) rather than failing at startup with a clear message.

**Root cause**: POSIX special-builtin rule: when `export` is used as `export VAR=$(cmd)`, the exit status of `cmd` is discarded — `export`'s own status (always 0) is what `set -e` sees. So a failing `cat` is silently ignored and `VAR` is set to empty.

**Fix**: Use intermediate variables. The assignment form `_var=$(cmd)` is a simple command — `set -e` *does* apply to the command substitution:
```sh
# Wrong — set -e does NOT catch cat failing here:
export VIKUNJA_DATABASE_PASSWORD="$(cat /run/secrets/db_pwd)"

# Correct — set -e catches cat failing here:
_pwd="$(cat /run/secrets/db_pwd)"
export VIKUNJA_DATABASE_PASSWORD="$_pwd"
unset _pwd
```

**Files**: `business/vikunja/config/entrypoint.sh`, `business/openproject/config/entrypoint.sh`

---

### Bug 3 — `cat: not found` in entrypoint (FROM scratch image)

**Symptom**: Secret injection failed with `cat: not found` — the entrypoint ran but `cat` was not available.

**Root cause**: `vikunja/vikunja` is built `FROM scratch`. Only `/bin/sh` had been copied from busybox; `/bin/cat` was missing.

**Fix**: Add `COPY --from=shell /bin/cat /bin/cat` to the Dockerfile.

**File**: `business/vikunja/Dockerfile`

---

### Bug 4 — `/app/vikunja/files` permission denied (uid=1000 vs root-owned dir)

**Symptom**: Vikunja failed to start with `permission denied` on the files volume.

**Root cause**: The `vikunja/vikunja` upstream image leaves `/app/vikunja/files` root-owned. When Docker initializes the named volume on first run, the directory inherits root ownership. Vikunja runs as uid=1000 and cannot write to it.

**Attempted wrong fix**: `USER root` / `USER 0` in Dockerfile → `unable to find user root: invalid argument`. FROM scratch images have no `/etc/passwd` — Docker cannot resolve any user identifier for `USER` or `RUN`.

**Correct fix**: `COPY --chown=1000:0 --from=shell /files-init /app/vikunja/files` — creates the directory with the correct ownership in the image layer without executing any runtime command.

**File**: `business/vikunja/Dockerfile`

---

### Note — OpenProject CE has no OIDC/SSO

The OpenProject OAuth2 provider setup documented in the Authentik integration docs is for the **Enterprise Edition** only. CE supports local accounts and basic LDAP. No workaround exists.
