# Upstream Reference

## Source

- **Repo:** https://github.com/invoiceninja/dockerfiles (branch: `debian`)
- **Docs:** https://invoiceninja.github.io/docs/self-host/self-host-installation
- **Based on version:** 5.13.16
- **Last checked:** 2026-04-14

## What we use from upstream

| File | Used as | Notes |
|------|---------|-------|
| `docker-compose.yml` | Adapted | Added Traefik labels, Blueprint naming |
| `.env` | Adapted | Restructured, passwords as placeholders |
| `nginx/laravel.conf` | 1:1 copy | Server block for Laravel/PHP-FPM |
| `nginx/invoiceninja.conf` | 1:1 copy | Global nginx settings (gzip, buffers) |

## What we changed and why

| Change | Reason |
|--------|--------|
| Traefik labels on nginx | Blueprint uses Traefik, not exposed ports |
| certresolver commented out | crt.sh privacy |
| Network `name:` added | Blueprint naming (`invoiceninja-internal`) |
| Container names via variables | Blueprint standard |
| Image tags fixed (not floating) | Reproducibility |
| Passwords in .env (not Secrets) | Laravel has no _FILE support, env_file pattern |
| `COMPOSE_PROJECT_NAME` instead of `STACK_NAME` | Docker Compose standard variable |

## What we kept from upstream

- `build: context: .` — allows local image build
- `env_file: ./.env` — Invoice Ninja reads many env vars directly
- Named volumes (not bind mounts) — upstream pattern
- Service names: app, nginx, mysql, redis
- nginx config files — 1:1 from upstream
- All app env vars (FILESYSTEM_DISK, CACHE_DRIVER, etc.)

## First-time setup

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set HOST_DOMAIN, IN_USER_EMAIL

# 2. Generate passwords
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env
sed -i "s|^IN_PASSWORD=.*|IN_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')|" .env

# 3. Fix MYSQL_ variables (they reference DB_ vars but sed broke the chain)
DB_PWD=$(grep '^DB_PASSWORD=' .env | cut -d= -f2)
DB_ROOT=$(grep '^DB_ROOT_PASSWORD=' .env | cut -d= -f2)
sed -i "s|^MYSQL_PASSWORD=.*|MYSQL_PASSWORD=${DB_PWD}|" .env
sed -i "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=${DB_ROOT}|" .env

# 4. Start (first time builds the image)
docker compose up -d

# 5. Generate APP_KEY
docker compose run --rm app php artisan key:generate --show
# Copy output to .env: APP_KEY=base64:...

# 6. Restart with key
docker compose down
docker compose up -d
```

## Verify

```bash
docker compose ps                    # All 4 services healthy/running
docker compose logs app | tail -20   # Should show "Seahub is started" equivalent
curl -sI https://your-domain/       # Should return 200 or 302
```

## Upgrade checklist

1. Check [Invoice Ninja releases](https://github.com/invoiceninja/invoiceninja/releases)
2. Check [dockerfiles repo](https://github.com/invoiceninja/dockerfiles/tree/debian) for changes
3. Bump `APP_TAG` in `.env`
4. `docker compose build` → `docker compose up -d`
5. Check logs for migration output

## Known issues

- **502 with Blueprint network naming**: Earlier attempts with `app-internal` + `proxy-public` and `internal: true` caused nginx DNS resolution to wrong network IP. Current setup uses simple `internal` (bridge) + `proxy` (external) which works.
- **No Docker Secrets**: Laravel doesn't support `_FILE` env vars. Passwords stored in `.env` (gitignored).
- **First boot race**: MySQL init causes brief `Connection refused` from app — normal, resolves after ~30s.
