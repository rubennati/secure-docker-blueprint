# Listmonk

**Status: ✅ Ready — v6.1.0 · 2026-05-11**

Self-hosted newsletter, mailing list manager, and transactional mail. Go single-binary app + Postgres backend. Handles subscriber management, double-opt-in, campaign sending, tracking (open/click), bounce processing, list segmentation.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `listmonk/listmonk:v6.1.0` | Admin UI + sender + subscriber endpoints |
| `db` | `postgres:16-alpine` | Subscribers, campaigns, templates, analytics |

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/postgres volumes/uploads
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

docker compose up -d
# First boot: --install --idempotent → creates Postgres schema.
# Admin user is NOT created from env — create it on first login via the web UI.
docker compose logs app --follow
# Watch for: "http server started on [::]:9000"

# https://<APP_TRAEFIK_HOST>
# → First visit prompts you to create the super admin account.
```

## Access split (recommended for production)

Default is `acc-public + sec-2` so subscriber endpoints (`/subscription/*`, `/link/*`, `/campaign/*`) work for external users. The admin UI at `/admin` is then *also* public.

For "admin VPN-only + subscriber endpoints public", add a second Traefik router:

```yaml
# Add to docker-compose.yml labels section:
- "traefik.http.routers.listmonk-admin.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/admin`)"
- "traefik.http.routers.listmonk-admin.priority=100"
- "traefik.http.routers.listmonk-admin.entrypoints=websecure"
- "traefik.http.routers.listmonk-admin.tls=true"
- "traefik.http.routers.listmonk-admin.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
- "traefik.http.routers.listmonk-admin.middlewares=acc-tailscale@file,sec-3@file"
- "traefik.http.routers.listmonk-admin.service=${COMPOSE_PROJECT_NAME}"
# The existing router (priority 1 implicit) catches subscriber paths publicly.
```

## Security Model

- **Admin user created via web UI on first visit** — Listmonk v6+ removed `admin_username`/`admin_password` from env/config. The first visit to `/` shows a setup wizard to create the super admin. Do not use the old `ADMIN_USER`/`ADMIN_PASSWORD` env vars — they are ignored and trigger a deprecation warning.
- **`DB_PWD_INLINE` duplicates the DB password** — Listmonk has no `_FILE` support on `LISTMONK_db__password`.
- **`no-new-privileges:true`** on both services.
- **Postgres on `app-internal` (`internal: true`)** — not reachable from outside.
- **SMTP credentials** live in the admin UI (Settings → SMTP) after setup — not in `.env`. They're stored encrypted in the DB.

## Known Issues

- **UI warning about admin credentials** — after first login, Listmonk shows a banner asking to remove `admin_username`/`admin_password` from config. These fields are already absent from this blueprint's setup; the banner can be dismissed.
- **Campaign/template preview uses an iframe** — the preview panel renders `GET /api/campaigns/:id/preview` in an `<iframe>`. `X-Frame-Options: deny` blocks this. The default is therefore `sec-2e` (`SAMEORIGIN`) instead of `sec-2` (`deny`).
- **Bounce processing** requires either IMAP config to your sender mailbox or an SMTP relay with bounce-webhook support (AWS SES, Mailgun, Postmark).
- **Media uploads** (logo, campaign images) land in `volumes/uploads/`. Back up together with the Postgres dump.

## Integration with n8n

For event-driven flows (new subscriber → CRM row, unsubscribe → alert):
- Admin UI → Settings → Webhook events → point at `https://n8n.example.com/webhook/<path>`
