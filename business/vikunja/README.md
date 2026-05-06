# Vikunja

**Status: 🚧 Draft — not yet live-tested**

Open-source task management with kanban boards, to-do lists, Gantt views, and table view. Trello / Microsoft Planner alternative. Single binary image (API + frontend combined).

## Services

| Service | Image | Purpose |
|---|---|---|
| `vikunja` | `vikunja/vikunja` | API + frontend (single binary, port 3456) |
| `db` | `postgres:17-alpine` | Persistent storage |

## Setup

```bash
# 1. Copy env file and configure it
cp .env.example .env
# → set HOST_DOMAIN and TZ
# → VIKUNJA_AUTH_OPENID_ENABLED=false for first run (no Authentik needed yet)

# 2. Create secrets (no trailing newlines)
mkdir -p .secrets
echo -n "$(openssl rand -base64 48 | tr -d '\n')" > .secrets/VIKUNJA_JWT_SECRET
echo -n "$(openssl rand -base64 32 | tr -d '\n')" > .secrets/VIKUNJA_DB_PWD
# OIDC secret file must exist even when OIDC is disabled — use placeholder for now:
echo -n "placeholder" > .secrets/VIKUNJA_OIDC_SECRET

# 3. Build the custom image (adds /bin/sh to the upstream scratch image
#    so that the secrets-injection entrypoint can run)
docker compose build

# 4. Start
docker compose up -d

# 5. Open https://<HOST_DOMAIN>
#    First user to register becomes admin.
#    Once Authentik is configured: set VIKUNJA_AUTH_OPENID_ENABLED=true in .env,
#    replace .secrets/VIKUNJA_OIDC_SECRET with the real client secret,
#    then docker compose up -d (recreates the container).
```

## Authentik OIDC setup

Official guide: https://docs.goauthentik.io/integrations/services/vikunja/

### In Authentik

Use **Applications → Create with Provider** to create the application/provider pair in one step:

1. **Provider type**: `OAuth2/OpenID Connect`
2. **Redirect URI** (type: **Strict**): `https://<HOST_DOMAIN>/auth/openid/authentik`
   - The path segment `authentik` must match the provider key used in Vikunja env vars
   - Optional (desktop client): add a `Regex` URI `^http://127\.0\.0\.1:[0-9]+/auth/openid/authentik$`
3. **Signing key**: select any available key
4. Note the **Client ID**, **Client Secret**, and **application slug**

### In `.env`

```
AUTHENTIK_DOMAIN=auth.example.com
AUTHENTIK_APP_SLUG=vikunja          # application slug from Authentik (used in authurl)
OIDC_CLIENT_ID=<client-id-from-authentik>
```

### In `.secrets/VIKUNJA_OIDC_SECRET`

```bash
echo -n "<client-secret-from-authentik>" > .secrets/VIKUNJA_OIDC_SECRET
```

### Auto-redirect to Authentik

To skip the Vikunja login page and go directly to Authentik:

```
https://<HOST_DOMAIN>/login?redirectToProvider=authentik
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
3. In `.env`, change the scope line:
   ```
   # In docker-compose.yml:
   VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_SCOPE: "openid profile email vikunja_scope"
   ```

## Open items (before ✅ Ready)

- [ ] Live test: `docker compose build && docker compose up -d`
- [ ] Verify `vikunja healthcheck` subcommand works (scratch image, no shell available natively)
- [ ] Verify entrypoint.sh runs correctly with busybox `/bin/sh`
- [ ] Authentik: create OIDC provider, test login flow end-to-end
- [ ] Disable registration after admin account created: `VIKUNJA_SERVICE_ENABLEREGISTRATION=false`
- [ ] Test `read_only: true` — enable if Vikunja writes only to `/app/vikunja/files` and `/tmp`
- [ ] SMTP configuration for password reset emails (not needed if OIDC-only)
- [ ] Verify `no-new-privileges` does not break startup

## Verify

- [ ] Both containers healthy: `docker compose ps`
- [ ] Web UI loads at configured domain
- [ ] Authentik login button appears on Vikunja login page
- [ ] Log in via Authentik — user account created automatically
- [ ] Create a project and a task — verify they persist after `docker compose restart`
- [ ] Kanban view works

## Security Model

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | Both services |
| Secrets | ✅ | JWT secret, DB password, OIDC client secret via Docker Secrets |
| Database isolation | ✅ | `db` on internal network only |
| Docker socket | ✅ | Not mounted |
| SSO | ✅ | Authentik OIDC configured |
| `read_only` filesystem | ⬜ | Not set — verify in live test before enabling |

## Notes

- **PostgreSQL vs SQLite**: PostgreSQL is required for multi-user setups (upstream recommendation). SQLite is only suitable for personal single-user use.
- **Secrets**: Vikunja has no `_FILE` env var support — all secrets are injected via `config/entrypoint.sh`
- **Files volume**: uploaded files are in the `vikunja_files` named Docker volume. Back this up.
- **Postgres version**: upstream docs show `postgres:18`. We pin to `17-alpine` to match the blueprint standard. Vikunja has no hard dependency on a specific PG version.
- **First user**: first user to complete registration becomes admin. After testing, consider disabling registration: set `VIKUNJA_SERVICE_ENABLEREGISTRATION=false`
