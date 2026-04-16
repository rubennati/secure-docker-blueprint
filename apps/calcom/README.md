# Cal.com

Self-hosted scheduling / booking platform (Calendly alternative). Built on Next.js + Prisma, backed by PostgreSQL.

## Architecture

Two services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `calcom/cal.com` | Next.js web app + REST/tRPC API on port `3000` |
| `db` | `postgres:17` | Primary data store (users, event types, bookings, webhooks) |

Cal.com bundles everything else (job queue, caching, sessions) into the Next.js process — no Redis or separate worker container.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, CALCOM_EMAIL_*, TZ

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
openssl rand -hex 16     | tr -d '\n' > .secrets/encryption_key.txt
printf '%s' 'YOUR-SMTP-PASSWORD' > .secrets/smtp_pwd.txt

# 3. Copy the DB password into .env (see "Known Issues")
# DB_PWD_INLINE must be identical to .secrets/db_pwd.txt:
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 4. Start
docker compose up -d

# 5. First boot runs Prisma migrations; takes ~60s
docker compose logs app --follow

# 6. Complete admin setup in the browser
# https://<APP_TRAEFIK_HOST>/auth/setup
```

Default access policy is `acc-public` + `sec-2` — booking pages need to be reachable by anyone.

## Verify

```bash
docker compose ps                                   # Both services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/api/health    # 200 OK
docker compose logs app --tail 100                  # No Prisma / NEXTAUTH errors
```

Create a test user, set up an event type, and confirm booking emails arrive.

## Security Model

- Database is on `app-internal` (`internal: true`) — not reachable from `proxy-public`
- Four Docker Secrets: `DB_PWD`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY`, `SMTP_PWD`
- `NEXTAUTH_SECRET` signs session cookies — rotating it invalidates every logged-in session
- `CALENDSO_ENCRYPTION_KEY` encrypts third-party API credentials stored in the DB (Google Calendar OAuth tokens, Zoom keys, etc.). **Losing or changing this key means re-linking every connected calendar and meeting provider.**
- `no-new-privileges:true` on both services
- Telemetry disabled by default (`CALCOM_TELEMETRY_DISABLED=1`)

## Known Issues

### `DB_PWD_INLINE` duplicates the DB secret

Cal.com's Prisma client reads **one single `DATABASE_URL`** — no URL-from-parts, no `DATABASE_URL_FILE`. The compose file assembles:

```
postgresql://${DB_USER}:${DB_PWD_INLINE}@db:5432/${DB_NAME}
```

The password therefore has to sit inline in `.env`. `.secrets/db_pwd.txt` is still used by Postgres itself (`POSTGRES_PASSWORD_FILE`), so the same password lives in two places and they must be kept in sync manually. Mismatch = Prisma fails to connect at startup.

A cleaner fix is an entrypoint wrapper that reads the secret and builds `DATABASE_URL` at runtime. That's a functional change outside the scope of a documentation pass — tracked for a dedicated refactor.

### Encryption key format

`CALENDSO_ENCRYPTION_KEY` must be a 32-character hex string. `openssl rand -hex 16` produces exactly that. Do **not** use `-base64 32` — base64 output contains `+/=` characters that Cal.com's decryption logic rejects.

### First boot runs migrations on every version bump

The `app` container runs Prisma migrations on start. On a version bump this delays healthy status; the healthcheck uses `start_period: 60s` to accommodate it. Very large DBs may need more — adjust if you see the container flap.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
