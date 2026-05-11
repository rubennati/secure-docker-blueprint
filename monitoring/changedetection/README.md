# changedetection.io

**Status: ✅ Ready — v0.55.3 · 2026-05-11**

Self-hosted website content change detection. Different axis from uptime monitoring — answers "what changed on this page" instead of "is it up". Good for: restock alerts, price drops, ToS/policy diff tracking, external-dependency defacement detection.

## Architecture

Single-container deployment (HTTP fetcher only):

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghcr.io/dgtlmoon/changedetection.io:0.55.3` | Watcher + diff engine + notification dispatcher |

For JavaScript-heavy sites (SPAs), uncomment the optional `browser` service in `docker-compose.yml` — it runs a Playwright Chrome instance.

## Setup

```bash
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ

mkdir -p volumes/data
docker compose up -d
docker compose logs app --follow
# Watch for: "Running on http://0.0.0.0:5000"

# Open UI, set a password under Settings → General
# https://<APP_TRAEFIK_HOST>
```

## Security Model

- **No first-user wizard** — the app is open by default. Set a password in Settings → General immediately, or put Authentik forward-auth in front.
- **Default access `acc-tailscale` + `sec-3`** — watched URLs + selectors + scraping credentials live in the UI. VPN-only default.
- **Data volume** (`volumes/data/`) holds every snapshot of every watched page. Can grow large — set retention per-watch in Settings.
- **`no-new-privileges:true`** on the container.

## Notification integrations

Built-in support (via [Apprise](https://github.com/caronc/apprise)):
- Discord, Slack, Mattermost, Telegram, ntfy
- Email (SMTP)
- Generic webhook (POST JSON) — use this to route via n8n for richer logic

Configure globally (Settings → Notifications) or per-watch.

## Common patterns

**Restock alert**:
```
URL:       https://shop.example.com/product/xy
Trigger:   CSS/JSON path `.in-stock-badge` shows "Verfügbar" or similar
Webhook:   https://n8n.example.com/webhook/restock
```

**API endpoint drift**:
```
URL:       https://api.partner.com/v1/status
Fetch:     Include request headers / auth
Trigger:   On any body change
```

**Impressum / ToS watcher**:
```
URL:       https://competitor.example/impressum
Schedule:  Daily
Notification: Slack #compliance
```

## Known Issues

- **`WARNING: This is a development server`** in logs — changedetection.io uses Flask's built-in dev server as their official deployment method (no uWSGI/Gunicorn in front). Fine in practice: Traefik absorbs all external traffic; Flask never sees direct internet connections. Upstream decision, not actionable.
- **Socket.IO WebSocket returns 400 behind Traefik** — `https://<domain> is not an accepted origin` in logs. `BASE_URL` is set correctly but Socket.IO CORS doesn't pick it up when running behind a reverse proxy. Cosmetic only: the app works fully, watches run, diffs are stored and notifications fire. Only live-push updates in the browser UI are affected (badges don't update in real-time — refresh manually). Upstream issue; no workaround without patching the CORS init.
- **`APP_TAG=0.55.3` is pinned** — `latest` is not reproducible.
- **No auth on first boot** — set a password immediately or front with Authentik.
- **Diff storage grows fast** with high-churn pages — set "Max snapshots" per watch.
- **JS-heavy sites need the optional browser service** — without it, you get the raw HTML which may be a near-empty SPA shell.
- **Respect rate limits + ToS** — watching sites at high frequency can get you blocked or violate their ToS. Default interval is hours, not seconds, for a reason.
