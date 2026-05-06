# Vikunja

**Status: ✅ Ready** — v2.3.0 · 2026-05-06

Open-source task management with kanban boards, to-do lists, Gantt views, and table view. Trello / Microsoft Planner alternative. Single binary image (API + frontend combined).

## Services

| Service | Image | Purpose |
|---|---|---|
| `vikunja` | `vikunja/vikunja` (custom build) | App + frontend (single binary, port 3456) |
| `db` | `postgres:17-alpine` | Stores all tasks, projects, and user data |

The upstream image ships without a shell or any utilities (`FROM scratch`). A custom build layer adds the minimum needed: a shell and `cat` for reading secrets at startup, and `wget` for the health check.

## Setup

```bash
# 1. Copy and configure the env file
cp .env.example .env
# Required: set APP_TRAEFIK_HOST and TZ

# 2. Create the secrets folder and generate credentials
mkdir -p .secrets
openssl rand -base64 48 | tr -d '\n' > .secrets/jwt_key.txt   # signs user sessions
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt    # database password

# Placeholder files — must exist even when the feature is disabled
echo -n "placeholder" > .secrets/oidc_secret.txt   # replace when enabling Authentik
echo -n "placeholder" > .secrets/smtp_pwd.txt       # replace when enabling email

# 3. Build the image (adds busybox utilities to the upstream image)
docker compose build

# 4. Start
docker compose up -d

# 5. Open https://<APP_TRAEFIK_HOST>
#    The first person to register becomes the admin.
#    Once all accounts are set up, set VIKUNJA_ENABLEREGISTRATION=false in .env.
```

## Authentik OIDC

With Authentik, users log in through your central identity provider instead of managing a separate Vikunja password. Authentik handles the login page, MFA, and session.

### In Authentik

Use **Applications → Create with Provider** to create both in one step:

1. **Provider type**: `OAuth2/OpenID Connect`
2. **Redirect URI** (type: **Strict**): `https://<APP_TRAEFIK_HOST>/auth/openid/authentik`
3. **Signing key**: select any available key
4. Copy the **Client ID**, **Client Secret**, and **application slug**
5. **Policy / Group / User Bindings** → add the groups or users who should have access

### Activate in `.env`

```env
VIKUNJA_AUTH_OPENID_ENABLED=true
AUTHENTIK_DOMAIN=auth.example.com
AUTHENTIK_APP_SLUG=vikunja          # the slug you set in Authentik
OIDC_CLIENT_ID=<client-id>
```

### Write the client secret

```bash
echo -n "<client-secret>" > .secrets/oidc_secret.txt
docker compose up -d --force-recreate vikunja
```

Users now see an **"Log in with Authentik"** button. The login page also auto-redirects to Authentik (no button click needed) — this is handled by a Traefik rule already configured in `docker-compose.yml`.

### Group → team sync (optional)

Authentik groups can be automatically mirrored as Vikunja teams.

1. In Authentik, create a scope mapping named `vikunja_scope`:
   ```python
   groupsDict = {"vikunja_groups": []}
   for group in request.user.ak_groups.all():
       groupsDict["vikunja_groups"].append({"name": group.name, "oidcID": group.num_pk})
   return groupsDict
   ```
2. Add `vikunja_scope` to the provider → Advanced protocol settings → Scopes
3. In `.env`, extend the scope:
   ```env
   # Add to docker-compose.yml environment or override via .env:
   VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_SCOPE=openid profile email vikunja_scope
   ```

## Access control

| Setting | What it does | Recommended value |
|---|---|---|
| `VIKUNJA_ENABLEREGISTRATION` | Show/hide the "Create account" link | `true` during setup, `false` after |
| `VIKUNJA_LOCAL_AUTH_ENABLED` | Show/hide the username/password form | Keep `true` as emergency fallback |
| `VIKUNJA_AUTH_OPENID_ENABLED` | Enable Authentik login button | `true` once Authentik is configured |

**Why keep local login enabled?** If Authentik is temporarily unreachable, you can still access Vikunja with a local admin account. Users who log in via Authentik are unaffected by this setting — it only controls whether the password form is visible.

If you prefer SSO-only (no password form shown at all): set `VIKUNJA_LOCAL_AUTH_ENABLED=false` after confirming Authentik works. If you ever get locked out, set it back to `true` and restart the container.

## SMTP / Email

Vikunja can send task reminders and password reset emails.

```bash
# Get the SMTP key from your provider (Brevo: SMTP & API → SMTP Keys)
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

## Branding

You can replace the Vikunja logo with your own. The logo must be reachable via HTTPS (host it anywhere — your own server, a CDN, or even as a static file on another service).

```env
VIKUNJA_CUSTOMLOGOURL=https://your-domain.com/logo.png
VIKUNJA_CUSTOMLOGOURLDARK=https://your-domain.com/logo-dark.png  # optional
VIKUNJA_ALLOWICONCHANGES=false  # prevents seasonal changes overriding your logo
```

Legal footer links (shown at the bottom of the login page):
```env
VIKUNJA_IMPRINTURL=https://your-domain.com/imprint
VIKUNJA_PRIVACYURL=https://your-domain.com/privacy
```

## Open items

- [x] Authentik OIDC configured and live-tested
- [ ] Disable registration once all accounts exist: `VIKUNJA_ENABLEREGISTRATION=false`
- [ ] SMTP: configure outgoing email (see SMTP section above)
- [ ] Custom logo (optional)
- [ ] Test `read_only: true` filesystem — currently disabled pending verification

## Verify

- [x] Both containers healthy: `docker compose ps`
- [x] Login page loads at the configured domain
- [x] First registration creates an admin account
- [x] Authentik button appears and auto-redirect works
- [x] Logging in via Authentik creates a user account automatically
- [x] Creating a project and task — data persists after `docker compose restart`
- [x] Kanban view works
- [ ] Password reset email arrives (requires SMTP)
- [ ] Task reminder email arrives (requires SMTP)

## Security

| Control | Status | Notes |
|---|---|---|
| `no-new-privileges` | ✅ | Both containers |
| Secrets | ✅ | All credentials in Docker Secrets, never in environment variables |
| Database | ✅ | Not reachable from outside — internal network only |
| Docker socket | ✅ | Not mounted |
| SSO | ✅ | Authentik OIDC — live-tested |
| Auto-redirect | ✅ | Login page redirects directly to Authentik |
| Real client IP | ✅ | Read from `X-Forwarded-For` (Traefik) for accurate rate limiting |
| Rate limiting | ✅ | Enabled |
| Read-only filesystem | ⬜ | Not yet verified — enable after testing |

## Notes

- **PostgreSQL vs SQLite**: PostgreSQL is required for multi-user setups (SQLite only for personal single-user use).
- **Uploaded files**: stored in the `vikunja_files` Docker volume — include this in your backups.
- **Health check**: the built-in `vikunja healthcheck` command fails every time because it starts without the database password. We replaced it with an HTTP check against the running server. See `docs/bugfixes/vikunja-openproject-2026-05-06.md`.
- **DNS on self-hosted servers**: the container must be able to resolve the Authentik hostname. On a server with public DNS this works automatically. On test servers, add the hostname to `/etc/hosts` on the Docker host. See `docs/bugfixes/vikunja-openproject-2026-05-06.md` Bug 5.
- **Authentik policy binding required**: the Vikunja application in Authentik must have at least one Group/User binding — without it Authentik returns 403 on the login endpoint.
- **Postgres version**: pinned to `17-alpine` to match the blueprint standard. Upstream docs mention `postgres:18` — no hard dependency on the version.
