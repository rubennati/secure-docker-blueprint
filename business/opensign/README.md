# OpenSign

**Status: ✅ Ready — main · 2026-05-11**

Self-hosted electronic signature platform — DocuSign / Adobe Sign alternative. Upload PDF/DOCX, define signing roles, send to signers, audit trail, certificates. GDPR-friendly since everything stays on your infrastructure.

## Architecture

Three-service stack with Traefik path-based split (same pattern as OpnForm):

| Service | Image | Purpose |
|---------|-------|---------|
| `ui` | `opensign/opensign:main` | React frontend |
| `api` | `opensign/opensignserver:main` | Parse Server backend + PDF signing engine |
| `db` | `mongo:6` | Documents, templates, users, audit log |

Traefik routes `PathPrefix(/app)` to the API (priority 100), everything else to the UI (priority 1). No `/api` prefix — Traefik routes directly to Parse's mount path without stripping (unlike Caddy in the upstream default).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, APP_NAME, TZ

mkdir -p .secrets volumes/mongodb volumes/api-files

# DSN-safe Mongo root password (alphanumeric only — DSN-safe)
openssl rand -hex 32 > .secrets/db_root_pwd.txt
sed -i "s|^DB_ROOT_PWD_INLINE=.*|DB_ROOT_PWD_INLINE=$(cat .secrets/db_root_pwd.txt)|" .env

# Master key
sed -i "s|^MASTER_KEY=.*|MASTER_KEY=$(openssl rand -hex 32)|" .env

# Self-signed document signing certificate
# Use passphrase from PASS_PHRASE (set it first in .env)
PASS="$(openssl rand -hex 24)"
sed -i "s|^PASS_PHRASE=.*|PASS_PHRASE=${PASS}|" .env
openssl genrsa -des3 -passout pass:"${PASS}" -out /tmp/opensign.key 2048
openssl req -key /tmp/opensign.key -passin pass:"${PASS}" -new -x509 -days 365 \
  -out /tmp/opensign.crt -subj "/CN=OpenSign"
openssl pkcs12 -inkey /tmp/opensign.key -passin pass:"${PASS}" \
  -in /tmp/opensign.crt -export -out /tmp/opensign.pfx -passout pass:"${PASS}"
PFX_B64="$(openssl base64 -in /tmp/opensign.pfx | tr -d '\n')"
sed -i "s|^PFX_BASE64=.*|PFX_BASE64=${PFX_B64}|" .env
rm /tmp/opensign.key /tmp/opensign.crt /tmp/opensign.pfx

# Configure mail in .env (Mailgun OR SMTP)

docker compose up -d
docker compose logs api --follow
# Watch for: "opensign-server running on port 8080."
# Then: "SUCCESS  Successfully run migrations."

# https://<APP_TRAEFIK_HOST>
# First account to register becomes admin (redirects to /addadmin)
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

- **No semver tags on Docker Hub** — OpenSign only publishes `main`, `staging`, `docker_beta`. There are no `vX.Y.Z` release tags; upstream does not version its Docker images.
- **`APP_TAG=main` is a floating tag** — rebuild with `docker compose pull` to get updates. Cannot pin to a specific release.
- **`APP_ID` is fixed as `opensign`** — it is deprecated upstream and hardcoded in the compose. Do not generate a random value; the React client and Parse Server must agree on this literal string.
- **`MONGODB_URI` has no `_FILE` support** — password embedded inline in DSN. Use alphanumeric-only password to avoid DSN-breaking characters (`@`, `:`, `/`, `?`, `#`).
- **`MASTER_KEY` in `.env`** — Parse Server has no `_FILE` convention. Move to Docker Secret + entrypoint wrapper for higher security.
- **`SERVER_URL` is the public Parse URL** — set to `https://<domain>/app`. Parse uses this to generate links in signature request emails and webhook payloads. Upstream uses Caddy which strips a `/api` prefix; our Traefik setup routes directly to `/app`, so no prefix needed.
- **Self-signed signing cert is not Adobe-trusted** — documents signed with a self-generated cert show no green tick in Adobe Acrobat. For eIDAS Advanced signatures, purchase a qualified p12 from an AATL-approved CA and set `PFX_BASE64` + `PASS_PHRASE`.
- **MongoDB 6 is the last version with full Parse Server support** — do not jump to 7+ until OpenSign tests it.
- **OCR / keyword detection** for auto-placement of signature fields requires the `OPENSIGN_OCR` side-car — not included here.

## Integration patterns

- **Zammad → OpenSign**: customer service request triggers an NDA or contract signing. Zammad webhook → n8n → OpenSign REST API (`POST /api/contract`).
- **Kimai → OpenSign**: end-of-project sign-off on hours delivered. Manual export from Kimai + upload to OpenSign template.
