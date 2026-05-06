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
# → set APP_TRAEFIK_HOST and TZ
# → VIKUNJA_AUTH_OPENID_ENABLED=false for first run (no Authentik needed yet)
# → VIKUNJA_MAILER_ENABLED=false until SMTP is configured

# 2. Create secrets (no trailing newlines)
mkdir -p .secrets
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
# OIDC + SMTP secret files must exist even when disabled — Docker mounts them regardless:
echo -n "placeholder" > .secrets/oidc_secret.txt
echo -n "placeholder" > .secrets/smtp_pwd.txt
# Replace with real values when enabling OIDC / mailer.

# 3. Build the custom image (adds busybox utilities to the upstream scratch image)
docker compose build

# 4. Start
docker compose up -d

# 5. Open https://<APP_TRAEFIK_HOST>
#    First user to register becomes admin.
#    Once Authentik is configured: set VIKUNJA_AUTH_OPENID_ENABLED=true in .env,
#    replace .secrets/oidc_secret.txt with the real client secret,
#    then docker compose up -d (recreates the container).
```

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
```

### Auto-redirect to Authentik

To skip the Vikunja login page and go directly to Authentik:

```
https://<APP_TRAEFIK_HOST>/login?redirectToProvider=authentik
```

### Disable local login (SSO-only)

Once Authentik works, uncomment in `docker-compose.yml`:
```yaml
VIKUNJA_AUTH_LOCAL_ENABLED: "false"
```

### Authentik group → Vikunja team sync (optional)

1. In Authentik: create a scope mapping `vikunja_scope` with expression:
   ```python
   groupsDict = {"vikunja_groups": []}
   for group in request.user.ak_groups.all():
       groupsDict["vikunja_groups"].append({"name": group.name, "oidcID": group.num_pk})
   return groupsDict
   ```
2. Add `vikunja_scope` to the Authentik provider → Advanced protocol settings → Scopes
3. In `.env`, change the scope:
   ```
   # In docker-compose.yml:
   VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_SCOPE: "openid profile email vikunja_scope"
   ```

## Open items

- [x] Authentik: create OIDC provider, test login flow end-to-end
- [ ] Disable registration after confirming OIDC works: `VIKUNJA_SERVICE_ENABLEREGISTRATION=false`
- [ ] Disable local login for SSO-only: uncomment `VIKUNJA_AUTH_LOCAL_ENABLED: "false"` in docker-compose.yml
- [ ] Test `read_only: true` — enable if Vikunja writes only to `/app/vikunja/files` and `/tmp`
- [ ] SMTP: set `VIKUNJA_MAILER_ENABLED=true` in `.env`, fill host/user/from, write password to `.secrets/smtp_pwd.txt`

## Verify

- [x] Both containers healthy: `docker compose ps`
- [x] Web UI loads at configured domain
- [x] First user registration creates admin account
- [x] Authentik login button appears on Vikunja login page
- [x] Log in via Authentik — user account created automatically
- [x] Create a project and a task — verify they persist after `docker compose restart`
- [x] Kanban view works

## Security Model

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | Both services |
| Secrets | ✅ | JWT secret, DB password, OIDC client secret via Docker Secrets |
| Database isolation | ✅ | `db` on internal network only |
| Docker socket | ✅ | Not mounted |
| SSO | ✅ | Authentik OIDC — live-tested |
| `read_only` filesystem | ⬜ | Not set — verify in live test before enabling |

## Notes

- **PostgreSQL vs SQLite**: PostgreSQL is required for multi-user setups (upstream recommendation). SQLite is only suitable for personal single-user use.
- **Secrets**: Vikunja has no `_FILE` env var support — all secrets are injected via `config/entrypoint.sh`.
- **Healthcheck**: The built-in `vikunja healthcheck` subcommand spawns a new process without the entrypoint's environment — it fails DB auth every time. The HTTP check via wget hits the already-running server instead. See `docs/bugfixes/vikunja-openproject-2026-05-06.md`.
- **Files volume**: uploaded files are in the `vikunja_files` named Docker volume. Back this up.
- **First user**: first user to complete registration becomes admin. After testing, disable registration: `VIKUNJA_SERVICE_ENABLEREGISTRATION=false`.
- **Postgres version**: upstream docs show `postgres:18`. Pinned to `17-alpine` to match the blueprint standard. No hard Vikunja dependency on PG version.
