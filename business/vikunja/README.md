# Vikunja

**Status: ✅ Live-tested — Authentik OIDC working**

Open-source task management with kanban boards, to-do lists, Gantt views, and table view. Trello / Microsoft Planner alternative. Single binary image (API + frontend combined).

## Services

| Service | Image | Purpose |
|---|---|---|
| `vikunja` | `vikunja/vikunja` (custom build) | API + frontend (single binary, port 3456) |
| `db` | `postgres:17-alpine` | Persistent storage |

The upstream image is `FROM scratch` — no shell or utilities. A custom build layer (busybox) adds `/bin/sh`, `/bin/cat`, and `/bin/wget` for secrets injection and the HTTP healthcheck.

## Setup

```bash
# 1. Copy env file and configure it
cp .env.example .env
# → set APP_TRAEFIK_HOST, TZ, AUTHENTIK_DOMAIN, AUTHENTIK_APP_SLUG, OIDC_CLIENT_ID
# → set VIKUNJA_AUTH_OPENID_ENABLED=true once Authentik provider is created

# 2. Create secrets (no trailing newlines)
mkdir -p .secrets
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
# Placeholders — Docker mounts these even when the feature is disabled.
# Replace with real values when enabling OIDC / SMTP.
echo -n "placeholder" > .secrets/oidc_secret.txt
echo -n "placeholder" > .secrets/smtp_pwd.txt

# 3. Write the real Authentik Client Secret
echo -n "<client-secret-from-authentik>" > .secrets/oidc_secret.txt

# 4. Build the custom image (adds busybox utilities to the upstream scratch image)
docker compose build

# 5. Start
docker compose up -d

# 6. Open https://<APP_TRAEFIK_HOST>
#    Login via Authentik — first user to log in via OIDC becomes admin.
```

> **First-run note**: The default `.env.example` ships with registration disabled and local login disabled — OIDC is the only login method. Set up the Authentik provider (see below) before deploying, or temporarily set `VIKUNJA_ENABLEREGISTRATION=true` and `VIKUNJA_LOCAL_AUTH_ENABLED=true` in `.env` to bootstrap with a local account first.

## Authentik OIDC setup

Official guide: https://docs.goauthentik.io/integrations/services/vikunja/

### In Authentik

Use **Applications → Create with Provider** to create the application/provider pair in one step:

1. **Provider type**: `OAuth2/OpenID Connect`
2. **Redirect URI** (type: **Strict**): `https://<APP_TRAEFIK_HOST>/auth/openid/authentik`
   - The path segment `authentik` must match the provider key used in Vikunja env vars
   - Optional (desktop client): add a `Regex` URI `^http://127\.0\.0\.1:[0-9]+/auth/openid/authentik$`
3. **Signing key**: select any available key
4. Note the **Client ID**, **Client Secret**, and **application slug**
5. **Policy / Group / User Bindings**: add at least one group or user binding — without it Authentik returns 403 on the OIDC discovery endpoint

### In `.env`

```
AUTHENTIK_DOMAIN=auth.example.com
AUTHENTIK_APP_SLUG=vikunja          # application slug from Authentik (used in authurl)
OIDC_CLIENT_ID=<client-id-from-authentik>
VIKUNJA_AUTH_OPENID_ENABLED=true
```

### In `.secrets/oidc_secret.txt`

```bash
echo -n "<client-secret-from-authentik>" > .secrets/oidc_secret.txt
docker compose up -d --force-recreate vikunja
```

### Auto-redirect to Authentik

The Traefik `redirectregex` middleware is already configured in `docker-compose.yml` — visiting `/login` automatically redirects to Authentik. No click needed.

To go directly to Authentik from a link:
```
https://<APP_TRAEFIK_HOST>/login?redirectToProvider=authentik
```

> **Emergency local access**: if you need to bypass Authentik (e.g., Authentik is down), temporarily set `VIKUNJA_AUTH_LOCAL_ENABLED=true` and `VIKUNJA_ENABLEREGISTRATION=true` in `.env` and recreate the container.

### Authentik group → Vikunja team sync (optional)

1. In Authentik: create a scope mapping `vikunja_scope` with expression:
   ```python
   groupsDict = {"vikunja_groups": []}
   for group in request.user.ak_groups.all():
       groupsDict["vikunja_groups"].append({"name": group.name, "oidcID": group.num_pk})
   return groupsDict
   ```
2. Add `vikunja_scope` to the Authentik provider → Advanced protocol settings → Scopes
3. In `.env`, set:
   ```
   VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_SCOPE=openid profile email vikunja_scope
   ```
   (override the default in `docker-compose.yml` via the env var)

## SMTP setup

```bash
# Write the SMTP key/password (Brevo: SMTP & API → SMTP Keys, not your login password)
echo -n "<smtp-key>" > .secrets/smtp_pwd.txt

# In .env:
VIKUNJA_MAILER_ENABLED=true
VIKUNJA_MAILER_HOST=smtp-relay.brevo.com
VIKUNJA_MAILER_PORT=587
VIKUNJA_MAILER_USERNAME=your@email.com
VIKUNJA_MAILER_FROMEMAIL=vikunja@your-domain.com
VIKUNJA_MAILER_AUTHTYPE=login

docker compose up -d --force-recreate vikunja
```

## Open items

- [x] Authentik: create OIDC provider, test login flow end-to-end
- [x] Disable registration (default: false)
- [x] Disable local login — SSO-only (default: false)
- [ ] SMTP: configure outgoing email (see SMTP setup above)
- [ ] Test `read_only: true` — enable if Vikunja writes only to `/app/vikunja/files` and `/tmp`
- [ ] Logo: set `VIKUNJA_CUSTOMLOGOURL` in `.env` if custom branding needed

## Verify

- [x] Both containers healthy: `docker compose ps`
- [x] Web UI loads at configured domain
- [x] Authentik login button appears on login page (auto-redirect active)
- [x] Log in via Authentik — user account created automatically
- [x] Create a project and a task — verify they persist after `docker compose restart`
- [x] Kanban view works
- [ ] SMTP: password reset / reminder email received

## Security Model

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | Both services |
| Secrets | ✅ | JWT key, DB password, OIDC secret, SMTP password via Docker Secrets |
| Database isolation | ✅ | `db` on internal network only |
| Docker socket | ✅ | Not mounted |
| SSO | ✅ | Authentik OIDC — live-tested |
| Local login | ✅ | Disabled by default — SSO-only |
| Registration | ✅ | Disabled by default |
| Auto-redirect | ✅ | Traefik redirects `/login` → Authentik |
| Rate limiting | ✅ | Enabled, real client IP via XFF |
| `read_only` filesystem | ⬜ | Not set — verify in live test before enabling |

## Notes

- **PostgreSQL vs SQLite**: PostgreSQL is required for multi-user setups (upstream recommendation). SQLite is only suitable for personal single-user use.
- **Secrets**: Vikunja has no `_FILE` env var support — all secrets are injected via `config/entrypoint.sh`.
- **Healthcheck**: The built-in `vikunja healthcheck` subcommand spawns a new process without the entrypoint's environment — it fails DB auth every time. The HTTP check via wget hits the already-running server instead. See `docs/bugfixes/vikunja-openproject-2026-05-06.md`.
- **Files volume**: uploaded files are in the `vikunja_files` named Docker volume. Back this up.
- **First OIDC user**: first user to log in via Authentik becomes admin in Vikunja. Registration is disabled so no local accounts can be created afterward.
- **Postgres version**: upstream docs show `postgres:18`. Pinned to `17-alpine` to match the blueprint standard. No hard Vikunja dependency on PG version.
- **DNS on self-hosted servers**: The Vikunja container must be able to resolve the Authentik hostname. On a server with proper public DNS this works automatically. On test servers add the hostname to `/etc/hosts` on the Docker host. See `docs/bugfixes/vikunja-openproject-2026-05-06.md` Bug 5.
- **Authentik policy binding required**: The Vikunja application in Authentik must have at least one Group/User binding — without it Authentik returns 403 on the OIDC discovery endpoint and login fails completely.
