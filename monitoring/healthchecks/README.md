# Healthchecks

**Status: ✅ Ready — v3.13 · 2026-05-11**

Self-hosted cron / scheduled-task monitoring. Each monitored job gets a unique URL — the job pings that URL on schedule, and Healthchecks alerts you (email, webhook, Slack, Discord, ntfy, etc.) when an expected ping doesn't arrive.

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `healthchecks/healthchecks:v3.13` | Django app with built-in scheduler, serves UI + ping endpoints |

Data stored in SQLite (`./volumes/data/hc.sqlite`). Suitable for personal use and small teams. Can be switched to PostgreSQL for higher loads — not needed for most self-hosted cases.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, HC_SITE_NAME, HC_EMAIL_FROM,
#       HC_SMTP_HOST, HC_SMTP_USER, HC_SMTP_PASSWORD

# 2. Generate Django SECRET_KEY and put it into .env as HC_SECRET_KEY
openssl rand -base64 60 | tr -d '\n='

# 3. Create data directory — app runs as uid 999, must own the volume
mkdir -p volumes/data
chown -R 999:999 volumes/data

# 4. Start
docker compose up -d
docker compose logs app --follow
# Watch for: "spawned uWSGI worker"

# 5. Create the first admin user (one-time)
docker compose exec app /opt/healthchecks/manage.py createsuperuser

# 6. Open UI and log in
# https://<APP_TRAEFIK_HOST>
```

## Verify

```bash
docker compose ps                                   # app healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/              # 200 OK
curl -fsSI https://<APP_TRAEFIK_HOST>/projects/     # 302 redirect to login
```

Create a test check in the UI:

- Project → Add Check → give it a name like "test"
- Copy the generated ping URL
- From another terminal: `curl <ping-url>`
- Back in UI → Check should now show "up" with timestamp

## Security Model

- **Access policy `acc-tailscale` by default** — assumes monitored jobs live on the same Tailscale network. Switch to `acc-public` if you monitor cron jobs running on public servers or third-party hosts.
- **`no-new-privileges:true`** — baseline hardening.
- **Registration closed (`HC_REGISTRATION_OPEN=False`)** by default — only the superuser you create can log in and invite others. Flip to `True` if you want self-service signup (only for trusted networks).
- **SECRET_KEY in `.env`** (gitignored) — upstream does not support `_FILE` env vars for this. Rotating the secret invalidates all sessions (acceptable).
- **Ping URLs are public-information once shared** — anyone with the URL can ping a check. Each URL is a UUID and unguessable but does not need authentication; if you need stricter control, use signed ping URLs (Healthchecks v2+ feature, in UI per-check).

## Known Issues

- **`volumes/data` must be owned by uid 999** — the app runs as `hc` (uid 999). If Docker creates the directory as root, SQLite migration fails with `unable to open database file`. Fix: `chown -R 999:999 volumes/data` before first start.
- **Monitored-job reachability** — if your cron jobs run on servers that can't reach this instance (e.g. behind NAT without Tailscale), pings will silently fail. The only symptom is "check is down" in the UI for a job that is actually running fine. Check job-side logs first when diagnosing.
- **Email alerts require working SMTP.** Without SMTP, the only notification channels are webhooks, Slack, Discord, ntfy, and Pushover — all of which need to be configured per-check in the UI.
- **SECRET_KEY in `.env`** rather than `.secrets/` is a pragmatic blueprint deviation; see ROADMAP "Secret & Password Generation Standard" for the broader policy discussion.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
