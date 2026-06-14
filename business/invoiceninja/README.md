# Invoice Ninja

> **Status: 🔬 Preview** — v5.13.16 · 2026-04-14

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

### Step 3: Start (first boot — no APP_KEY yet)

```bash
docker compose up -d
docker compose logs -f app  # Wait until PHP-FPM and supervisor are running
```

### Step 4: Generate APP_KEY

```bash
docker compose run --rm app php artisan key:generate --show
```

Copy the `base64:...` output and set it in `.env`:

```env
APP_KEY=base64:your-key-here
```

**CRITICAL:** Never change `APP_KEY` after first boot. Changing it invalidates all encrypted data (stored payment tokens, gateway credentials).

### Step 5: Restart with Key

```bash
docker compose down
docker compose up -d
```

### Step 6: Log in

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
