# IT-Tools

A self-hosted collection of handy IT and developer tools: JSON/YAML formatters, hash and UUID generators, regex tester, base64/URL encoders, QR code generator, timezone converters, and dozens more. Pure static SPA — no backend, no database, no accounts.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/corentinth/it-tools` | Static SPA served by Nginx on port 80 |

Completely stateless. Can be torn down and recreated without data loss.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

# 2. Start
docker compose up -d

# 3. Open in browser
# https://<APP_TRAEFIK_HOST>
```

No secrets. No persistent state. No initial configuration.

## Verify

```bash
docker compose ps                               # app healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/          # 200 OK
```

The tool list loads immediately — no login, no setup page.

## Security Model

- **Read-only root filesystem** with minimal `tmpfs` mounts for Nginx's runtime dirs (`/tmp`, `/var/cache/nginx`, `/var/run`). Container can't write anywhere else.
- **`no-new-privileges:true`** — prevents capability escalation.
- **Default access `acc-tailscale`** — personal toolbox, VPN-only by default. Flip to `acc-public` if you want to share the tools publicly (the app is a benign static SPA, no confidentiality concerns; but personal use doesn't need public exposure).
- **No backend** — no API endpoints, no data submission anywhere. All computation happens in the user's browser.

## Known Issues

- **Live-tested: no.** Expect minor surprises on first deployment.
- **Image tag** is a timestamped hash from upstream (`2025.7.18-a0bc346` style). Upstream doesn't publish semver tags, so bumping means picking a newer commit-tagged release. Check [upstream releases](https://github.com/CorentinTh/it-tools/releases) for the latest.
- **Read-only root filesystem** breaks on some old Nginx variants — if the container refuses to start with permission errors, temporarily drop `read_only: true` to diagnose.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
