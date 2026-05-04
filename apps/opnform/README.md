# OpnForm

> **Status: 🚧 Draft** — not yet deployed.

Self-hosted form builder — Typeform / Google Forms alternative. Drag-and-drop editor, conditional logic, file uploads, webhooks. Laravel API + Nuxt UI.

## Architecture

Five services — nginx is the single entry point, routing to php-fpm or the Nuxt UI:

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx` | `nginx:1` | HTTP entry point — routes `/api/*`, `/open/*` to php-fpm; everything else to the UI |
| `api` | `jhumanj/opnform-api:1.13.2` | Laravel backend — php-fpm on port 9000 |
| `ui` | `jhumanj/opnform-client:1.13.2` | Nuxt frontend on port 3000 |
| `db` | `postgres:16-alpine` | Primary store (forms, responses, users, workspaces) |
| `redis` | `redis:7.4-alpine` | Cache + queue + sessions |

Traefik routes to **nginx only** (port 80). nginx handles path-based splitting internally via `docker/nginx.conf`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, TZ, MAIL_FROM_ADDRESS

# 2. Generate Laravel APP_KEY
# Note: the opnform-api entrypoint waits for the DB, so `php artisan key:generate`
# hangs when run standalone. Generate the key directly instead:
echo "base64:$(openssl rand -base64 32)"
# Copy the 'base64:...' output into APP_KEY in .env

# 3. Generate DB secret
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt

# 4. Sync DB_PWD_INLINE with the secret file
sed -i "s|^DB_PWD_INLINE=.*|DB_PWD_INLINE=$(cat .secrets/db_pwd.txt)|" .env

# 5. Create volumes
mkdir -p volumes/postgres volumes/redis volumes/api-storage

# 6. Start
docker compose up -d

# 7. Wait for Laravel migrations (~60 seconds)
docker compose logs api --follow
# Watch for: "Application ready"

# 8. Open UI and register the first account (becomes admin)
# https://<APP_TRAEFIK_HOST>
```

## Verify

```bash
docker compose ps                                    # five services up
curl -fsSI https://<APP_TRAEFIK_HOST>/               # 200 OK  (UI via nginx)
curl -fsSI https://<APP_TRAEFIK_HOST>/api/health     # 200 OK  (API via nginx → php-fpm)
```

## Security Model

- **First-user-wins admin** — the first account to register becomes the workspace admin. Set `REGISTRATION_DISABLED=true` (default) to block further signups after that.
- **`APP_KEY`** encrypts Laravel sessions and form-response encryption. Rotating invalidates sessions and any stored-encrypted response data.
- **`DB_PWD_INLINE` duplicates the DB password** — see Known Issues.
- **`APP_TRUSTED_PROXIES: "*"`** — required so Laravel honours `X-Forwarded-Proto=https` from Traefik.
- **`no-new-privileges:true`** on all services.
- **`read_only: true` + tmpfs on redis** — persistence via `/data` volume only.
- **Postgres + Redis on `app-internal` (`internal: true`)** — not reachable from outside.
- **Default access `acc-public` + `sec-2`** — forms are meant to be filled out by external users. The public form URLs (`/forms/<slug>`) must be reachable. The admin UI is on the same host — gate with `sec-3` + a stricter access policy if sensitive.

## Known Issues

- **Not yet deployed.** Expect minor surprises, especially path-priority tuning in Traefik.
- **`DB_PWD_INLINE` duplicates the DB password** — OpnForm's Laravel config reads `DB_PASSWORD` from env only. Postgres side uses `POSTGRES_PASSWORD_FILE`; OpnForm needs the same value inline.
- **`APP_TAG=latest` is not reproducible** — pin to a specific version. OpnForm's release cadence is frequent.
- **Mail driver defaults to `log`** — no outgoing email until you set `MAIL_MAILER=smtp` + the `MAIL_*` env vars. Form submission notifications and admin invitations rely on this.
- **Startup 502s in UI logs** — on first start the Nuxt SSR calls the API via the public URL while the API is still initialising. These resolve within ~30 seconds once the API is ready. Not an error.
- **Storage volume** — form file uploads and logo images land in `volumes/api-storage/`. Back up together with the Postgres dump.
- **Queue worker not run** — Laravel queue jobs for this image run on demand (short-lived). For heavy setups, consider adding a separate `worker` service running `php artisan queue:work`.

## Details

- [UPSTREAM.md](UPSTREAM.md)
