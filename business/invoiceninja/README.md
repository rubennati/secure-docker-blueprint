# Invoice Ninja

> **Status: 🔬 Preview** — v5.13.26 · 2026-07-26

Self-hosted invoicing, quotes, expenses, and time-tracking (Laravel / PHP-FPM).

## Services

| Service | Image | Purpose |
|---|---|---|
| app | invoiceninja/invoiceninja-debian | PHP-FPM + Supervisor (scheduler + 2 queue workers) |
| nginx | nginx | Web server — static assets + FastCGI proxy to app:9000 |
| mysql | mysql | Database (MySQL 8.x — upstream requirement) |
| redis | redis | Cache / queue broker / sessions |

Supervisor inside the `app` container manages the Laravel scheduler and queue workers — no separate cron or worker container is needed.

## Security Features

- `no-new-privileges:true` on all services
- All services isolated on an internal bridge network
- nginx is the only public-facing service (on the `proxy` network)
- MySQL and Redis are not exposed on the host
- `REQUIRE_HTTPS=true` enforced via env
- `APP_DEBUG=false` in production
- Access restricted to VPN (`acc-tailscale`) by default
- Known deviation: secrets in `.env` (Laravel has no `_FILE` support — see UPSTREAM.md)

## First-Time Setup

### Step 1: Configure

```bash
cp .env.example .env
nano .env
```

Set these values:

| Variable | Description |
|---|---|
| `APP_TRAEFIK_HOST` | Your domain (e.g. `invoice.example.com`) |
| `IN_USER_EMAIL` | Initial admin email |
| `MAIL_HOST` / `MAIL_*` | SMTP settings for sending invoices |

### Step 2: Generate Passwords

```bash
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^IN_PASSWORD=.*|IN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
```

### Step 3: Generate APP_KEY (before first boot)

**APP_KEY must be set before starting the stack for the first time.** Generate it now using `openssl` — no containers required:

```bash
APP_KEY="base64:$(openssl rand -base64 32)"
sed -i "s|^APP_KEY=.*|APP_KEY=${APP_KEY}|" .env
```

**CRITICAL:** Never change `APP_KEY` after data exists in the database. It encrypts stored payment tokens, gateway credentials, and other sensitive values. If `APP_KEY` changes, that data becomes unreadable.

Save a copy of your `.env` (including `APP_KEY`) in a secure location before starting.

### Step 4: Start

```bash
docker compose up -d
```

On first boot the app runs database migrations and seeds initial data. Watch progress:

```bash
docker compose logs app --follow
```

Expected success markers (in order):

```
Creating migration table
Running migrations
Seeding database
Production setup completed
php-fpm entered RUNNING state
queue-worker_00 entered RUNNING state
queue-worker_01 entered RUNNING state
scheduler entered RUNNING state
```

First boot typically takes 1–3 minutes. MySQL initialization and user/database creation happen before the app container starts (enforced by the healthcheck), so the race condition between the app and MySQL is handled automatically.

### Step 5: Log in

Open `https://invoice.example.com` and log in with `IN_USER_EMAIL` / `IN_PASSWORD`.

After logging in you can remove or blank `IN_USER_EMAIL` and `IN_PASSWORD` from `.env` — the account already exists in the database.

## Verify

```bash
docker compose ps                         # All 4 services healthy/running
docker compose logs app --tail=20         # No errors; supervisor procs listed
curl -sI https://your-domain/            # 200 or 302
```

## TODOs After Initial Setup

- [ ] `APP_KEY` set and saved in a secure location (loss = cannot decrypt stored data)
- [ ] `IN_USER_EMAIL` and `IN_PASSWORD` blanked or removed from `.env`
- [ ] SMTP configured and tested (send a test invoice)
- [ ] Backup strategy in place (see UPSTREAM.md)
- [ ] Upgrade check: verify `APP_TAG` against latest stable release (see UPSTREAM.md)
- [ ] Consider tightening `TRUSTED_PROXIES` from `*` to the Traefik network CIDR

## Diagnostics

### Check running version

```bash
docker compose exec app php artisan --version
```

Visit **Settings → Account Management → Version** in the UI.

### Check supervisor processes (scheduler + queue workers)

```bash
docker compose exec app supervisorctl status
```

Expected output: `php-fpm`, `scheduler`, and `queue-worker_00` / `queue-worker_01` — all `RUNNING`.

### Check queue backlog

```bash
docker compose exec app php artisan queue:monitor
```

### SMTP troubleshooting

After changing `MAIL_*` variables, recreate the app container:

```bash
docker compose up -d --force-recreate app
```

Verify env vars were picked up:

```bash
docker compose exec app sh -c 'env | grep -E "^MAIL_"'
```

### PDF / live preview troubleshooting

Invoice Ninja uses Snappdf (Chromium) for PDF rendering. If `/api/v1/live_design` or `/api/v1/live_preview` return 504 or 500:

1. **504 from nginx** — FastCGI read timeout exceeded. Check nginx access log for the upstream response time:
   ```bash
   docker compose logs nginx --tail=50 | grep "live_design\|live_preview"
   ```
   The nginx FastCGI timeouts are set to 300s in `nginx/laravel.conf`. If renders still time out, Chromium may be crashing — check app logs.

2. **500 from the app** — Chromium likely ran out of memory or crashed. Check:
   ```bash
   docker compose logs app --tail=50 | grep -iE "snappdf|chromium|chrome|error|fatal"
   ```
   The app container memory limit is 1G. If Chromium crashes repeatedly, increase `memory:` in `docker-compose.yml`.

3. **Check Chromium path**:
   ```bash
   docker compose exec app ls -la /usr/bin/google-chrome-stable
   ```

### Browser console warnings (non-critical)

These warnings appear in the browser DevTools console and are expected or cosmetic:

| Warning | Meaning | Action |
|---|---|---|
| `tiptap: Extension X is already registered` | Duplicate frontend JS extension registration | Cosmetic — does not affect functionality |
| `CSP report-only violations` | App tries to load external docs/images; `report-only` means violations are logged but not blocked | No action unless strict CSP is required |

The actionable errors are HTTP **504** on `/api/v1/live_design` and **500** on `/api/v1/live_preview`. Debug those with the steps above, not the console warnings.

### Logs

```bash
docker compose logs app --tail=50           # PHP-FPM + supervisor output
docker compose logs nginx --tail=20         # Access and error logs
docker compose logs mysql --tail=20         # DB startup and errors
```

### Database shell

```bash
docker compose exec mysql mysql -u ninja -p ninja
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Deviations, backup, restore, upgrade checklist, known issues
