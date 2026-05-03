# Dashy

Self-hosted homelab dashboard. Config-driven via a single YAML file; the UI re-builds when the config changes.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `lissy93/dashy:4.0.4` | Vue-based SPA + embedded build server |

No database. Config lives in `config/conf.yml`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Create your dashboard config
mkdir -p config
cp config/conf.example.yml config/conf.yml
# Edit config/conf.yml — add your sections, items, bookmarks

# 3. Start
docker compose up -d
```

## Verify

```bash
docker compose ps                              # healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- `no-new-privileges:true`
- Default access `acc-tailscale` — personal dashboard, VPN-only
- Default security `sec-3`
- No data persistence beyond config file — container can be recreated freely

## Known Issues

- **Config changes** require a container restart to take effect (`docker compose restart app`).
- **In-app config editor unavailable** — `conf.yml` is mounted read-only (`:ro`). All changes go through the file directly. This is intentional: file-based management is cleaner and prevents accidental in-UI overwrites.

## Details

- [UPSTREAM.md](UPSTREAM.md)
- [config/conf.example.yml](config/conf.example.yml) — starter config from the inbox source
