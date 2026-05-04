# OpnForm

> **Status: ✅ Ready** — v1.13.2 · 2026-05-04

Self-hosted form builder — Typeform / Google Forms alternative. Drag-and-drop editor, conditional logic, file uploads, webhooks. Laravel API + Nuxt UI.

## Architecture

Seven services — nginx is the single Traefik entry point:

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx` | `nginx:1` | HTTP entry point — routes `/api/*` to php-fpm, everything else to Nuxt |
| `api` | `jhumanj/opnform-api:1.13.2` | Laravel backend — php-fpm on port 9000 |
| `api-worker` | same | `artisan queue:work` — processes async jobs (notifications, webhooks) |
| `api-scheduler` | same | `artisan schedule:work` — runs scheduled tasks |
| `ui` | `jhumanj/opnform-client:1.13.2` | Nuxt SSR frontend on port 3000 |
| `db` | `postgres:16-alpine` | Primary store (forms, responses, users, workspaces) |
| `redis` | `redis:7.4-alpine` | Cache, queue, sessions |

Traefik routes to **nginx only** (port 80). nginx handles path-based routing internally.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, MAIL_FROM_ADDRESS

# 2. Generate secrets (run each command, paste output into .env)
echo "base64:$(openssl rand -base64 32)"   # → APP_KEY
openssl rand -base64 32                    # → JWT_SECRET
openssl rand -base64 32                    # → FRONT_API_SECRET

# 3. Generate DB password secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt

# 4. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 5. Create volumes directory (entrypoint initialises subdirectories on first start)
mkdir -p volumes/storage volumes/postgres volumes/redis

# 6. Start
docker compose up -d

# 7. Follow logs — wait for "ready to handle connections" on api, then "Listening on" on ui
docker compose logs -f

# 8. Open UI and create the first account — it becomes the admin
# https://<APP_TRAEFIK_HOST>
# Public registration is disabled after the first account is created (SELF_HOSTED=true).
```

## Verify

```bash
docker compose ps                                    # all seven services up
curl -fsSI https://<APP_TRAEFIK_HOST>/               # 200 OK  (UI via nginx)
curl -fsSI https://<APP_TRAEFIK_HOST>/api/health     # 200 OK  (API via nginx → php-fpm)
```

## Security Model

- **First-user-wins admin** — the first registered account becomes the workspace admin. Register immediately after first start. Subsequent signups are blocked by `SELF_HOSTED=true`.
- **`APP_KEY`** encrypts Laravel sessions and tokens. Rotating invalidates all active sessions.
- **`JWT_SECRET`** signs API tokens. Rotating logs out all users.
- **`FRONT_API_SECRET` / `NUXT_API_SECRET`** is a shared secret between the Laravel API and the Nuxt SSR layer. Both must have the same value.
- **`DB_PWD_INLINE` duplicates the DB password** — Laravel reads `DB_PASSWORD` from env only (no `_FILE` support). Postgres side uses `POSTGRES_PASSWORD_FILE`.
- **`APP_TRUSTED_PROXIES: "*"`** — required so Laravel honours `X-Forwarded-Proto=https` from Traefik.
- **`NUXT_PRIVATE_API_BASE=http://nginx/api`** — Nuxt SSR calls the API via the internal Docker network (not the public URL), avoiding DNS resolution failures on private networks.
- **`no-new-privileges:true`** on all services.
- **Postgres + Redis on `app-internal` (`internal: true`)** — not reachable from outside Docker.

## Known Issues

- **Icon 404s in browser console** — `/api/_nuxt_icon/ix.json` and `heroicons.json` return 404. This is an upstream OpnForm issue: the icon proxy path gets routed to the Laravel API instead of the Nuxt icon server. Cosmetic only — the app works normally.
- **Storage bind mount permissions** — on first start the api entrypoint runs `chown -R www-data:www-data /usr/share/nginx/html/storage`. If permissions fail, fix with:
  ```bash
  docker compose exec api chown -R www-data:www-data /usr/share/nginx/html/storage
  docker compose exec api chmod -R 775 /usr/share/nginx/html/storage
  ```
- **Startup 502s in UI logs** — on first start the Nuxt SSR makes internal requests to `http://nginx/api` while the API is still initialising. These resolve once the API healthcheck passes (~60 seconds). Not an error.
- **`DB_PWD_INLINE` duplicates the DB password** — OpnForm's Laravel config reads `DB_PASSWORD` from env only. Postgres uses `POSTGRES_PASSWORD_FILE`; the API needs the same value inline.
- **Queue worker required for async features** — email notifications, webhook integrations, and file processing are handled by `api-worker`. If it's not running, those features silently fail.
- **Storage volume path** — the api image stores files at `/usr/share/nginx/html/storage`. All three api services (api, api-worker, api-scheduler) must mount the same path.

## Scripts Reference

| Script | Run with | Description |
|--------|----------|-------------|
| `artisan cache:clear` | `docker compose exec api php artisan cache:clear` | Clear application cache |
| `artisan config:clear` | `docker compose exec api php artisan config:clear` | Clear config cache |
| `artisan queue:work` | handled by `api-worker` container | Process queued jobs |

## Details

- [UPSTREAM.md](UPSTREAM.md)
