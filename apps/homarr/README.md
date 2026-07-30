# Homarr

Modern self-hosted dashboard focused on integrations — widget-based UI that can show live status of media servers, torrent clients, reverse proxies, Proxmox nodes, weather, calendars, and dozens more.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/homarr-labs/homarr:v1.60.0` | Next.js dashboard with built-in SQLite + internal Redis |

Data lives in `./volumes/appdata/`. Integrations encrypt their credentials using `SECRET_ENCRYPTION_KEY`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Generate the encryption key (64 hex chars = 32 bytes)
openssl rand -hex 32
# Put the output into .env as HOMARR_SECRET_ENCRYPTION_KEY

# 3. Create data directory
mkdir -p volumes/appdata

# 4. Start
docker compose up -d

# 5. Open UI — first-run setup wizard will guide you
# https://<APP_TRAEFIK_HOST>
```

## Verify

```bash
docker compose ps                              # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **`SECRET_ENCRYPTION_KEY` encrypts stored integration credentials** (API tokens for torrent clients, media servers, etc.). Losing or rotating the key invalidates all stored integrations — they have to be re-entered in the UI.
- **Default access `acc-tailscale`** — personal dashboard.
- **Default security `sec-3`**.
- **Docker integration is disabled by default** — see below.
- **`no-new-privileges:true`**.

## Backup

| | |
|---|---|
| **Database** | SQLite inside `./volumes/appdata` — no database server, no dump hook |
| **State** | `./volumes/appdata` — boards, integrations, users, encrypted credentials |
| **Reproducible** | nothing |
| **Quiescing** | **Recommended.** Stop the container or snapshot the filesystem rather than copying a live SQLite file. |

No database hook. This stack is `source_directories` only, quiesced.

**The encryption key is not in this directory.** Homarr encrypts stored
integration credentials with a key supplied through the environment; restoring
`appdata` against a different key leaves the boards intact and every integration
unable to authenticate. Back the key up wherever `.env` is kept, and treat the two
as one restore unit.

## Docker integration (optional)

Homarr can show live container status, start/stop buttons, etc. if it can reach the Docker socket. The direct socket mount gives the container full control of Docker — **risky**.

Two options if you want this feature:

1. **Direct socket mount** (quick, risky): uncomment the `docker.sock` line in `docker-compose.yml`. Understand: any code-execution vulnerability in Homarr = full Docker takeover.

2. **Socket proxy** (recommended): route Homarr through a `tecnativa/docker-socket-proxy` with only `CONTAINERS=1`, `NETWORKS=1`, `INFO=1` enabled. See `core/traefik/docker-compose.yml` for the pattern used elsewhere in the blueprint. Requires adapting Homarr's config to talk to the proxy endpoint (e.g. `tcp://docker-socket-proxy:2375`).

Leave disabled if you don't need live container status.

## Known Issues

- **`SECRET_ENCRYPTION_KEY` leak in inbox source** — the upstream example and many tutorials include a specific hex string as example. Any .env.example containing it would be a backdoor. Our `.env.example` uses `__REPLACE_ME__` — regenerate in Setup step 2.
- **`SECRET_ENCRYPTION_KEY` not `_FILE`-capable** — upstream reads it from env only. Stays in `.env` (gitignored).

## Details

- [UPSTREAM.md](UPSTREAM.md)
