# Authentik

Self-hosted identity provider. Acts as a central SSO endpoint for other apps in the stack via **Forward-Auth** (Traefik middleware) or **OAuth2 / OIDC / SAML** (app-native clients).

## Architecture

Four services:

| Service | Image | Purpose |
|---------|-------|---------|
| `server` | `ghcr.io/goauthentik/server` (cmd `server`) | Web UI + REST API, the only container exposed through Traefik |
| `worker` | Same image (cmd `worker`) | Background jobs: email, LDAP/directory sync, policy evaluation |
| `db` | `postgres:16-alpine` | Primary data store (users, groups, tokens, events) |
| `redis` | `redis:7.4-alpine` | Session cache + Celery broker for the worker |

`server` and `worker` share the same image — only the command differs. Both need access to `db` and `redis`; only `server` needs access to the outside world (for initial setup flows and user logins).

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

# 3. Start
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

## Integrating other apps

### Forward-Auth (easiest — no changes in the target app)

Use Authentik's `Proxy Provider` + a Traefik middleware. Each protected app gets:

```yaml
labels:
  - "traefik.http.routers.<app>.middlewares=authentik-forward-auth@docker,..."
```

The middleware is defined once in Authentik's Outposts config and injected into Traefik via Docker labels or the file provider. See: https://docs.goauthentik.io/docs/providers/proxy/forward_auth/traefik

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
- **Worker volumes are shared with server.** Both mount `./volumes/media` and `./volumes/custom-templates`. Don't change the mount paths without updating both services.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, version-pinning guidance
