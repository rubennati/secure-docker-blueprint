# Healthchecks

Self-hosted cron / scheduled-task monitoring. Each monitored job gets a unique URL — the job pings that URL on schedule, and Healthchecks alerts you (email, webhook, Slack, Discord, ntfy, etc.) when an expected ping doesn't arrive.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

Single service:

| Service | Image | Purpose |
|---------|-------|---------|
| `healthchecks-app` | `healthchecks/healthchecks:v5.0.3` | Django app with built-in scheduler, serves UI + ping endpoints |

Data stored in SQLite (`./volumes/data/hc.sqlite`). Suitable for personal use and small teams. Can be switched to PostgreSQL for higher loads — not needed for most self-hosted cases.

## Try it locally

Runs on `http://localhost:8000` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'HC_SECRET_KEY=%s\n' "$(openssl rand -base64 60 | tr -d '\n=')" >> .env.local

mkdir -p volumes/local/data
sudo chown -R 999:999 volumes/local/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
docker compose -f docker-compose.local.yml --env-file .env.local \
  exec app python /opt/healthchecks/manage.py createsuperuser
# http://localhost:8000
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

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
sudo chown -R 999:999 volumes/data

# 4. Start
docker compose up -d
docker compose logs healthchecks-app --follow
# Watch for: "spawned uWSGI worker"

# 5. Create the first admin user (one-time). Since v4.4 the command takes its
#    arguments explicitly and has no --noinput; a passphrase of a few words is
#    what gets typed into a browser later.
docker compose exec healthchecks-app /opt/healthchecks/manage.py createsuperuser --email admin@example.com --password '<passphrase>'

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

## Pings from the same host

Jobs on the host that runs this stack — `core/host-watchdog`, the Traefik watchdog in
`core/traefik/ops/scripts`, `backup/borgmatic` — ping the loopback port instead of the
public name:

```text
http://127.0.0.1:8001/ping/<uuid>        # HC_LOCAL_PORT, 8001 by default
```

Through Traefik such a ping arrives as the gateway address of the edge network, not as
the host's address, so a closed access policy refuses it — and that gateway must not go
into `TRUSTED_RANGES`, since every container on the network would pass with it. The
loopback port avoids the proxy: it is published on `127.0.0.1` only, so nothing outside
the host reaches it, and the route keeps its closed policy. No public `/ping/` route is
needed for these jobs. The UI shows ping URLs under `SITE_ROOT`; replace
`https://<APP_TRAEFIK_HOST>` with `http://127.0.0.1:8001` in the job's configuration, the
UUID stays the same.

Verified on the lab host (VM) on 2026-11-09 (v5.0.3), with the route on
`access-trusted`: the Traefik watchdog and the Docker daemon watchdog, each started from
its shipped systemd unit, and borgmatic 2.2.0 (`start` and `finish`) all reached their
checks through `127.0.0.1:8001`; the same ping through the route from the host answered
`403`, and the port did not answer from another machine on the LAN.

A green check proves the ping path, not the alarm. Attach a notification
channel, stop pinging, and let the grace time expire — the down notification
has to arrive where it is supposed to. Done on 2026-09-08 (v4.4): ntfy to a
phone and email to the mail sink, down and up, within a second each.

## Security Model

- **Switching to `access-public` opens the admin UI, not just the ping endpoints.** One service serves both, so an access policy set for the pings applies to the login page and the check list as well. Keep `access-vpn` and give the ping path its own router instead:

  ```yaml
  - "traefik.http.routers.hc-ping.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/ping/`)"
  - "traefik.http.routers.hc-ping.priority=100"
  - "traefik.http.routers.hc-ping.middlewares=${APP_TRAEFIK_HEADERS}@file,access-public@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}"
  - "traefik.http.routers.hc-ping.service=${COMPOSE_PROJECT_NAME}"
  ```

  The catch-all router keeps `access-vpn`, and the path-scoped one runs at the higher priority so it decides requests to `/ping/`. `monitoring/uptime-kuma` documents the mirror image of this for its public status pages.

- **Access policy `access-vpn` by default** — assumes monitored jobs live on the same Tailscale network. Switch to `access-public` if you monitor cron jobs running on public servers or third-party hosts.
- **`no-new-privileges:true`** — baseline hardening.
- **Registration closed (`HC_REGISTRATION_OPEN=False`)** by default — only the superuser you create can log in and invite others. Flip to `True` if you want self-service signup (only for trusted networks).
- **SECRET_KEY in `.env`** (gitignored) — upstream does not support `_FILE` env vars for this. Rotating the secret invalidates all sessions (acceptable).
- **The loopback port serves the whole application, not only `/ping/`.** Anyone with a shell on the host can open the login page on `127.0.0.1:8001`; the login still applies. Nothing off the host reaches it.
- **Ping URLs are public-information once shared** — anyone with the URL can ping a check. Each URL is a UUID and unguessable but does not need authentication; if you need stricter control, use signed ping URLs (Healthchecks v2+ feature, in UI per-check).

## Backup

| | |
|---|---|
| **State** | `./volumes/data` — SQLite at `/data/hc.sqlite`: checks, ping URLs, notification channels, ping history |
| **Critical** | The ping URLs. Every monitored job holds one; regenerating them means reconfiguring every job that pings this instance, including `backup/borgmatic`. |
| **Quiescing** | Dump rather than copy |

```yaml
sqlite_databases:
    - name: healthchecks
      path: /srv/docker/monitoring/healthchecks/volumes/data/hc.sqlite
```

The hook reads the file from the host with borgmatic's own `sqlite3`; the image
has none. `UPSTREAM.md` documents a manual online backup through the image's
Python as the alternative.

**Restore order:** stop, restore, start, then confirm an existing job's ping still
registers — the URL must be unchanged.

## Known Issues

- **`volumes/data` must be owned by uid 999** — the app runs as `hc` (uid 999). If Docker creates the directory as root, or the operator creates it under their own user, the SQLite migration fails with `unable to open database file` and the container stays unhealthy. Fix: `chown -R 999:999 volumes/data` before first start. Confirmed on 2026-09-08 (v4.4).
- **Integrations cannot reach the Docker network unless `HC_ALLOW_PRIVATE_IPS=True`.** Healthchecks refuses to deliver to private addresses by default, and the ntfy stack next to it is one. The compose file names the trade-off.
- **`APP_TRAEFIK_HOST` typo causes Traefik 404** — double-check the hostname in `.env` after copying from `.env.example`. A typo (e.g. `helathchecks.example.com` instead of `healthchecks.example.com`) results in `HTTP 404` from Traefik with no other error. Verify with `docker inspect <container> | grep rule`.
- **Monitored-job reachability** — if your cron jobs run on servers that can't reach this instance (e.g. behind NAT without Tailscale), pings will silently fail. The only symptom is "check is down" in the UI for a job that is actually running fine. Check job-side logs first when diagnosing.
- **Email alerts require working SMTP.** Without SMTP, the only notification channels are webhooks, Slack, Discord, ntfy, and Pushover — all of which need to be configured per-check in the UI.
- **SECRET_KEY in `.env`** rather than `.secrets/` is a pragmatic blueprint deviation; see ROADMAP "Secret & Password Generation Standard" for the broader policy discussion.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `v5.0.3` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `healthchecks/healthchecks:v5.0.3` | 0 · 3 | 0 · 6 | — |

<!-- findings:end -->

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist
