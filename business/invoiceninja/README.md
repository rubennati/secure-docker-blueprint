# Invoice Ninja

> **Status: 🚧 v5.13.26** — credentials moved into Docker Secrets;
> not yet exercised on a host · 2026-07-29

Self-hosted invoicing, quotes, expenses, and time-tracking (Laravel / PHP-FPM).

## Minimum requirements

From the project's own [server requirements](https://www.invoiceninja.org/getting-started/):

| | Upstream |
|---|---|
| RAM | 1 GB, **2 GB recommended** |
| CPU | 1 vCPU core |
| Storage | 20 GB |
| PHP | 8.1 or higher |
| Database | MySQL 5.7+ or MariaDB 10.3+ |
| Web server | Nginx or Apache |

Those figures describe the application alone. This stack runs four containers,
and the resource limits in `docker-compose.yml` reserve 1 GB for the application
and 1 GB for MySQL — so **2 GB is the floor and 4 GB is comfortable**. The
application limit is not padding: Chromium renders the PDFs and the live design
previews, and it exceeds 512 MB under concurrent load.

The pinned images clear every line above — PHP 8.x in the application image,
MySQL 8.4, nginx.

PHP extensions (BCMath, Ctype, Fileinfo, JSON, Mbstring, OpenSSL, PDO,
Tokenizer, XML, GD) come with the official image; the list matters only if you
depart from it.

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
- All six credentials in Docker Secrets, injected by `ops/entrypoint.sh`
- `app-internal` is `internal: true`; only the app container has an outbound path

## Backup

| | |
|---|---|
| **Database** | MySQL · container `invoiceninja-mysql` · database `ninja` · user `ninja` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `mysql_data` (database) · `app_storage` (attachments, logos, generated PDFs) · **`.env`, especially `APP_KEY`** |
| **Reproducible** | `redis_data` (cache) · `app_public` — served assets, rebuilt by the image |
| **Quiescing** | Not needed. The dump is consistent on its own. |

This stack uses **named volumes**, not bind mounts. Their host paths are
`/var/lib/docker/volumes/invoiceninja_<name>/_data` — that is what goes into
`source_directories`, not a path under the stack directory.

```yaml
mysql_databases:
    - name: ninja
      container: invoiceninja-mysql
      username: ninja
      password: "{credential file /srv/docker/business/invoiceninja/.secrets/db_pwd.txt}"
```

**`.secrets/app_key.txt` decrypts the stored data.** Without it a restored database
is unreadable — this is the single most important line in this section, and it is
the one thing here that is not in a volume. Back `.env` up with the database, and
keep a copy of `APP_KEY` somewhere the host cannot reach.

Point borgmatic straight at `.secrets/db_pwd.txt`, the same file the stack
mounts — one copy of the password on the host, and nothing to update twice when
it is rotated.

Manual dump and restore, when borgmatic is not in the picture:

```bash
# Dump
docker exec invoiceninja-mysql mysqldump \
  -u root -p"$(grep '^DB_ROOT_PASSWORD=' .env | cut -d= -f2)" ninja \
  > backup-db-$(date +%Y%m%d-%H%M).sql

docker run --rm -v invoiceninja_app_storage:/data:ro -v "$(pwd)":/out \
  alpine tar czf /out/backup-storage-$(date +%Y%m%d-%H%M).tar.gz -C /data .

cp .env .env.backup-$(date +%Y%m%d)

# Restore — database first, with only MySQL running
docker compose up -d mysql
docker compose exec mysql sh -c 'mysql -u root -p"${MYSQL_ROOT_PASSWORD}" ninja' \
  < backup-db-YYYYMMDD-HHMM.sql

docker run --rm -v invoiceninja_app_storage:/data -v "$(pwd)":/in \
  alpine sh -c "cd /data && tar xzf /in/backup-storage-YYYYMMDD-HHMM.tar.gz"
```

**Back up before every upgrade.** Invoice Ninja runs migrations on start, and a
failed migration against a database with no dump behind it is not recoverable.

**Restore order:** `.env` and database first, then storage, then the app.

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

### Step 2: Create the secrets

Nothing sensitive goes in `.env`. All six live in `.secrets/`, and the
application reads them through `ops/entrypoint.sh`.

```bash
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
openssl rand -hex 32    | tr -d '\n' > .secrets/redis_pwd.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/in_pwd.txt
printf 'your-smtp-password'          > .secrets/mail_pwd.txt
chmod 600 .secrets/*.txt
```

`in_pwd.txt` is the first administrator's password, used on the first start
only. Read it once, store it, then change it in the interface.

### Step 3: Generate the APP_KEY, before the first start

It has to exist before the stack comes up — starting without it fails during the
migration. Let the application generate it: Laravel expects the `base64:` prefix
its own generator produces, which `openssl rand` alone does not give you.

```bash
docker run --rm invoiceninja/invoiceninja-debian:5.13.26 \
  php artisan key:generate --show | tr -d '\n' > .secrets/app_key.txt
chmod 600 .secrets/app_key.txt
```

**Never change it once data exists.** It encrypts stored payment tokens and
gateway credentials; if it changes, that data is unreadable.

Store a copy of `app_key.txt` somewhere this host cannot reach — a database
backup without it restores nothing readable.

### Step 4: Start

```bash
docker compose up -d
```

On first boot the app runs database migrations and seeds initial data. Watch progress:

```bash
docker compose logs app --follow
```

Expected success markers (in order):

```text
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
