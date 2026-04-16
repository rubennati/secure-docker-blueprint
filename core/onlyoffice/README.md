# OnlyOffice Document Server

Browser-based office document editor. Runs as a shared backend that other apps (Seafile, Nextcloud, any WOPI-capable client) call into for live editing of `.docx`, `.xlsx`, `.pptx`, and similar formats.

One OnlyOffice instance serves many consumers. Each consumer authenticates with the same JWT secret.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `onlyoffice/documentserver:8.3` | Node.js server + rendering, serves the editor at `/web-apps/apps/api/documents/api.js` |

There is no DB container in this setup — the image bundles its own PostgreSQL + Redis + RabbitMQ for internal state. This is the upstream-recommended "single container" deployment.

### JWT handshake

Every editing request carries a signed JWT. Both sides — OnlyOffice and the consuming app — must hold the same secret:

```
┌────────────┐      ┌──────────────┐      ┌──────────────┐
│ Seafile /  │─────▶│ Traefik      │─────▶│ OnlyOffice   │
│ Nextcloud  │ JWT  │ (TLS + CSP)  │ JWT  │ (verify)     │
└────────────┘      └──────────────┘      └──────────────┘
  JWT_SECRET         frame-ancestors        JWT_SECRET
  (shared)                                   (shared)
```

Mismatched secrets → documents open read-only with "Token is invalid" in the browser console.

### Why iframe embedding needs a custom Traefik chain

OnlyOffice has to be embedded in an `<iframe>` inside Seafile / Nextcloud. Every `sec-*` middleware chain in this repo sets `X-Frame-Options: DENY`, which browsers honour strictly and block the iframe.

The `docker-compose.yml` therefore defines two dedicated middlewares:

- `${COMPOSE_PROJECT_NAME}-proto` — sets `X-Forwarded-Proto: https` and `X-Forwarded-Host` so OnlyOffice generates HTTPS URLs (otherwise Mixed Content errors in the editor)
- `${COMPOSE_PROJECT_NAME}-headers` — HSTS + nosniff + `Content-Security-Policy: frame-ancestors <allowed-origins>` instead of a blanket frame-deny

The allowed origins come from `ONLYOFFICE_ALLOWED_ORIGINS` in `.env`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, ONLYOFFICE_ALLOWED_ORIGINS, TZ

# 2. Generate the JWT secret
mkdir -p .secrets
openssl rand -base64 30 | tr -d '\n' > .secrets/jwt_secret.txt

# 3. Start
docker compose up -d

# 4. First boot takes ~90s (PostgreSQL init + document server warm-up)
docker compose logs app --follow

# 5. Verify
curl -fsSI https://<APP_TRAEFIK_HOST>/healthcheck   # 200 OK
```

### Connecting from a consuming app

For each app that will use OnlyOffice, copy the JWT secret into its own secrets directory:

```bash
cp .secrets/jwt_secret.txt ../../apps/seafile/.secrets/onlyoffice_jwt_secret.txt
cp .secrets/jwt_secret.txt ../../apps/nextcloud/.secrets/onlyoffice_jwt_secret.txt
```

Then configure that app to point at:

```
https://<APP_TRAEFIK_HOST>/web-apps/apps/api/documents/api.js
```

Exact configuration UI differs per app — see the consuming app's README.

## Verify

```bash
docker compose ps                          # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/healthcheck
curl -fsSI https://<APP_TRAEFIK_HOST>/web-apps/apps/api/documents/api.js
```

Open an office doc from a connected app and confirm the editor loads in an iframe without `X-Frame-Options` errors in the browser console.

## Security Model

- Only the JWT secret is Docker Secret; OnlyOffice reads it via the entrypoint wrapper (`config/entrypoint.sh`) because the upstream image doesn't support `_FILE` env vars.
- The custom `-headers` middleware keeps HSTS, nosniff, and `referrer-policy`-equivalent protections while permitting controlled iframe embedding.
- `ONLYOFFICE_ALLOWED_ORIGINS` is a CSP allowlist. Any domain not listed here is rejected by the browser, even if it holds a valid JWT.
- `no-new-privileges:true` on the container.

## Known Issues

- **Image size is large (~1.5 GB)** — this is upstream; the document server bundles LibreOffice, Node.js, Nginx, PostgreSQL, RabbitMQ, and Redis. No slim variant is available.
- **Log volume grows quickly.** `./volumes/logs` is mounted so logs persist; rotate or truncate it periodically if disk usage matters.
- **`APP_TRAEFIK_SECURITY` is not used.** Setting it in `.env` has no effect — the compose file wires the custom middleware chain unconditionally. Left in the `.env.example` with a comment so nobody is surprised.
- **JWT secret rotation is not automatic.** Rotating means updating the secret file in OnlyOffice _and_ every consuming app, then restarting each.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
