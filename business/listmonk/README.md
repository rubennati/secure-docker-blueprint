# Listmonk

Self-hosted newsletter, mailing list manager, and transactional mail. Go single-binary app + Postgres backend. Handles subscriber management, double-opt-in, campaign sending, tracking (open/click), bounce processing, list segmentation.

## Open findings

The pinned image, `listmonk/listmonk:v6.2.0`, ships with 1 CRITICAL vulnerability that has a published fix, in the Echo web framework's proxy middleware. v6.2.0 is the newest stable release.

**Risk:** listmonk does not appear to use that middleware (checked by code search only). Watch for the v7 stable release.

The PostgreSQL image, `postgres`, carries CVE-2025-68121 in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go. The `18.6-alpine` build also carries brotli-libs 1.2.0-r1 (CVE-2026-111497); Alpine has the fix, the official image is not rebuilt on it yet.

**Risk:** the gosu flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. brotli is linked through libcurl for PostgreSQL 18's OAuth support, which this stack does not configure. Both clear with upstream's next rebuild.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `listmonk-install` | `listmonk/listmonk:v6.2.0` | One-shot: schema on first start, migrations after an upgrade |
| `smtp-guard` | `postgres:18.6-alpine` | One-shot: replaces upstream's SMTP placeholder before the app starts (below) |
| `listmonk-app` | `listmonk/listmonk:v6.2.0` | Admin UI + sender + subscriber endpoints — UID 1000, no capabilities |
| `db` | `postgres:18.6-alpine` | Subscribers, campaigns, templates, analytics |

## Try it locally

Runs on `http://localhost:9000` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local # fill the __REPLACE_ME__ values
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:9000
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/postgres volumes/uploads
# listmonk runs as APP_UID:APP_GID (default 1000:1000), not as root
sudo chown 1000:1000 volumes/uploads
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

docker compose up -d
# listmonk-install creates the schema (first boot) or migrates it; smtp-guard
# replaces the SMTP placeholder; then listmonk-app starts. Both one-shots exit 0.
docker compose ps -a
docker compose logs smtp-guard   # "smtp placeholder replaced by smtp.invalid" once, then nothing

# Over the VPN: https://<APP_TRAEFIK_HOST>/admin
# → the first visit creates the super admin account.
```

**The stack ships closed** (`APP_TRAEFIK_ACCESS=access-vpn`), because of what the step 8
lab host measured (v6.2.0; final audit FA-01, FA-02):

- **The first visit to `/admin` creates the super admin** — there is no setup secret. With a
  public route that is whoever arrives first. Create the account over the VPN.
- **The SMTP settings ship with upstream's placeholder `smtp.yoursite.com`**, a real domain
  that resolves to a third party. Before the guard, an opt-in mail for a public subscription
  — with the subscriber's address — was sent there on port 25 (it timed out on the lab host
  only because the provider blocks outbound 25). `smtp-guard` now replaces exactly that
  value with `smtp.invalid` (RFC 2606, never resolves) before the application loads its
  settings; a server you configured is never changed. Until you set one under
  **Settings → SMTP**, mail fails with `lookup smtp.invalid: no such host` and the
  subscription form answers `500` — nothing leaves the host (measured: 0 packets to
  25/465/587 from the stack's edge network during two subscriptions).
- Then open the subscriber paths: `access-public` for the whole host, or — better — the
  access split below, so `/admin` stays VPN-only.
- The session cookie is set `HttpOnly` without `Secure`, although `root_url` is `https://`.

**Outbound mail is not filtered by the stack.** The edge network has egress, which a real
relay on 587 or 465 needs; port 25 is blocked by many providers, not by the blueprint. A
per-network egress filter in the host ruleset is an open point, not implemented.

## Access split (recommended for production)

The shipped default is `access-vpn`: nothing is public until you open it. Subscriber endpoints (`/subscription/*`, `/link/*`, `/campaign/*`) need a public route for external readers; with `access-public` on the one router, the admin UI at `/admin` is *also* public.

For "admin VPN-only + subscriber endpoints public", add a second Traefik router:

```yaml
# Add to docker-compose.yml labels section:
- "traefik.http.routers.listmonk-admin.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/admin`)"
- "traefik.http.routers.listmonk-admin.priority=100"
- "traefik.http.routers.listmonk-admin.entrypoints=websecure"
- "traefik.http.routers.listmonk-admin.tls=true"
- "traefik.http.routers.listmonk-admin.middlewares=frame-self@file,${APP_TRAEFIK_HEADERS}@file,access-vpn@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}"
- "traefik.http.routers.listmonk-admin.service=${COMPOSE_PROJECT_NAME}"
# The existing router (priority 1 implicit) catches subscriber paths publicly.
```

## Security Model

- **Admin user created via web UI on first visit** — Listmonk v6+ removed `admin_username`/`admin_password` from env/config. The first visit to `/` shows a setup wizard to create the super admin. Do not use the old `ADMIN_USER`/`ADMIN_PASSWORD` env vars — they are ignored and trigger a deprecation warning.
- **`DB_PWD_INLINE` duplicates the DB password** — Listmonk has no `_FILE` support on `LISTMONK_db__password`.
- **No root:** `listmonk-app` and `listmonk-install` run as `APP_UID:APP_GID` (1000:1000) with `cap_drop: ALL`; `smtp-guard` as the image's `postgres` user (70) with `cap_drop: ALL`. Measured on the lab host: setup, login, API, subscription with the opt-in mail, campaign test send, a media upload (final audit FA-06). An existing installation needs `sudo chown -R 1000:1000 volumes/uploads` once before the upgrade.
- **`no-new-privileges:true`** on every service.
- **Postgres on `app-internal` (`internal: true`)** — not reachable from outside.
- **SMTP credentials** live in the admin UI (Settings → SMTP) after setup — not in `.env`. They're stored encrypted in the DB.

## What it sends outward

Listmonk requests `update.listmonk.app` to see whether a newer version exists.
It is a plain GET with no payload and no installation identifier — the vendor
learns the source address and the timing.

On by default. Turn it off in **Settings → General → Check for updates**; the
setting lives in the database.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `listmonk-db` · database `listmonk` · user `listmonk` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/uploads` (media referenced from campaigns) |
| **Reproducible** | nothing |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: listmonk
      container: listmonk-db
      username: listmonk
      password: "{credential file /srv/docker/business/listmonk/.secrets/db_pwd.txt}"
```

Subscriber lists and their opt-in state are database rows. Restoring an **older**
database is not a neutral act here: it can resurrect addresses that unsubscribed
after that backup was taken, and mail them again. Check the subscription table
against the unsubscribe log before the first send following a restore.

**Restore order:** database first, then the app.

## Known Issues

- **UI warning about admin credentials** — after first login, Listmonk shows a banner asking to remove `admin_username`/`admin_password` from config. These fields are already absent from this blueprint's setup; the banner can be dismissed.
- **Campaign/template preview uses an iframe** — the preview panel renders `GET /api/campaigns/:id/preview` in an `<iframe>`. `X-Frame-Options: deny` blocks this. The router therefore carries `frame-self@file` (`SAMEORIGIN`) before `${APP_TRAEFIK_HEADERS}@file`, whose `headers-standard` would send `deny`.
- **Bounce processing** requires either IMAP config to your sender mailbox or an SMTP relay with bounce-webhook support (AWS SES, Mailgun, Postmark).
- **Media uploads** (logo, campaign images) land in `volumes/uploads/`. Back up together with the Postgres dump.

## Integration with n8n

For event-driven flows (new subscriber → CRM row, unsubscribe → alert):

- Admin UI → Settings → Webhook events → point at `https://n8n.example.com/webhook/<path>`
