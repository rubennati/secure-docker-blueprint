# Lychee

Self-hosted photo gallery focused on fast browsing and clean presentation. Three-service stack: Laravel app, MariaDB backend, Redis cache.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

| Service | Image | Purpose |
|---------|-------|---------|
| `lychee-app` | `lycheeorg/lychee:v7.12.1` | PHP/Laravel app on FrankenPHP |
| `db` | `mariadb:12.3.3` | Primary store (albums, photo metadata, users) |
| `redis` | `redis:8.10.3-alpine` | Cache + session driver |

## Try it locally

Runs on `http://localhost:8000` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local # fill the empty secrets
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8000
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, PUID/PGID

# 2. Generate Laravel APP_KEY (one-time)
echo "APP_KEY=base64:$(openssl rand -base64 32)"
# Copy the full 'APP_KEY=base64:...' line into .env
# Note: docker run key:generate does NOT work — the entrypoint blocks it if APP_KEY is unset.

# 3. Generate DB secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

# 4. Volume ownership (Lychee entrypoint drops to PUID/PGID)
mkdir -p volumes/{uploads,logs,tmp,mysql,redis}
sudo chown -R 1000:1000 volumes/uploads volumes/logs volumes/tmp
# Redis runs as the image's own user and cannot fix ownership itself
sudo chown 999:1000 volumes/redis

# 5. Start
docker compose up -d

# 6. Wait for first-run migrations (~60 seconds — note the STARTUP_DELAY=30)
docker compose logs lychee-app --follow
# Watch for: "Started Apache"

# 7. Over the VPN, open the UI and create the admin account on first visit. The
#    route ships closed (APP_TRAEFIK_ACCESS=access-vpn); open it afterwards
# https://<APP_TRAEFIK_HOST>
# The first-visit wizard creates the admin user.
```

## Verify

```bash
docker compose ps                              # three services healthy
curl -fsSI https://<APP_TRAEFIK_HOST>/         # 200 OK
```

## Security Model

- **First-visit admin creation** — until an admin exists, `/` redirects to `/install/admin`, whose form creates the admin for whoever submits it — no setup secret, no CSRF token; afterwards it answers `403` (measured on the lab host at v7.12.1). With a public route that is whoever arrives first, which is why the route ships at `access-vpn`: create the admin over the VPN, then open it.
- **`APP_KEY`** encrypts Laravel sessions and signed URLs. Rotating invalidates all sessions (acceptable).
- **`DB_PASSWORD_FILE` is supported natively** — Lychee reads the password from `/run/secrets/DB_PWD`. No inline duplication needed.
- **`MYSQL_PASSWORD_FILE` + `MYSQL_ROOT_PASSWORD_FILE`** — MariaDB also reads secrets from files.
- **`cap_drop: ALL`** on MariaDB with minimal `cap_add` (CHOWN, SETUID, SETGID, DAC_OVERRIDE).
- **`no-new-privileges:true`** on all services.
- **Redis is `read_only: true` + tmpfs /tmp** — persistence via `/data` volume.
- **MariaDB + Redis on `app-internal` (`internal: true`)** — not reachable from outside the app.
- **`TRUSTED_PROXIES: "*"`** — required behind Traefik so Laravel trusts `X-Forwarded-*` headers.

## Backup

| | |
|---|---|
| **Database** | MariaDB · container `lychee-db` · database `lychee` · user `lychee` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/mysql` (database) · `./volumes/uploads` (the photos) |
| **Reproducible** | `./volumes/redis` (cache) · `./volumes/logs` · `./volumes/tmp` |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
mariadb_databases:
    - name: lychee
      container: lychee-db
      username: lychee
      password: "{credential file /srv/docker/apps/lycheeorg/.secrets/db_pwd.txt}"
```

`volumes/uploads` holds the originals and the generated sizes together. The
database holds albums and permissions that reference them by path, so the two have
to be restored as a pair — a mismatch produces albums full of missing files rather
than an error.

**Restore order:** database first, then the app.

## Known Issues

- **`docker run key:generate` is blocked by the entrypoint** — the Lychee entrypoint validates `APP_KEY` before executing any command, so `php artisan key:generate --show` never runs. Use `echo "APP_KEY=base64:$(openssl rand -base64 32)"` directly (see Setup step 2).
- **`STARTUP_DELAY=30`** — Lychee waits 30 s for MariaDB before starting. Leave as-is unless your DB is unusually slow.
- **WebAuthn is enabled by default** — disable via `DISABLE_WEBAUTHN=true` if you do not want passkey support.
- **Redis password is not configured here** — Redis runs on the internal network only. If you expose it or move it off-host, add a password.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

Not scanned at the pin `v7.13.0` yet.

<!-- findings:end -->

The MariaDB image, `mariadb`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.

## Details

- [UPSTREAM.md](UPSTREAM.md)
