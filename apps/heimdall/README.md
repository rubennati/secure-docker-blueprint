# Heimdall

> **Status: ✅ Ready** — v2.6.3 · 2026-05-02

Self-hosted application dashboard — a pretty launcher for your homelab apps, with optional widgets that show status / stats per service.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `lscr.io/linuxserver/heimdall:2.6.3` | LinuxServer.io build of Heimdall on Apache + PHP |

Data (SQLite DB, uploaded icons, config) lives in `./config/`, managed by Heimdall's web UI.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID (match host owner of ./config/)

# 2. Prepare config directory with correct ownership
mkdir -p config
sudo chown -R 1000:1000 config

# 3. Start
docker compose up -d

# 4. First boot takes ~30s while the image builds the SQLite DB
docker compose logs app --follow

# 5. Open UI — no login initially
# https://<APP_TRAEFIK_HOST>
```

All further configuration (items, backgrounds, users) happens in the Web UI.

## Verify

```bash
docker compose ps                              # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **LinuxServer.io image with s6-overlay** — container starts as root to set up `/run`, drops to `PUID:PGID` internally. Do **not** set `user:` in compose (breaks s6-overlay).
- **`ALLOW_INTERNAL_REQUESTS=false`** by default — Heimdall's status-check widgets cannot probe RFC1918 addresses. Flip to `true` if you want widgets to monitor internal app status (e.g. Uptime status of `wordpress-app:80`).
- **Default access `acc-tailscale`** — VPN-only.
- **Optional authentication** — Heimdall supports user accounts in its UI. Not enabled by default; add via the UI if you share the instance.

## Known Issues

- **First user setup is in the UI, not via env var** — new users must be added by clicking "Users" in the sidebar after logging in. Initial user is a "public" admin (everyone sees the same dashboard) until a proper user is created.
- **Icon upload may need ownership fixes** — if you see permission errors on icon upload, re-run `chown -R 1000:1000 ./config` to match `PUID/PGID`.

## Details

- [UPSTREAM.md](UPSTREAM.md)
