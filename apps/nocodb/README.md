# NocoDB

Open-source Airtable alternative. Turns any SQL database into a spreadsheet-like UI with views, forms, and a REST + GraphQL API. Commonly paired with **n8n** for low-code automation.

## Architecture

Single-container deployment with NocoDB's built-in SQLite:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `nocodb/nocodb:latest` | Web UI + REST/GraphQL API |

Data lives in `./volumes/data/` (SQLite DB, attachments, user uploads).

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate JWT secret
mkdir -p .secrets
openssl rand -hex 64 > .secrets/nc_jwt_secret.txt
# This encrypts every API token NocoDB issues. Back it up off-host.

# 3. Create data volume
mkdir -p volumes/data

# 4. Start
docker compose up -d

# 5. Wait for first-boot init (~30 seconds)
docker compose logs app --follow
# Watch for: "Visit: http://localhost:8080/dashboard"

# 6. Open UI and create the first super-admin
# https://<APP_TRAEFIK_HOST>
# The first account to sign up becomes super-admin.
```

## Verify

```bash
docker compose ps                                          # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/api/v1/health        # 200 OK
```

## Security Model

- **First-user-wins super-admin** — open the UI and sign up immediately after `docker compose up`.
- **`NC_INVITE_ONLY_SIGNUP=true` by default** — after the first account is created, further signups require an invitation from an admin.
- **`NC_AUTH_JWT_SECRET_FILE`** — Docker Secret. Encrypts every API token NocoDB issues. Losing the key makes all stored API tokens invalid. Back up `.secrets/nc_jwt_secret.txt` off-host.
- **`NC_DISABLE_TELE=true`** — disables usage telemetry.
- **`no-new-privileges:true`** on the container.
- **Default access `acc-tailscale` + `sec-3`** — NocoDB holds structured operational data and often API credentials in table cells. VPN-only is a safer default than public. Switch to `acc-public + sec-2` only if you want external share links and are OK with that exposure.

## Using NocoDB with n8n

Typical automation pattern:

1. In NocoDB, open a table → **Details → API Tokens** → create a token.
2. In n8n, add an HTTP Request node (or the NocoDB node if available).
3. Base URL is the internal Docker hostname if n8n shares a network with NocoDB, or the Traefik hostname otherwise.
4. Authentication header: `xc-token: <token>`.
5. Store the token as an n8n credential so it encrypts into n8n's credential store.

For n8n and NocoDB to reach each other on an internal network, either:
- Run both in the same `compose.yml`, or
- Attach n8n's app service to NocoDB's `proxy-public` network and address it as `http://nocodb-app:8080`.

## Known Issues

- **Live-tested: no.** Expect minor surprises on first boot.
- **`APP_TAG=latest` is not reproducible** — pin to a specific release for stable deployments. NocoDB has frequent breaking changes on minor version bumps.
- **SQLite locks under heavy writes** — for high-volume automation workloads, switch to Postgres. See `UPSTREAM.md`.
- **Attachments in `volumes/data/`** — back up together with the SQLite DB. Losing `volumes/data/` loses all records *and* file attachments.
- **JWT secret rotation invalidates every issued API token** — any downstream automation (n8n, scripts) will break and needs new tokens.

## Details

- [UPSTREAM.md](UPSTREAM.md)
