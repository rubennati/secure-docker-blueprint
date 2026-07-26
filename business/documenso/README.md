# Documenso

> **Status: 🚧 Draft** — v2.15.0 · 2026-07-26 · config complete, **not yet verified on a live server**

Open-source document-signing platform — a self-hosted **DocuSign alternative**. Sibling e-sign
option: [`business/opensign/`](../opensign/).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `documenso/documenso:v2.15.0` | Remix web app + signing API (port 3000) |
| `db` | `postgres:16-alpine` | Documents, signatures, users |

No `_FILE` support → `config/entrypoint.sh` injects secrets from Docker Secret files and execs the
image CMD (`sh start.sh`, which runs Prisma migrations on boot). A signing certificate (`.p12`) is
mounted read-only at `/opt/documenso/cert.p12` — Documenso ships none, you generate it.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, SMTP_*, TZ

mkdir -p .secrets volumes/postgres
openssl rand -hex 32 > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/nextauth_secret.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/encryption_key.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/encryption_secondary_key.txt
touch .secrets/smtp_password.txt

# Signing certificate (Documenso ships none):
openssl req -x509 -newkey rsa:4096 -keyout /tmp/k.pem -out /tmp/c.pem -days 3650 -nodes -subj "/CN=Documenso"
PASS="$(openssl rand -hex 16)"; printf '%s' "$PASS" > .secrets/signing_passphrase.txt
openssl pkcs12 -export -out .secrets/cert.p12 -inkey /tmp/k.pem -in /tmp/c.pem -passout pass:"$PASS"
rm /tmp/k.pem /tmp/c.pem

docker compose up -d
docker compose logs app --follow   # watch migrations + server start
# https://<APP_TRAEFIK_HOST> — first user becomes the admin
```

## Security Model

| Concern | How handled |
|---------|-------------|
| DB password | Docker Secret — injected via entrypoint, never in `.env` |
| `NEXTAUTH_SECRET`, encryption keys | Docker Secrets — injected via entrypoint |
| Signing passphrase | Docker Secret; the `.p12` mounted `:ro` (never committed — `.secrets/` gitignored) |
| SMTP password | Docker Secret |
| Postgres | `app-internal` (`internal: true`) — not reachable from host |
| Privilege escalation | `no-new-privileges:true` + `cap_drop: ALL` |
| HTTP security headers | Traefik `sec-3` chain (public-facing, stores PII) |
| Resource limits | `deploy.resources` (memory/cpus/pids) |

## Local testing (no Traefik)

```bash
cp .env.local.example .env.local     # fill values; generate .secrets/cert.p12 first
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000
```

## Verify on first deploy (Draft → Ready gate)

Config follows the standard but has not been run here. Confirm:

- [ ] `docker compose up -d` — both healthy; logs show migrations + server start (entrypoint execs `sh start.sh` in `/app/apps/remix`)
- [ ] Secrets injected — no secret values in `docker inspect documenso-app`
- [ ] `cert.p12` mounted and the signing passphrase matches — a document can be signed
- [ ] UI loads over HTTPS; first account created; a signature request email is delivered

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, deviations
- Sibling: [`business/opensign/`](../opensign/) — alternative e-sign platform
