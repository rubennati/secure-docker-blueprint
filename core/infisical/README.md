# Infisical

> **Status: 🚧 Preview** — v0.162.13 · 2026-07-26 · config complete, **not yet verified on a live server**

Self-hosted central secret manager. Instead of distributing and re-filling `.env` files per app
per server, manage every secret in one place; servers and apps pull what they need over the
network (CLI / machine identity). An optional, central alternative to per-server Docker Secrets.

> **⚠️ This holds every other app's secrets.** Default access is **VPN-only** (`acc-tailscale`) —
> a central secret store must not sit on the public internet. Other servers reach it over
> Tailscale. Exposing it publicly (`acc-public`) is a deliberate, high-risk decision.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `infisical/infisical:v0.162.13` | Backend + web UI + API (port 8080) |
| `db` | `postgres:16-alpine` | Encrypted secret store, users, projects |
| `redis` | `redis:7.4-alpine` | Cache + job queue |

Infisical has no `_FILE` support, so `config/entrypoint.sh` injects secrets from Docker Secret
files and then execs the image's `./standalone-entrypoint.sh` (which runs DB migrations on boot).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, SMTP_* (optional)

mkdir -p .secrets volumes/postgres volumes/redis
openssl rand -hex 32 > .secrets/db_pwd.txt           # hex = URL-safe for the DB URI
openssl rand -hex 16 > .secrets/encryption_key.txt   # Infisical ENCRYPTION_KEY (32 hex chars)
openssl rand -base64 32 | tr -d '\n' > .secrets/auth_secret.txt
touch .secrets/smtp_password.txt                     # optional

docker compose up -d
docker compose logs app --follow    # watch for migrations + server start

# https://<APP_TRAEFIK_HOST>  (over VPN) — create the first (admin) account
```

## Security Model

| Concern | How handled |
|---------|-------------|
| Access | **VPN-only** (`acc-tailscale`) by default — not public |
| DB password | Docker Secret (`db_pwd.txt`) — injected via entrypoint, never in `.env` |
| `ENCRYPTION_KEY` / `AUTH_SECRET` | Docker Secrets — injected via entrypoint, never in `.env` |
| SMTP password | Docker Secret (`smtp_password.txt`) |
| Postgres / Redis | `app-internal` (`internal: true`) — not reachable from host |
| Redis | `read_only: true`, `cap_drop: ALL`, `tmpfs` |
| Privilege escalation | `no-new-privileges:true` + `cap_drop: ALL` on all services |
| Resource limits | `deploy.resources` (memory/cpus/pids) on all services |

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `infisical-db` · database `infisical` · user `infisical` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) |
| **Reproducible** | `./volumes/redis` — cache |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: infisical
      container: infisical-db
      username: infisical
      password: "{credential file /srv/docker/core/infisical/.secrets/db_pwd.txt}"
```

**`.secrets/encryption_key.txt` is the backup.** Everything this service stores is
encrypted with it, so a database dump without the key is ciphertext and nothing
else. Restoring the key alone recovers nothing either — both are needed, and
storing them in the same place turns two controls into one.

Keep the key off this host and out of the borgmatic repository the database goes
into. That is inconvenient on purpose: a single compromised archive should not
yield both halves.

**Restore order:** database first, then the app.

## Local testing (no Traefik)

Run standalone on `http://localhost:8080` — plain env, no Traefik/Docker Secrets:

```bash
cp .env.local.example .env.local   # fill values (openssl one-liners inside)
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — create the first account
```

## Verify on first deploy (Preview → Ready gate)

This config follows the standard but has **not** been run on a server yet. Confirm before marking ✅:

- [ ] `docker compose config` clean; `docker compose up -d` — all three healthy, no restart loop
- [ ] Logs show DB migrations succeed and the server starts (entrypoint execs `standalone-entrypoint.sh`)
- [ ] Secrets injected — no `ENCRYPTION_KEY`/`AUTH_SECRET`/`DB_*` values in `docker inspect infisical-app`
- [ ] `GET /api/status` returns 200 (healthcheck); UI loads over VPN and first account can be created
- [ ] A machine identity / CLI on another server can authenticate and read a secret

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
