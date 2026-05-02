# Ghost

Headless Node.js CMS focused on publishing, newsletters, and paid memberships. This setup runs Ghost with a dedicated MySQL 8 database and an external SMTP relay for member emails. ActivityPub (Fediverse/Mastodon integration) is optional via a separate overlay file.

## Architecture

Base stack (two services):

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `ghost:6-alpine` | Ghost CMS (Node.js), serves the blog + admin UI on port `2368` |
| `db` | `mysql:8.4` | Ghost's content database (posts, members, settings) |

Optional ActivityPub stack (`activitypub.yml`):

| Service | Image | Purpose |
|---------|-------|---------|
| `activitypub` | `ghcr.io/tryghost/activitypub` | ActivityPub backend — keys, federation, Fediverse API |
| `activitypub-migrate` | `ghcr.io/tryghost/activitypub-migrations` | One-shot migration runner, exits after schema init |

Ghost's built-in mailer (`mail__transport: SMTP`) is required for member signup confirmation emails and newsletter sending. Without working SMTP, signups silently fail.

### Secret handling

Ghost does not support Docker's native `_FILE` env var pattern. A custom entrypoint (`ops/entrypoint.sh`) reads the secret files at container startup and exports the plain env vars Ghost expects before handing off to `docker-entrypoint.sh`:

```sh
export database__connection__password="$(cat /run/secrets/DB_PWD)"
export mail__options__auth__pass="$(cat /run/secrets/GHOST_MAIL_PWD)"
exec docker-entrypoint.sh node current/index.js
```

The ActivityPub service has the same limitation — `ops/activitypub-entrypoint.sh` follows the same pattern for `MYSQL_PASSWORD`.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, GHOST_MAIL_*, TZ
# To enable ActivityPub: set COMPOSE_FILE=docker-compose.yml:activitypub.yml

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

### Enabling ActivityPub on an existing deployment

ActivityPub requires its own database. For existing deployments where MySQL already has data, create the database once manually before enabling ActivityPub:

```bash
docker exec ghost-db sh /docker-entrypoint-initdb.d/01-activitypub-db.sh
```

Then set `COMPOSE_FILE=docker-compose.yml:activitypub.yml` in `.env` and run `docker compose up -d`.

## Verify

```bash
docker compose ps                       # All services healthy
docker compose logs app --tail 50       # Ghost startup, DB migration messages
docker compose logs db --tail 20        # MySQL ready-for-connections

# With ActivityPub:
docker compose logs activitypub --tail 30       # booted + no key errors
docker compose logs activitypub-migrate         # migrations ran, exited 0
```

Check that SMTP works: register a test member on the site and confirm the verification email arrives.

## Security Model

- Database is on the internal network `${COMPOSE_PROJECT_NAME}-internal`, not reachable from `proxy-public`
- MySQL runs with `cap_drop: ALL` and only the minimum capabilities (`CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`) needed for user switching and file ownership on the data volume
- DB password, root password, and SMTP password are Docker Secrets (files under `./.secrets/`)
- `no-new-privileges:true` on all containers
- Ghost and ActivityPub run as non-root users inside their containers (configured by upstream images)
- ActivityPub backend is on the internal network; only Traefik routes the specific ActivityPub paths to it

## Known Issues

- **Ghost 6 DB migrations on first start can take 30–60 seconds.** The `start_period: 45s` on the healthcheck allows for this; if migrations take longer (e.g. on slow storage), the container may briefly show `unhealthy` before recovering.
- **Ghost 6 requires working SMTP before you can log in.** Ghost 6 sends an email verification code for every new-device login. If SMTP is not configured or the credentials are wrong, the login code never arrives and admin access is blocked. Configure `GHOST_MAIL_*` in `.env` and write the SMTP password to `.secrets/mail_pwd.txt` before the first login. See `.env.example` for Brevo settings.
- **Email deliverability.** Ghost uses the `Mail-From` domain as-is. SPF/DKIM/DMARC for `GHOST_MAIL_FROM` must be configured at your DNS provider, otherwise member emails end up in spam.
- **ActivityPub redirect loop may persist in existing browser sessions.** Browsers can cache redirect chains. If the ActivityPub UI shows redirect errors after a config change, open a fresh private/incognito window to verify — if it works there, clear the browser cache for the domain.
- **ActivityPub startup error on boot.** If Ghost starts before the ActivityPub service is fully ready, a `No webhook secret found` warning appears in the log. With `depends_on: condition: service_healthy` this should not occur in normal operation.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, useful commands
