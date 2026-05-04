# Cal.diy

> **Read first:** Cal.diy is the MIT-licensed community edition of Cal.com, spun out in 2026 when Cal.com moved its production codebase behind a closed-source licence. Upstream explicitly labels Cal.diy as "strictly for personal, non-production use" with no security guarantees. **Do not use for business-critical scheduling** without understanding that trade-off.

For an alternative with an established track record and no build dependency, see [`apps/easyappointments/`](../easyappointments/) (PHP + MariaDB, GPL-3.0).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/rubennati/cal.diy:v6.2.0` | Next.js web app + scheduling engine |
| `db` | `postgres:17.4` | Users, event types, bookings, team memberships |
| `redis` | `redis:7.4-alpine` | Session cache + job queue |

The image is built from [`rubennati/cal.diy`](https://github.com/rubennati/cal.diy) — a fork of the upstream that publishes versioned images to GHCR. Upstream does not publish a reliable pre-built image.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, APP_TAG, TZ, EMAIL_*, branding vars

# 1. Generate secrets
mkdir -p .secrets volumes/postgres volumes/redis
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/encryption_key.txt
openssl rand -hex 16 | tr -d '\n' > .secrets/cron_api_key.txt
touch .secrets/smtp_password.txt  # write SMTP password here if needed

# 2. Generate VAPID keys (required — app errors on boot without them)
# No Node.js on the server? Use a temporary container:
docker run --rm node:lts-alpine npx --yes web-push generate-vapid-keys
# Copy the output into VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in .env

# 3. Update ALLOWED_HOSTNAMES in .env to match APP_TRAEFIK_HOST:
#    ALLOWED_HOSTNAMES='"cal.yourdomain.com"'

# 4. Start
docker compose up -d
docker compose logs app --follow
# Watch for: "ready on port 3000"

# https://<APP_TRAEFIK_HOST>
# Setup wizard runs on first visit — first user becomes the owner.
```

## Security Model

| Concern | How handled |
|---------|-------------|
| DB password | Docker Secret (`db_pwd.txt`) — never in `.env` |
| `NEXTAUTH_SECRET` | Docker Secret (`nextauth_secret.txt`) — never in `.env` |
| `CALENDSO_ENCRYPTION_KEY` | Docker Secret (`encryption_key.txt`) — never in `.env` |
| `CRON_API_KEY` | Docker Secret (`cron_api_key.txt`) — protects `/api/cron/*` |
| SMTP password | Docker Secret (`smtp_password.txt`) — never in `.env` |
| Secret injection | Custom entrypoint (`config/entrypoint.sh`) reads secrets at runtime |
| Postgres | `app-internal` network (`internal: true`) — not reachable from host |
| Redis | `app-internal`, `read_only: true`, `cap_drop: ALL` |
| Host header injection | `ALLOWED_HOSTNAMES` set to deployment hostname |
| Privilege escalation | `no-new-privileges:true` on all services |
| Resource abuse | `deploy.resources` limits on all services |
| Community-maintained security | No Cal.com, Inc. incident response — watch upstream releases manually |

## Known Issues

- **Live-tested: yes (v6.2.0, 2026-05-04)**
- **VAPID keys are mandatory** — skip step 2 and the app logs `Error: No key set vapidDetails.publicKey` on every request.
- **`CLIENT_FETCH_ERROR` if `NEXTAUTH_URL` is wrong** — must include `/api/auth` path. Already set correctly in `docker-compose.yml`.
- **`/api/health` returns 500** — Node.js stream API incompatibility in this image version causes a `TypeError` on the health endpoint. The healthcheck falls back to `nc -z 127.0.0.1 3000` (TCP) which works fine. The app itself runs normally.
- **Feature parity with Cal.com is partial** — Teams, Organisations, advanced Insights, SSO/SAML, and Workflows are removed from the community edition.
- **Google/Outlook integrations require OAuth app registration** — see [upstream docs](https://github.com/rubennati/cal.diy#obtaining-the-google-api-credentials).

## Details

- [UPSTREAM.md](UPSTREAM.md)
- Sibling: [`apps/easyappointments/`](../easyappointments/) — PHP-stack alternative, no build dependency
