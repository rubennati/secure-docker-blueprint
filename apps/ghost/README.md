# Ghost

Headless Node.js CMS focused on publishing, newsletters, and paid memberships. This setup runs Ghost with a dedicated MySQL 8 database and an external SMTP relay for member emails.

## Architecture

Two services:

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghost:6-alpine` | Ghost CMS (Node.js), serves the blog + admin UI on port `2368` |
| `db` | `mysql:8.4` | Ghost's content database (posts, members, settings) |

Ghost's built-in mailer (`mail__transport: SMTP`) is required for member signup confirmation emails and newsletter sending. Without working SMTP, signups silently fail.

### Secret handling

Ghost supports its own file-based secrets pattern via the `__file` suffix on config keys:

```yaml
database__connection__password__file: /run/secrets/DB_PWD
mail__options__auth__pass__file: /run/secrets/GHOST_MAIL_PWD
```

This maps to Ghost's nconf config `database.connection.password.file` — Ghost resolves these at startup and reads the file contents. No entrypoint wrapper is needed.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, GHOST_MAIL_*, TZ

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
printf '%s' 'YOUR-SMTP-PASSWORD' > .secrets/mail_pwd.txt

# 3. Start
docker compose up -d

# 4. Open the admin UI and finish setup
# https://<APP_TRAEFIK_HOST>/ghost/
```

Default access policy is `acc-public` + `sec-2` — a public blog with standard headers and soft rate limiting.

## Verify

```bash
docker compose ps                       # Both services healthy
docker compose logs app --tail 50       # Ghost startup, DB migration messages
docker compose logs db --tail 20        # MySQL ready-for-connections
```

Check that SMTP works: register a test member on the site and confirm the verification email arrives.

## Security Model

- Database is on the internal network `${COMPOSE_PROJECT_NAME}-internal`, not reachable from `proxy-public`
- MySQL runs with `cap_drop: ALL` and only the minimum capabilities (`CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`) needed for user switching and file ownership on the data volume
- DB password, root password, and SMTP password are Docker Secrets (files under `./.secrets/`)
- `no-new-privileges:true` on both containers
- Ghost itself runs as a non-root user inside the container (configured by the upstream image)

## Known Issues

- **Ghost 6 DB migrations on first start can take 30–60 seconds.** The `start_period: 45s` on the healthcheck allows for this; if migrations take longer (e.g. on slow storage), the container may briefly show `unhealthy` before recovering.
- **Email deliverability.** Ghost uses the `Mail-From` domain as-is. SPF/DKIM/DMARC for `GHOST_MAIL_FROM` must be configured at your DNS provider, otherwise member emails end up in spam.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
