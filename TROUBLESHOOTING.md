# Troubleshooting & Lessons Learned

**Check this file first.** Every entry here burned real time during live deployment. These are the most common failure patterns across this blueprint — recurring, non-obvious, and often not covered by upstream docs.

---

## 1. Docker Image Issues

### 1.1 `pull access denied` / `repository does not exist`

**Symptom:** `pull access denied for <image>` or image pulls but container won't start.

**Causes & fixes:**

| Cause | Fix |
|---|---|
| Docker Hub org renamed upstream | Check current org on Docker Hub — e.g. `opensignlabs/` → `opensign/` |
| Image name changed between versions | Check upstream GitHub repo's current `docker-compose.yml` |
| Typo in image name in compose | `docker inspect <name>` → check `"Image"` field |

**OpenSign-specific:** The Docker Hub org is `opensign/opensign` and `opensign/opensignserver` — NOT `opensignlabs/`.

---

### 1.2 Tag not found / no semver tags

**Symptom:** `manifest unknown` or `tag does not exist` when pulling a specific version.

**Causes & fixes:**

| Cause | Fix |
|---|---|
| App only publishes floating tags | Use `main`, `latest`, or `stable` — check Docker Hub tags page |
| Semver tag tried but doesn't exist | OpenSign only has `main` / `staging` / `docker_beta` — no `vX.Y.Z` |

**Check:** `https://hub.docker.com/r/<org>/<image>/tags` before pinning a version.

---

## 2. Environment Variable Issues

### 2.1 Wrong variable names

**Symptom:** App starts but features are broken (mail doesn't work, DB can't connect, wrong URL embedded in links).

**Root cause:** Upstream docs are often outdated. The actual env var names come from the image source, not the README. Always verify against the **current** upstream `docker-compose.yml` on GitHub.

**Known wrong names we've encountered:**

| App | Wrong name (docs) | Correct name (actual) |
|---|---|---|
| OpenSign | `DATABASE_URI` | `MONGODB_URI` |
| OpenSign | `SMTP_USER` | `SMTP_USER_EMAIL` |
| OpenSign | `REACT_APP_SERVER_URL` | `REACT_APP_SERVERURL` |
| OpenSign | `REACT_APP_APP_ID` | `REACT_APP_APPID` |
| OpenSign | `APP_ID=<random>` | `APP_ID=opensign` (fixed/deprecated) |

**Debug approach:** When something silently fails, `docker compose exec <service> printenv | sort` and compare against what you set.

---

### 2.2 Internal vs. public URL

**Symptom:** Mixed Content errors in browser (`http://container-name:port/...` in responses), broken email links, broken file previews.

**Root cause:** Some apps embed the configured URL into stored data or outgoing emails. If you set the internal container URL (`http://api:8080`) instead of the public URL (`https://domain.example.com`), it gets baked into the database and sent to browsers.

**Affected apps:** OpenSign (`SERVER_URL`), Zammad (`ZAMMAD_FQDN`), Healthchecks (`SITE_ROOT`).

**Fix:** Always set these to the **public HTTPS URL** the browser uses, not the internal container address.

**If already wrong and data was written:** You need a DB migration. Example for OpenSign (Parse Server stores full file URLs):
```bash
docker compose exec db mongosh \
  --username opensign --password "$(cat .secrets/db_root_pwd.txt)" \
  --authenticationDatabase admin OpenSignDB --eval '
  db.contracts_Document.updateMany(
    { "URL": { $regex: "http://api:8080" } },
    [{ $set: { "URL": { $replaceAll: {
      input: "$URL", find: "http://api:8080/app",
      replacement: "https://<YOUR_DOMAIN>/app"
    }}}}]
  )'
```

---

### 2.3 DSN-unsafe passwords (special characters in connection strings)

**Symptom:** DB connection fails with parse error or `invalid URI` even though the password is correct.

**Root cause:** Characters like `@`, `:`, `/`, `?`, `#` break URI/DSN parsing when embedded directly in connection strings like `mongodb://user:password@host/db`.

**Affected apps:** Any app that takes a full DSN string (OpenSign `MONGODB_URI`, etc.).

**Fix:** Generate alphanumeric-only passwords for DSN use:
```bash
openssl rand -hex 32   # safe: hex chars only
```
Avoid `openssl rand -base64` for DSN passwords — base64 output contains `+`, `/`, `=`.

---

## 3. Volume & Permissions Issues

### 3.1 Container can't write to volume directory

**Symptom:** `unable to open database file`, `permission denied`, or migration fails on first start.

**Root cause:** Docker creates bind-mount directories as `root:root`. If the app runs as a non-root UID inside the container, it can't write.

**Known UIDs:**

| App | Container UID |
|---|---|
| Healthchecks | 999 (`hc`) |
| Uptime Kuma | 1000 |
| Most LSIO images | 1000 (`abc`) |

**Fix:**
```bash
sudo chown -R <uid>:<gid> volumes/<dirname>
# Example for Healthchecks:
sudo chown -R 999:999 volumes/data
```

**When to apply:** Always run this before the first `docker compose up -d` if you pre-create volume directories. Or: let Docker create the dir, then fix ownership, then restart.

**Note:** `chown` without `sudo` fails with `Operation not permitted` if run as a non-root user — always use `sudo` for host directory ownership changes.

---

## 4. Networking Issues

### 4.1 `internal: true` blocks outbound connections

**Symptom:** App can reach the database but can't send email, call webhooks, or reach external APIs. No obvious error — just silent failures or timeouts.

**Root cause:** `internal: true` on a Docker network means **no outbound internet**. Only use this for networks that should be completely isolated (e.g. DB-only networks).

**Affected:** Zammad `app-internal` — railsserver and scheduler need outbound for SMTP and webhooks. Remove `internal: true`.

**Rule of thumb:**
- DB-only network (no container needs outbound) → `internal: true` OK
- App network (app containers need email/webhooks) → no `internal: true`

---

### 4.2 Traefik returns 404 for a service

**Symptom:** `curl -I https://<domain>/` returns `HTTP/2 404` with Traefik headers. App is running and healthy.

**Causes in order of likelihood:**

1. **Typo in `APP_TRAEFIK_HOST`** — the most common cause. The label on the container has the wrong hostname.
   ```bash
   docker inspect <container> | grep "rule"
   # Check: does the Host() value exactly match the DNS name you're hitting?
   ```

2. **Container not on the correct Docker network** — Traefik can only route to containers on a shared network.
   ```bash
   docker inspect <container> --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
   # Must include proxy-public (or whatever TRAEFIK_NETWORK is set to)
   ```

3. **Labels not applied** — happens when `docker compose up -d` used an old compose file or the container wasn't recreated after a label change.
   ```bash
   docker inspect <container> | grep -A30 '"Labels"'
   # Check traefik.http.routers.* labels are present
   ```

4. **Router name collision** — two services with same `COMPOSE_PROJECT_NAME` → same router name → one wins, one loses.

**Fix for typo:** Correct `.env`, then `docker compose up -d --force-recreate <service>`.

---

### 4.3 Browser shows `ERR_NAME_NOT_RESOLVED` but `dig` resolves correctly

**Symptom:** Browser can't reach the domain, but `dig <domain> +short` returns an IP.

**Cause:** Browser DNS cache holds the old NXDOMAIN from before the DNS record was created.

**Fix:** Hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`) or open in a private/incognito window.

---

## 5. Git & Deployment Issues

### 5.1 Server running old code after local commits

**Symptom:** Config fix committed locally, `docker compose up -d` on server, still broken. `printenv` shows old value. `git log` on server shows old commit hash.

**Root cause:** Commits exist locally but were never pushed. Server's `git pull` has nothing to fetch.

**Fix:**
```bash
# On local machine:
git push origin dev

# On server:
git pull
docker compose up -d --force-recreate <service>
```

**Important:** `docker compose restart` does NOT pick up new env vars or label changes from an updated compose file. You need `up -d` (or `up -d --force-recreate`) to recreate the container with the new config.

---

### 5.2 `force-recreate` doesn't pick up env changes

**Symptom:** `docker compose up -d --force-recreate` runs, but `docker compose exec <service> printenv VAR` still shows old value.

**Cause:** The server hasn't pulled the latest commit yet. `force-recreate` re-reads the compose file and `.env` on disk — if they haven't changed on disk, nothing changes.

**Debug:**
```bash
git log --oneline -3          # what commit is the server on?
grep "VAR_NAME" .env          # what does the file actually say?
docker compose exec svc printenv VAR_NAME   # what did the container get?
```

---

## 6. Healthcheck Issues

### 6.0 Before writing any healthcheck — check the image type first

**Rule:** Before writing a healthcheck with `wget`/`curl`/`sh`, always verify the image has those tools:
```bash
docker compose exec <service> sh -c "which curl || which wget || echo none"
# If sh itself fails → scratch image → use healthcheck: disable: true immediately
```

**Known scratch/minimal Go images in this blueprint** (no shell, no tools):
| Image | Healthcheck |
|---|---|
| `henrygd/beszel` (hub) | `disable: true` |
| `twinproduction/gatus` | `disable: true` |

If `sh` fails → don't spend time looking for alternatives → `disable: true`.

---

### 6.1 Container perpetually `(unhealthy)` — image has no shell or tools

**Symptom:** Container shows `(unhealthy)` but the app works fine. `docker compose exec <service> sh` fails with `executable file not found`.

**Root cause:** Scratch-based or distroless images contain only the app binary — no `sh`, `wget`, `curl`, or any Unix tools.

**Affected:** Beszel hub (`henrygd/beszel`) — scratch image.

**Fix:** Disable the healthcheck:
```yaml
healthcheck:
  disable: true
```

**Check before writing a healthcheck:**
```bash
docker compose exec <service> sh -c "which curl || which wget || echo none"
```
If `sh` itself fails → scratch image → `disable: true`.

---

### 6.2 Healthcheck command exists but endpoint doesn't

**Symptom:** Container `(unhealthy)` even though the app runs fine and the tool (`wget`, `curl`) is present.

**Causes:**
- Health endpoint path is wrong (e.g. `/api/health` doesn't exist, actual path is `/api/v3/status/`)
- App hasn't finished starting when healthcheck fires (increase `start_period`)
- Upstream provides no health endpoint at all

**Debug:**
```bash
docker compose exec <service> wget -qO- http://127.0.0.1:<port>/api/health
# 200 = endpoint exists, 404 = wrong path, connection refused = wrong port
```

---

## 7. App-Specific First-Run Issues

### 7.1 First-user-wins — open the UI immediately after start

**Affected apps:** Beszel, Uptime Kuma, OpenSign, Zammad, Healthchecks, Portainer.

**Symptom:** After deployment, someone else (or a bot) registers first and you're locked out of admin.

**Rule:** As soon as `docker compose up -d` completes and the app is reachable, **immediately open the UI and create the admin/owner account**.

---

### 7.2 Zammad setup wizard — email step crashes with `exitstatus 1`

**Symptom:** Setup wizard → Email step → selecting "Local MTA" → `Delivery failed with exitstatus 1`.

**Cause:** No `sendmail` / `postfix` binary in the container.

**Fix:** Select **"SMTP — configure your own outgoing SMTP settings"** instead, or click **Skip** and configure later under Admin → Channels → Email.

---

### 7.3 Browser console WebSocket errors during setup that aren't from the app

**Symptom:** Console shows errors like `wss://sync.heylogin.app` or other third-party WebSocket URLs failing during Zammad setup wizard.

**Cause:** Browser extensions (e.g. HeyLogin password manager) injecting their own WebSocket connections. Not from the app.

**Fix:** Ignore. Disable the extension temporarily if you want a clean console.

---

## 8. Reverse Proxy / Traefik Routing Patterns

### 8.1 Path-based routing without prefix stripping

**Context:** Some apps use path-based routing (e.g. OpenSign routes `/app` to the API).

**Upstream trap:** OpenSign's upstream uses Caddy which **strips** the `/api` prefix before forwarding to Parse Server. Our Traefik setup routes `/app` **directly** — no stripping. Setting `SERVER_URL` with an `/api` prefix (as upstream docs suggest for Caddy) will break Traefik routing.

**Rule:** When adapting an upstream Caddy/nginx config to Traefik, check carefully whether the upstream proxy strips a path prefix. If yes, your Traefik router should match the **final** path (after stripping), not the original path.

---

### 8.2 Rails / Django apps behind Traefik need trusted proxy headers

**Symptom:** Incorrect redirect URLs, HTTP links in emails instead of HTTPS, wrong `REMOTE_ADDR` in logs.

**Fix:** Tell the app to trust `X-Forwarded-*` headers from Traefik:
- Rails (Zammad): `RAILS_TRUSTED_PROXIES: "0.0.0.0/0"`
- Django: `USE_X_FORWARDED_HOST = True` + `SECURE_PROXY_SSL_HEADER`

---

## Quick Diagnostic Checklist

When something doesn't work after deployment, run through this in order:

```
1. Is the container running?
   docker compose ps

2. Is it on the right network?
   docker inspect <name> --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'

3. Does Traefik see it with the right rule?
   docker inspect <name> | grep "rule"

4. Does the app respond internally?
   docker compose logs <service> --tail=30
   docker compose exec <service> wget -qO- http://127.0.0.1:<port>/

5. Is the server on the latest commit?
   git log --oneline -3
   # If behind: git push origin dev (local), git pull (server)

6. Are the env vars actually set correctly?
   docker compose exec <service> printenv | sort

7. Are volume permissions correct?
   ls -la volumes/
   # Fix: sudo chown -R <uid>:<gid> volumes/<dir>
```
