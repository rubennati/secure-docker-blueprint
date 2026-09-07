# Tymeslot

Meeting scheduling on your own server: booking pages guests pick a slot on,
calendar sync with Google, Outlook, Apple, Nextcloud and any CalDAV server, video
links for Meet, Teams, Zoom or your own room, and the confirmation and reminder
mail that goes with it. Elixir/Phoenix LiveView with PostgreSQL. AGPL-3.0,
published by Diletta Luna OÜ (Tallinn, Estonia).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `tymeslot-app` | `luka1thb/tymeslot:<version>-slim` | Web UI and job queue in one BEAM, port 4000 |
| `db` | `postgres:17` | Database, on `app-internal` only |

The `-slim` tag carries no PostgreSQL server. The plain tag bundles one inside
the application container, which would put the database on `proxy-public`;
upstream's own `docker-compose.with-postgres.yml` is the two-container shape
this stack follows.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, the SMTP block, EMAIL_FROM_*

# 2. Secrets and data directories
mkdir -p .secrets volumes/postgres volumes/data
openssl rand -base64 64 | tr -d '\n' > .secrets/secret_key_base.txt       # at least 64 characters
openssl rand -base64 48 | tr -d '\n' > .secrets/data_encryption_key.txt   # never rotate
openssl rand -hex 32    | tr -d '\n' > .secrets/db_pwd.txt
touch .secrets/smtp_password.txt      # relay password — must be non-empty when EMAIL_ADAPTER=smtp
chmod 700 .secrets && chmod 600 .secrets/*.txt

# 3. Start
docker compose up -d
docker compose logs tymeslot-app --follow      # "Running TymeslotWeb.Endpoint" = up
```

The first boot runs every migration before the server starts — about thirty
seconds on an empty database. The healthcheck allows two minutes.

**The first account to register becomes the instance admin.** Register, then
close registration: `REGISTRATION_ENABLED=false` in `.env` and
`docker compose up -d`, or toggle it at `/admin`, which overrides the file.

## Verify

```bash
docker compose ps                                   # both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/               # 302 to the login page
docker compose exec tymeslot-app bash -c 'exec 3<>/dev/tcp/127.0.0.1/4000; printf "GET /healthcheck HTTP/1.0\r\n\r\n" >&3; cat <&3'
```

The last one prints `{"status":"ok","checks":{"oban":"ok","database":"ok"}}`
— database and job queue both answer. Then register, create a meeting type,
and open its booking page in a private window.

## Mail

With `EMAIL_ADAPTER=test`, the default, every message is discarded without an
error: verification, password reset, booking confirmation, reminder. The
application looks healthy and nobody is told anything.

`EMAIL_ADAPTER=smtp` needs a host, a username and a non-empty password in
`.secrets/smtp_password.txt`, or the application refuses to boot. The port
decides the encryption: 587 forces STARTTLS, 465 implicit TLS, any other port
opportunistic TLS. For trying the stack out, `apps/mailpit` accepts all of that
on port 1025 and shows every message in a browser.

## Integrations

Calendar and video providers are connected per user from the dashboard, once
the provider credentials exist in the compose `environment:` block:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_STATE_SECRET`, the
`OUTLOOK_*` and `ZOOM_*` equivalents. The redirect URIs to register at the
provider are listed in upstream's `.env.example`.

What each one needs from the network:

| Integration | Needs |
|---|---|
| Google, Outlook, Zoom OAuth | a browser that reaches this host — the callback is a redirect, not an inbound call |
| Calendar push notifications (`WEBHOOK_BASE_URL`) | the provider must reach this host from the public internet; unset, sync polls every 15 minutes |
| Stripe, Slack OAuth, Telegram shared bot | inbound webhooks — a publicly reachable host |
| CalDAV, Nextcloud, MiroTalk on private addresses | `ALLOW_PRIVATE_IPS_FOR_CALENDAR=true` or `_VIDEO`; the SSRF guard blocks them otherwise, and the switches are separate on purpose |

## Security model

- **Access policy is the deployment decision.** A booking page exists for
  guests, so a production instance serves `acc-public`. The stack ships
  `acc-tailscale` and leaves that decision to you; on a public router, put
  `crowdsec-basic@file,` in `APP_TRAEFIK_THREAT` and keep registration closed.
- **`sec-3`.** A first load is about ten requests, far below the soft burst of
  50. The application sends its own nonce-based CSP with
  `frame-ancestors 'none'`, `nosniff`, a referrer policy and
  `Secure; HttpOnly; SameSite=Lax` cookies; the chain adds HSTS and
  `X-Frame-Options: DENY`, and the two agree.
- **Embedding is blocked as shipped.** Booking pages can be embedded in other
  sites (`embed.js`), and `DENY` refuses that. If you want it, name the parent
  origins with a per-app `frame-ancestors` middleware on the embed routes
  rather than dropping the header.
- **Client addresses reach the application.** It trusts `X-Forwarded-For` from
  private ranges, which covers Traefik on `proxy-public`, so its own rate
  limiters — signup, booking, healthcheck — key on the real client. The CGNAT
  range Tailscale uses is not trusted as a proxy, so a VPN client cannot forge
  the header.
- **Root at start, then a privilege drop.** The image's start script runs as
  root to prepare `/app/data` and switches to uid 1000 for the migrations and
  the server. `cap_drop: ALL` with `CHOWN`, `DAC_OVERRIDE`, `SETGID`, `SETUID`
  is the set that needs; the root filesystem is read-only. One `su` process
  stays as root for the container's lifetime.
- **Secrets through the entrypoint wrapper.** No `_FILE` variant exists;
  `config/entrypoint.sh` exports the four secrets from `/run/secrets/`.
  `DATA_ENCRYPTION_KEY` is optional upstream and required here: without it,
  stored calendar credentials are tied to `SECRET_KEY_BASE`, and adding the key
  later means upstream's re-encryption sweep.
- **Outbound.** The IANA time-zone version at boot (`data.iana.org`), the
  hosted documentation for dashboard help links (`DOCS_ARTICLE_BASE_URL`
  redirects those), and the calendar and video APIs once a user connects them.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `tymeslot-db` · database `tymeslot` · user `tymeslot` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/data/uploads` (profile and branding uploads) — bind mounts |
| **Reproducible** | `./volumes/data/tzdata` — seeded from the release on first boot |
| **Secrets** | `.secrets/secret_key_base.txt` and `.secrets/data_encryption_key.txt` are part of the backup: stored calendar credentials are encrypted with them, and a restore without them leaves every integration disconnected |
| **Quiescing** | Not needed. The dump is consistent on its own; the app can keep running. |

```yaml
postgresql_databases:
    - name: tymeslot
      container: tymeslot-db
      username: tymeslot
      password: "{credential file /srv/docker/apps/tymeslot/.secrets/db_pwd.txt}"
```

**Restore order:** secrets, then database, then the app. The app runs its
migrations at boot, so starting it against a half-restored database writes
migrations over the restore.

## Administration

```bash
# Promote, demote, list admins — as the app user, not root
docker compose exec -u 1000 tymeslot-app bin/tymeslot rpc 'Tymeslot.Release.promote_admin("you@example.com")'
docker compose exec -u 1000 tymeslot-app bin/tymeslot rpc 'Tymeslot.Release.list_admins()'

# Logs are JSON on stdout; the migration lines are the noisy ones
docker compose logs tymeslot-app --since 10m | grep -v ecto_sql
```

## Known issues

- **Releases are frequent** — eight between 2026-08-29 and 2026-09-06.
  Migrations run at boot, so every upgrade touches the database; back up first
  and move the digest pin on purpose, not on every tag. The upgrade checklist in
  `UPSTREAM.md` includes a diff of the start script, which the entrypoint
  wrapper depends on.
- **A booking end to end has not been exercised here.** Registration, the
  dashboard and the verification mail have; the guest side of a booking is the
  next thing to try on a real install.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, licence, upgrade checklist
- `docker-compose.local.yml` — the stack on one machine, no proxy, no mail
