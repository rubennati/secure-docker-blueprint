# OpnForm

> **Upgrading from 1.x is a major version change.** Verify before rolling it out.

Self-hosted form builder — Typeform / Google Forms alternative. Drag-and-drop editor, conditional logic, file uploads, webhooks. Laravel API + Nuxt UI.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

Seven services — `opnform-nginx` is the single Traefik entry point:

| Service | Image | Purpose |
|---------|-------|---------|
| `opnform-nginx` | `nginx:1.31.8` | HTTP entry point — routes `/api/*` to php-fpm, everything else to Nuxt |
| `api` | `jhumanj/opnform-api:2.8.4` | Laravel backend — php-fpm on port 9000 |
| `api-worker` | same | `artisan queue:work` — processes async jobs (notifications, webhooks) |
| `api-scheduler` | same | `artisan schedule:work` — runs scheduled tasks |
| `ui` | `jhumanj/opnform-client:2.8.4` | Nuxt SSR frontend on port 3000 |
| `db` | `postgres:16.15-alpine` | Primary store (forms, responses, users, workspaces) |
| `redis` | `redis:8.10.3-alpine` | Cache, queue, sessions |

Traefik routes to **`opnform-nginx` only** (port 80). It handles path-based routing internally.

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'DB_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env.local
printf 'APP_KEY=base64:%s\n' "$(openssl rand -base64 32)" >> .env.local
printf 'JWT_SECRET=%s\n' "$(openssl rand -base64 32 | tr -d '\n')" >> .env.local
printf 'FRONT_API_SECRET=%s\n' "$(openssl rand -base64 32 | tr -d '\n')" >> .env.local

mkdir -p volumes/local/redis
sudo chown 999:1000 volumes/local/redis
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

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
# Redis runs as the image's own user and cannot fix ownership itself
sudo chown 999:1000 volumes/redis

# 6. Start
docker compose up -d

# 7. Follow logs — wait for "ready to handle connections" on api, then "Listening on" on ui
docker compose logs -f

# 8. Over the VPN, open the UI and create the first account — it becomes the admin.
#    The route ships closed (APP_TRAEFIK_ACCESS=access-vpn); switch it to
#    access-public afterwards, so the forms reach their respondents.
# https://<APP_TRAEFIK_HOST>
# Public registration is disabled after the first account is created (SELF_HOSTED=true).
```

## Verify

```bash
docker compose ps                                    # all seven services up
curl -fsSI https://<APP_TRAEFIK_HOST>/               # 200 OK  (UI via opnform-nginx)
curl -fsSI https://<APP_TRAEFIK_HOST>/api/healthcheck # 200 OK  (API via opnform-nginx → php-fpm)
```

## Security Model

- **First-user-wins admin** — the first visit to `/` redirects to `/setup`, and the first registered account becomes the workspace admin; there is no setup secret. With a public route that is whoever arrives first, which is why the route ships at `access-vpn`: register over the VPN, then open it. Subsequent signups are refused (`Registration is not allowed.` at 2.8.4) by `SELF_HOSTED=true`.
- **`APP_KEY`** encrypts Laravel sessions and tokens. Rotating invalidates all active sessions.
- **`JWT_SECRET`** signs API tokens. Rotating logs out all users.
- **`FRONT_API_SECRET` / `NUXT_API_SECRET`** is a shared secret between the Laravel API and the Nuxt SSR layer. Both must have the same value.
- **`DB_PWD_INLINE` duplicates the DB password** — Laravel reads `DB_PASSWORD` from env only (no `_FILE` support). Postgres side uses `POSTGRES_PASSWORD_FILE`.
- **`APP_TRUSTED_PROXIES: "*"`** — required so Laravel honours `X-Forwarded-Proto=https` from Traefik.
- **`NUXT_PRIVATE_API_BASE=http://opnform-nginx/api`** — Nuxt SSR calls the API via the internal Docker network (not the public URL), avoiding DNS resolution failures on private networks.
- **`no-new-privileges:true`** on all services.
- **`headers-standard` sends `X-Frame-Options: DENY`, which blocks the form embed.** Putting a form in another page — a website, a [Notion page](https://help.opnform.com/en/article/can-i-embed-my-form-in-a-notion-page-or-site-x7guph/) — is a documented OpnForm feature and how most forms are distributed. The default stays denying because the form pages and the workspace admin share one hostname, so relaxing the header for the forms relaxes it for form management as well. To embed, switch the router to `headers-application-owned` and add a stack middleware before it that sets a `frame-ancestors` CSP naming the sites you embed into; `apps/onlyoffice` shows the shape. `frame-self` does not help — it permits same-origin framing only, and an embed is by definition another origin.
- **`app-internal` is not `internal: true`** — the Nuxt SSR server calls `api.iconify.design` at startup to resolve icons; blocking outbound internet causes `EAI_AGAIN` DNS failures. Isolation is enforced at the Traefik layer: only `opnform-nginx` is on `proxy-public` and exposed to the reverse proxy. `db` and `redis` are on `app-internal` only and therefore unreachable from outside Docker.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `opnform-db` · database `opnform` · user `opnform` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · `./volumes/storage` (file uploads submitted through forms) |
| **Reproducible** | `./volumes/redis` — cache and queue |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: opnform
      username: opnform
      # The server's own client, inside its container (FA-03)
      pg_dump_command: docker exec opnform-db pg_dump
      pg_restore_command: docker exec -i opnform-db pg_restore
      psql_command: docker exec -i opnform-db psql
```

Form submissions are database rows; anything a respondent uploaded is in
`volumes/storage`. Restoring only the database gives submissions whose attachments
are gone — and unlike most losses here, the data cannot be asked for again without
contacting the people who sent it.

**Restore order:** database first, then the app. The worker and scheduler come up
with it; a queue restored mid-flight simply retries.

## Known Issues

- **Icon 404s in browser console** — `/api/_nuxt_icon/ix.json` and `heroicons.json` return 404. This is an upstream OpnForm issue: the icon proxy path gets routed to the Laravel API instead of the Nuxt icon server. Cosmetic only — the app works normally.
- **Storage bind mount permissions** — on first start the api entrypoint runs `chown -R www-data:www-data /usr/share/nginx/html/storage`. If permissions fail, fix with:

  ```bash
  docker compose exec api chown -R www-data:www-data /usr/share/nginx/html/storage
  docker compose exec api chmod -R 775 /usr/share/nginx/html/storage
  ```

- **Startup 502s in UI logs** — on first start the Nuxt SSR makes internal requests to `http://opnform-nginx/api` while the API is still initialising. These resolve once the API healthcheck passes (~60 seconds). Not an error.
- **`DB_PWD_INLINE` duplicates the DB password** — OpnForm's Laravel config reads `DB_PASSWORD` from env only. Postgres uses `POSTGRES_PASSWORD_FILE`; the API needs the same value inline.
- **Queue worker required for async features** — email notifications, webhook integrations, and file processing are handled by `api-worker`. If it's not running, those features silently fail.
- **Storage volume path** — the api image stores files at `/usr/share/nginx/html/storage`. All three api services (api, api-worker, api-scheduler) must mount the same path.

## Scripts Reference

| Script | Run with | Description |
|--------|----------|-------------|
| `artisan cache:clear` | `docker compose exec api php artisan cache:clear` | Clear application cache |
| `artisan config:clear` | `docker compose exec api php artisan config:clear` | Clear config cache |
| `artisan queue:work` | handled by `api-worker` container | Process queued jobs |

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `2.8.4` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `jhumanj/opnform-api:2.8.4` | 1 · 1 | — | — |
| `jhumanj/opnform-client:2.8.4` | — | 0 · 6 | — |
| `nginx:1.31.8` | 0 · 2 | — | — |
| `postgres:16.15-alpine` | — | — | 1 · 25 |
| `redis:8.10.3-alpine` | — | — | — |

<!-- findings:end -->

The API image, `jhumanj/opnform-api:2.8.4`, ships Alpine `brotli-libs` 1.2.0 with one CRITICAL finding (CVE-2026-111497, fixed in 1.2.1, listed by CISA as exploited). It is the newest release, and upstream has not rebuilt the image.

**Risk:** the library backs PHP's curl, which OpnForm uses for outbound requests such as webhooks, so a hostile endpoint could in principle reach it. Limit webhooks to endpoints you trust and move to the next release.

The PostgreSQL image, `postgres`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.

## Details

- [UPSTREAM.md](UPSTREAM.md)
