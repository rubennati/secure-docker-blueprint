# Authentik

Self-hosted identity provider. Acts as a central SSO endpoint for other apps in the stack via **Forward-Auth** (Traefik middleware) or **OAuth2 / OIDC / SAML** (app-native clients).

## Architecture

Five services (four long-running plus a one-shot init):

| Service | Image | Purpose |
|---------|-------|---------|
| `init-perms` | `alpine:3.19` | One-shot: chowns bind-mount directories to UID 1000 so the non-root Authentik image can write there. Exits in <1s, runs on every `up -d`. |
| `server` | `ghcr.io/goauthentik/server` (cmd `server`) | Web UI + REST API, the only container exposed through Traefik |
| `worker` | Same image (cmd `worker`) | Background jobs: email, LDAP/directory sync, policy evaluation |
| `db` | `postgres:16-alpine` | Primary data store (users, groups, tokens, events) |
| `redis` | `redis:7.4-alpine` | Session cache + Celery broker for the worker |

`server` and `worker` share the same image — only the command differs. Both need access to `db` and `redis`; only `server` needs access to the outside world (for initial setup flows and user logins).

### Why the init container

Recent Authentik images run as UID 1000 (non-root) and deliberately refuse to fix volume permissions themselves — the relevant log line is `"Not running as root, disabling permission fixes"`. On a fresh install the bind-mounted `./volumes/data`, `./volumes/certs`, and `./volumes/custom-templates` are owned by `root:root` and the container crashes with `PermissionError: [Errno 13] Permission denied`.

`init-perms` runs as root inside a short-lived Alpine container, creates the three subdirectories, and chowns them to `1000:1000` before `server` and `worker` start (`depends_on: service_completed_successfully`). The long-running Authentik containers stay non-root — only the init container needs privilege, and only for the ~500ms it takes to exit.

Upstream reference: https://docs.goauthentik.io/troubleshooting/image_upload/

### Secret handling

Authentik reads values prefixed `file://` by opening the referenced file. This is used for every sensitive piece:

```yaml
AUTHENTIK_POSTGRESQL__PASSWORD: file:///run/secrets/DB_PWD
AUTHENTIK_SECRET_KEY:            file:///run/secrets/AUTHENTIK_SECRET_KEY
AUTHENTIK_EMAIL__PASSWORD:       file:///run/secrets/SMTP_PASSWORD
```

No entrypoint wrapper needed.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, SMTP_*, TZ

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 60 | tr -d '\n' > .secrets/authentik_secret_key.txt
printf '%s' 'YOUR-SMTP-PASSWORD' > .secrets/smtp_password.txt

# 3. Start — the init-perms service chowns the bind-mount directories
#    to UID 1000 before server and worker start. No host-side sudo needed.
docker compose up -d

# 4. Wait for the server healthcheck to pass
docker compose logs server --follow
# Look for: "Startup complete"

# 5. Complete the first-run admin setup in the browser
# https://<APP_TRAEFIK_HOST>/if/flow/initial-setup/
# This URL is ONLY available before an admin exists. Set up akadmin here.
```

Default access policy is `acc-public` + `sec-3` — publicly reachable (users must be able to log in from anywhere), strict headers, soft rate limit.

## Verify

```bash
docker compose ps                              # All four services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/-/health/live/   # 200 OK
curl -fsSI https://<APP_TRAEFIK_HOST>/-/health/ready/  # 200 OK
```

Log in as the admin you just created, open `Admin Interface → System → Configuration`, and confirm:

- Database connection: green
- Redis connection: green
- Email: test-send works (if SMTP is configured)

## Integrating other apps via Forward-Auth

Forward-Auth lets Traefik delegate authentication to Authentik without touching the target app.
Every request hits Authentik first — if the user is authenticated the request passes through,
otherwise they are redirected to the Authentik login page.

The Traefik middleware (`sec-authentik`) is already defined in
`core/traefik/ops/templates/dynamic/integrations.yml.tmpl` — commented out.

> **Multi-host note:** `forwardAuth` is not limited to the same Docker host.
> The `address` in `sec-authentik` can point to any reachable endpoint —
> another machine in the LAN, a remote server, or a public URL. Traefik only
> needs network access to that address. This means one central Authentik
> instance can protect apps running on multiple hosts.

---

### Step 0 — One-time setup (do this once, not per app)

#### 0a. Activate the Traefik middleware

In `core/traefik/ops/templates/dynamic/integrations.yml.tmpl`, uncomment the `http:` /
`middlewares:` block and the `sec-authentik` section. Then re-render and redeploy Traefik:

```bash
cd core/traefik
./ops/scripts/render.sh
docker compose up -d
```

The middleware is now available as `sec-authentik@file` for any router.

#### 0b. Verify the embedded outpost

Authentik ships with an embedded outpost — no extra container needed.

In the Authentik UI: **Admin Interface → Applications → Outposts**

Confirm the `authentik Embedded Outpost` exists and its health is green.
If it is missing: create it (Type: `Proxy`, leave all defaults, save).

---

### Pattern 1 — Full app protection

The entire app is behind Authentik. Any unauthenticated request redirects to the login page.

**Use for:** Dashy, Heimdall, and any internal tool where all routes require a login.

#### 1a. Create the Authentik Provider

**Admin Interface → Applications → Providers → Create**

| Field | Value |
|-------|-------|
| Name | `<app-name> Forward Auth` |
| Type | `Proxy Provider` |
| Authorization flow | `default-provider-authorization-implicit-consent` |
| Forward auth (single application) | ✅ selected |
| External host | `https://<APP_TRAEFIK_HOST>` |

Save. Note the provider name.

#### 1b. Create the Authentik Application

**Admin Interface → Applications → Applications → Create**

| Field | Value |
|-------|-------|
| Name | `<app-name>` |
| Slug | `<app-name>` (lowercase, hyphens) |
| Provider | select the provider you just created |

Save. Then: **Admin Interface → Applications → Outposts** → edit the Embedded Outpost →
add the new application to its list → Save.

#### 1c. Add the middleware to the app's Compose file

Add `sec-authentik@file` to the router's existing middleware list:

```yaml
labels:
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file,sec-authentik@file"
```

Redeploy the app:

```bash
docker compose up -d
```

#### 1d. Verify

Open the app URL in a private browser window. You should be redirected to the Authentik
login page. After login, you land back at the app.

---

### Pattern 2 — Path-scoped protection

Only specific paths (e.g. `/admin`, `/api`) require authentication. All other routes remain
open. Implemented via a second Traefik router with higher priority on the protected path.

**Use for:** Paperless-ngx `/admin`, any app with a public-facing frontend and a protected
admin backend on the same domain.

#### 2a. Create the Authentik Provider

**Admin Interface → Applications → Providers → Create**

| Field | Value |
|-------|-------|
| Name | `<app-name> Admin Forward Auth` |
| Type | `Proxy Provider` |
| Authorization flow | `default-provider-authorization-implicit-consent` |
| Forward auth (single application) | ✅ selected |
| External host | `https://<APP_TRAEFIK_HOST>/<protected-path>/` |

> **Important:** For Pattern 2, the External host must include the protected path
> (e.g. `https://paperless.example.com/admin/`), **not** just the domain root.
> Authentik uses the External host as the redirect target after a successful login.
> If you set it to the domain root, users land on the app's public frontend after
> login instead of the protected path.

#### 2b. Create the Authentik Application

Same as Pattern 1 — Step 1b. Add the application to the Embedded Outpost.

#### 2c. Add a second router to the app's Compose file

Add a dedicated router for the protected path alongside the existing one.
The higher `priority` ensures Traefik matches `/admin` before the catch-all router:

```yaml
labels:
  # --- Existing router (all traffic, no auth) ---
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.rule=Host(`${APP_TRAEFIK_HOST}`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.entrypoints=websecure"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file"
  - "traefik.http.services.${COMPOSE_PROJECT_NAME}.loadbalancer.server.port=${APP_INTERNAL_PORT}"

  # --- Second router: /admin only, with Forward-Auth ---
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/admin`)"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.entrypoints=websecure"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.tls=true"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.priority=100"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.middlewares=${APP_TRAEFIK_ACCESS}@file,${APP_TRAEFIK_SECURITY}@file,sec-authentik@file"
  - "traefik.http.routers.${COMPOSE_PROJECT_NAME}-admin.service=${COMPOSE_PROJECT_NAME}"
```

> **Note:** The `-admin` router reuses the same Traefik service (same `loadbalancer.server.port`)
> — no separate container is needed. Only the middleware chain differs.

Redeploy the app:

```bash
docker compose up -d
```

#### 2d. Verify

- Open `https://<host>/admin` in a private browser window → redirects to Authentik login ✅
- Open `https://<host>/` → loads without login prompt ✅

### OAuth2 / OIDC (apps with native support)

Create an `OAuth2/OpenID Provider` in Authentik, point the target app at:

```
https://<APP_TRAEFIK_HOST>/application/o/<application-slug>/
```

Exact URLs (authorize, token, userinfo) are shown in Authentik's UI for each provider.

### SAML

Similar pattern — create a `SAML Provider`, download the metadata XML from Authentik, feed it to the target app.

## Security Model

- Database, Redis, and the worker are only on `app-internal` (which is `internal: true`) — none of them can reach or be reached from the outside directly
- Only `server` is on `proxy-public`; Traefik terminates TLS and applies `sec-3` (strict headers + rate limit + permissions-policy)
- `AUTHENTIK_SECRET_KEY` signs every token Authentik issues — treat rotation with care (existing sessions invalidate)
- `AUTHENTIK_ERROR_REPORTING__ENABLED: "false"` — no telemetry to external endpoints
- Redis runs `read_only: true` with a `tmpfs` for `/tmp`; no writable root filesystem
- `no-new-privileges:true` on every service

## Known Issues

- **Setup URL is public until an admin exists.** `/if/flow/initial-setup/` lets anyone create `akadmin`. Complete it immediately after the first boot; if you forget, anyone hitting that URL first becomes the admin.
- **`AUTHENTIK_SECRET_KEY` rotation invalidates all existing sessions and API tokens.** Plan a maintenance window.
- **Email flows depend on SMTP.** Password reset, invitation, and event notifications silently fail if SMTP is misconfigured. Test with a real account after setup.
- **Worker volumes are shared with server.** Both mount `./volumes/data` and `./volumes/custom-templates`. Don't change the mount paths without updating both services.
- **Legacy `/media` mount.** Authentik has migrated from `/media` to `/data`. If you are upgrading a pre-2025 install: stop the stack, move `volumes/media` to `volumes/data`, run `up -d` — the init container will re-chown.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, version-pinning guidance
