# Homepage (gethomepage)

> **Status: Draft — not yet live-tested.** First-pass import from inbox material.

Highly-configurable self-hosted dashboard. File-based YAML configuration — one file per concern (services, bookmarks, widgets, settings). Rich set of service integrations and info widgets.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/gethomepage/homepage:v0.10.9` | Next.js dashboard reading YAML configs |

Config lives in `./config/`. No database.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Bootstrap config from the examples
cd config
for f in *.example.yaml; do cp "$f" "${f/.example/}"; done
cd ..

# 3. Start
docker compose up -d

# 4. Open UI
# https://<APP_TRAEFIK_HOST>
```

Further configuration = edit files in `config/`, Homepage hot-reloads on change.

## Verify

```bash
docker compose ps                              # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **`HOMEPAGE_ALLOWED_HOSTS` derived from `APP_TRAEFIK_HOST`** — inbox source had a hardcoded real-IP value (192.168.x.x:port). Now consistent with the blueprint TLS hostname.
- **Default access `acc-tailscale`** — personal dashboard, VPN-only.
- **Default security `sec-3`**.
- **Docker socket integration disabled by default** — see below.
- **`no-new-privileges:true`**.

## Docker integration (optional)

Homepage can discover services via Docker labels (set on other containers) or show live container status. Two options:

1. **Direct `/var/run/docker.sock` mount** (uncomment in `docker-compose.yml`) — quick, gives Homepage **read-write Docker access**. Risk: any code-execution bug in Homepage = full container takeover.

2. **Socket-proxy** (recommended) — route through `tecnativa/docker-socket-proxy` with only the needed API endpoints (`CONTAINERS=1`, `NETWORKS=1`, `INFO=1`). See `core/traefik/` for the pattern. Point Homepage's docker config at `tcp://docker-socket-proxy:2375`.

Leave disabled if you manually maintain `services.yaml`.

## Known Issues

- **Live-tested: no.**
- **`HOMEPAGE_ALLOWED_HOSTS` must include the exact Host header** — if you proxy through Traefik with a different external hostname, update accordingly.

## Details

- [UPSTREAM.md](UPSTREAM.md)
- [config/README.md](config/README.md) — explanation of the YAML files
