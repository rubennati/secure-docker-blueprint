# n8n

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Workflow automation — visual builder for chaining HTTP calls, webhooks, scheduled jobs, and a large library of third-party integrations (Slack, Airtable, OpenAI, databases, etc.). Free self-hosted Community Edition.

## Architecture

Single-container deployment with n8n's built-in SQLite database:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `docker.n8n.io/n8nio/n8n:latest` | Web UI + workflow executor + webhook endpoint |

Data lives in `./volumes/data/` (SQLite DB, credentials, workflow exports).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, BASIC_AUTH_USER

# 2. Generate basic-auth password
BAUTH_PWD=$(openssl rand -base64 24 | tr -d '\n')
sed -i "s|^BASIC_AUTH_PASSWORD=.*|BASIC_AUTH_PASSWORD=${BAUTH_PWD}|" .env
echo "Basic auth password: ${BAUTH_PWD}"

# 3. Generate encryption key (CRITICAL — back this up!)
mkdir -p .secrets
openssl rand -hex 32 > .secrets/n8n_encryption_key.txt
# This key encrypts all stored credentials. Losing it = losing every
# OAuth token and API key saved in n8n.

# 4. Create data volumes
mkdir -p volumes/data volumes/files
# n8n runs as UID 1000 — ensure writable
sudo chown -R 1000:1000 volumes/data volumes/files

# 5. Start
docker compose up -d

# 6. Open UI and set the owner account on first visit
# https://<APP_TRAEFIK_HOST>
# Basic auth (from .env) → owner account setup wizard
```

## Verify

```bash
docker compose ps                              # app running
curl -fsSI https://<APP_TRAEFIK_HOST>/healthz  # 200 OK
```

## Security Model

- **Basic auth in front of the UI** — the Community Edition has no built-in multi-user auth unless you enable it. Basic auth gates access to everything.
- **`N8N_ENCRYPTION_KEY`** encrypts every credential stored in n8n (OAuth tokens, API keys, SMTP passwords). Stored in `.secrets/n8n_encryption_key.txt`. **Back this file up off-host** — losing it means re-entering every credential.
- **Default access `acc-tailscale` + `sec-3`** — n8n stores API tokens for many third parties; VPN-only is a safer default than public. Switch to `acc-public + sec-2` only if you really need external webhook endpoints and are willing to accept the exposure.
- **`N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS: true`** — n8n refuses to start if its config file is world-readable.
- **`N8N_RUNNERS_ENABLED: true`** — uses task runners for isolated code execution (n8n >= 1.53).
- **`no-new-privileges:true`** on the container.

## Known Issues

- **Live-tested: no.** Expect minor surprises, especially first-run ownership on `volumes/data/`.
- **Webhook exposure** — even with `acc-tailscale`, webhooks invoked by external services (e.g. GitHub, Stripe) will not reach n8n unless you add a second Traefik router with `acc-public` on specific paths (`/webhook/*`). Not configured here.
- **`APP_TAG=latest` is not reproducible** — pin to a specific version for stable deployments. n8n has frequent breaking changes in minor bumps.
- **Queue mode / horizontal scaling not configured** — this is a single-executor deployment. For high-throughput workflows, add Redis + a worker service (see upstream docs).
- **SQLite lock contention** — under heavy webhook load, SQLite can bottleneck. Switch to Postgres by setting `DB_TYPE=postgresdb` + related env vars; requires adding a `db:` service.

## Details

- [UPSTREAM.md](UPSTREAM.md)
