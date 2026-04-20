# OpenSign

> **Status: Draft — not yet live-tested.**

Self-hosted electronic signature platform — DocuSign / Adobe Sign alternative. Upload PDF/DOCX, define signing roles, send to signers, audit trail, certificates. GDPR-friendly since everything stays on your infrastructure.

## Architecture

Three-service stack with Traefik path-based split (same pattern as OpnForm):

| Service | Image | Purpose |
|---------|-------|---------|
| `ui` | `opensignlabs/opensign:latest` | React frontend |
| `api` | `opensignlabs/opensignserver:latest` | Parse Server backend + PDF signing engine |
| `db` | `mongo:6` | Documents, templates, users, audit log |

Traefik routes `/app/*` + `/api/*` to the API (priority 100), everything else to the UI (priority 1).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p .secrets volumes/mongodb volumes/api-files

# DSN-safe Mongo root password
openssl rand -hex 32 > .secrets/db_root_pwd.txt
sed -i "s|^DB_ROOT_PWD_INLINE=.*|DB_ROOT_PWD_INLINE=$(cat .secrets/db_root_pwd.txt)|" .env

# App IDs
sed -i "s|^APP_ID=.*|APP_ID=$(openssl rand -hex 16)|" .env
sed -i "s|^MASTER_KEY=.*|MASTER_KEY=$(openssl rand -hex 32)|" .env

# Configure mail (see .env.example — Mailgun OR SMTP)

docker compose up -d
docker compose logs api --follow
# Watch for: "parse-server-example running on port 8080"

# https://<APP_TRAEFIK_HOST>
# First account to register becomes admin
```

## Security Model

- **`MASTER_KEY` grants full Parse Server bypass** — keep it off-disk after bootstrap or move to a Docker Secret with a custom entrypoint reading `/run/secrets/MASTER_KEY`. Rotating requires coordinated API + UI config changes.
- **First-user-wins admin** — open the UI immediately after start.
- **DSN-safe Mongo password** — `@`, `:`, `/`, `?`, `#` break parsing. `openssl rand -hex` is safe.
- **Signature audit log** lives in MongoDB — back up regularly.
- **Signed PDFs** land in `volumes/api-files/` — legally binding artefacts, treat backup with care.
- **Default access `acc-public` + `sec-3`** — signers receive a signing URL and need to reach it from outside. Admin UI sits on the same host — gate with a second router if agents are internal-only.

## Mail configuration

OpenSign supports two mail backends — pick one:

- **Mailgun** (`MAILGUN_API_KEY` + `MAILGUN_DOMAIN`) — easiest for production
- **SMTP** (set `SMTP_ENABLE=true` + host/port/user/pass) — for self-hosted mailservers

Without a working mail config, signature request emails do not go out and the flow is broken.

## Known Issues

- **Live-tested: no.**
- **`APP_TAG=latest`** — pin to a version for production.
- **`MASTER_KEY` in `.env`** — current blueprint reads it from env; Parse Server has no `_FILE` convention. Move to Docker Secret + entrypoint wrapper for higher security.
- **MongoDB 6 is the last version with the community SSPL license that Parse Server fully supports** — do not jump to 7+ until OpenSign tests it.
- **Signing certificate** — OpenSign can generate self-signed signing certs, but for legally enforceable signatures in the EU (eIDAS Advanced), you need a qualified trust-service-provider certificate. The platform supports uploading a qualified cert; the basic setup here uses self-signed.
- **OCR / keyword detection** for auto-placement of signature fields requires the `OPENSIGN_OCR` side-car — not included here.

## Integration patterns

- **Zammad → OpenSign**: customer service request triggers an NDA or contract signing. Zammad webhook → n8n → OpenSign REST API (`POST /api/contract`).
- **Kimai → OpenSign**: end-of-project sign-off on hours delivered. Manual export from Kimai + upload to OpenSign template.
