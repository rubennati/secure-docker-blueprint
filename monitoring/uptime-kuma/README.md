# Uptime Kuma

**Status: ✅ Ready — v1.23.17 · 2026-05-11**

UI-driven uptime monitoring. Single container, SQLite backend, rich probe types (HTTP, TCP, DNS, docker, steam, …), public status pages, 90+ notification integrations.

Modern successor to Statping — more active (weekly releases), better UI, wider probe support.

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `louislam/uptime-kuma:1.23.17` | Web UI + probe scheduler + SQLite store |

Data lives in `./volumes/data/` (SQLite DB, monitor state, uploaded icons).

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ
mkdir -p volumes/data
docker compose up -d
docker compose logs app --follow
# Watch for: "Listening on 3001"

# Open UI and create the owner account on first visit
# https://<APP_TRAEFIK_HOST>
```

## Verify

```bash
curl -fsSI https://<APP_TRAEFIK_HOST>/        # 200 OK
```

## Security Model

- **First-user-wins owner** — open the UI yourself immediately after `docker compose up -d`.
- **Default access `acc-tailscale` + `sec-3`** — the admin UI exposes all your probe URLs, response bodies, and notification webhook URLs. VPN-only is the right default.
- **Public status pages** — Kuma serves these at `/status/<slug>`. If you want them externally reachable while keeping the admin UI private, add a second Traefik router:
  ```yaml
  - "traefik.http.routers.kuma-public.rule=Host(`status.example.com`)"
  - "traefik.http.routers.kuma-public.service=uptime-kuma"
  # + public-friendly middleware chain
  ```
- **`no-new-privileges:true`**.

## Known Issues

- **`APP_TAG=1.23.17` is pinned.** v2 is beta — not recommended in production yet.
- **Data volume ownership** — Kuma runs as UID 1000 inside the container. If you pre-create `volumes/data` as root, `chown -R 1000:1000` it.
- **No built-in backup** — stop the app, `cp -r volumes/data/` to backup target, start again. Do NOT `pg_dump`-style-dump a running SQLite DB.
- **Heavy monitor counts (>500)** can cause SQLite contention. Switch to MariaDB if that becomes a problem (env: `UPTIME_KUMA_DB_TYPE=mariadb`).
