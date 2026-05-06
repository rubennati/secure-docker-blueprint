# Listmonk

> **Status: 🚧 Draft**

Self-hosted newsletter, mailing list manager, and transactional mail. Go single-binary app + Postgres backend. Handles subscriber management, double-opt-in, campaign sending, tracking (open/click), bounce processing, list segmentation.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `listmonk/listmonk:latest` | Admin UI + sender + subscriber endpoints |
| `db` | `postgres:16-alpine` | Subscribers, campaigns, templates, analytics |

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/postgres volumes/uploads
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

ADMIN_PWD=$(openssl rand -base64 24 | tr -d '\n')
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PWD}|" .env
echo "Admin password: ${ADMIN_PWD}"

docker compose up -d
# First boot runs --install --idempotent → Postgres schema + admin user.
# Second start skips install.
docker compose logs app --follow
# Watch for: "Listening on :9000"

# https://<APP_TRAEFIK_HOST>/admin
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

- **`ADMIN_PASSWORD` only read on first install** — change in the UI afterwards and remove from `.env`.
- **`DB_PWD_INLINE` duplicates the DB password** — Listmonk has no `_FILE` support on `LISTMONK_db__password`.
- **`no-new-privileges:true`** on both services.
- **Postgres on `app-internal` (`internal: true`)** — not reachable from outside.
- **SMTP credentials** live in the admin UI (Settings → SMTP) after setup — not in `.env`. They're stored encrypted in the DB.

## Known Issues

- **Live-tested: no.**
- **`APP_TAG=latest`** — pin to a specific version for reproducibility.
- **Bounce processing** requires either IMAP config to your sender mailbox or an SMTP relay with bounce-webhook support (AWS SES, Mailgun, Postmark).
- **Media uploads** (logo, campaign images) land in `volumes/uploads/`. Back up together with the Postgres dump.

## Integration with n8n

For event-driven flows (new subscriber → CRM row, unsubscribe → alert):
- Admin UI → Settings → Webhook events → point at `https://n8n.example.com/webhook/<path>`
