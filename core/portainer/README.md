# Portainer CE

Docker management UI — the community edition of Portainer. Connects to the Docker daemon through a filtered socket proxy, not a direct socket mount.

Good fit for: visual inspection of containers, logs, volumes, networks; quick restart/exec/stop operations; image management. Less suited as the primary declarative deployment tool — for Git-driven stacks see [Dockhand](../dockhand/) instead.

## Architecture

Two services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `portainer/portainer-ce` | Portainer UI and API |
| `socket-proxy` | `lscr.io/linuxserver/socket-proxy` | Filtered Docker API gateway |

Portainer reaches Docker through `tcp://socket-proxy:2375` (configured via `--host` in the compose `command`). The socket proxy enforces which Docker API endpoints are allowed — Portainer never sees `/var/run/docker.sock`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Start (no secrets needed — Portainer prompts on first login)
docker compose up -d

# 3. Open the web UI within 5 minutes of first start
# https://<APP_TRAEFIK_HOST>
# Portainer locks out admin creation after 5 min of idleness — restart if missed
```

Default access policy is `acc-tailscale` + `sec-4` + `tls-modern` (admin tool, VPN-only, hardened).

## Verify

```bash
docker compose ps                      # Both services should be healthy
docker compose logs socket-proxy       # Watch API calls the proxy handles
```

In the UI: after first-run admin setup, confirm you can list containers, view logs, pull images.

## Security Model

The socket proxy is the main hardening. Its environment variables in `docker-compose.yml` define what Portainer can do:

- `CONTAINERS`, `SERVICES`, `NETWORKS`, `VOLUMES`, `IMAGES`, `SYSTEM` — read access
- `EXEC`, `POST`, `DELETE` — modifications
- `ALLOW_START`, `ALLOW_STOP`, `ALLOW_RESTARTS` — container lifecycle

This is a **full-access** set suitable for a trusted admin UI. If Portainer only needs read-only operation (e.g. monitoring), reduce `POST`, `DELETE`, `EXEC` to `"0"`.

## First-Login Admin Setup

Portainer enforces a 5-minute window for initial admin creation after first start. If missed, the instance becomes unreachable and must be restarted:

```bash
docker compose restart app
```

After successful admin creation, set a strong password and enable 2FA in the user settings.

## Known Issues

None currently documented.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
