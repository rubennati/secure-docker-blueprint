# Paperless-ngx

> **Upgrading from 2.x is a major version change and carries breaking changes.** Verify the migration first.

Self-hosted document archive: scan → OCR → searchable PDF archive. Optimised for paperless offices with a "consume folder" + mobile scan workflow.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

Five services:

| Service | Image | Purpose |
|---------|-------|---------|
| `paperless-app` | `ghcr.io/paperless-ngx/paperless-ngx` | Django web app + Celery workers + consumer |
| `db` | `postgres:18.6` | Primary data store (documents, tags, correspondents, users) |
| `redis` | `redis:8.10.3-alpine` | Celery broker + worker heartbeat |
| `gotenberg` | `gotenberg/gotenberg` | Converts HTML/Office documents to PDF |
| `tika` | `apache/tika` | Text extraction from scanned PDFs, Office files, emails |

Paperless-ngx drives OCR, classification, and archiving itself; it delegates format conversion to Gotenberg and text extraction to Tika.

### Optional: SSO via Authentik

`sso.yml` overlays Authentik OpenID Connect on top of the standard compose. When active, regular username/password login is disabled and every request redirects to Authentik.

Enable via `COMPOSE_FILE` in `.env`:

```env
COMPOSE_FILE=docker-compose.yml,sso.yml
```

## Try it locally

Runs on `http://localhost:8000` without Traefik, DNS or a certificate.

```bash
# Local settings; the secrets ship empty, so fill the ones this stack needs
cp .env.local.example .env.local
printf 'DB_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env.local
printf 'SECRET_KEY=%s\n' "$(openssl rand -base64 48 | tr -d '\n')" >> .env.local
printf 'ADMIN_PASSWORD=%s\n' "$(openssl rand -base64 24 | tr -d '\n')" >> .env.local

mkdir -p volumes/local/redis
sudo chown 999:1000 volumes/local/redis
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8000
docker compose -f docker-compose.local.yml --env-file .env.local down
```

`.env.local` holds plain values, not Docker Secrets — local only.

## Setup

```bash
# 1. Create .env
cp .env.example .env
# Edit: APP_TRAEFIK_HOST, PAPERLESS_OCR_LANGUAGE, USERMAP_UID/GID, TZ
# List the stack's edge network, paperless-edge, in core/traefik/.env EDGE_NETWORKS,
# then render and restart Traefik (core/traefik/docs/edge-networks.md) — otherwise
# step 4 stops on "network paperless-edge declared as external, but could not be found"

# 2. Generate secrets
mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 48 | tr -d '\n' > .secrets/secret_key.txt
: > .secrets/email_pwd.txt   # compose mounts it; empty while e-mail is off (SMTP below)

# 3. Prepare volume ownership (Paperless drops to USERMAP_UID/GID)
mkdir -p volumes/{data,media,consume,export,postgres,redis}
sudo chown -R 1000:1000 volumes/data volumes/media volumes/consume volumes/export
# Redis runs as the image's own user and cannot fix ownership itself
sudo chown 999:1000 volumes/redis

# 4. Start
docker compose up -d

# 5. Wait for migrations + healthcheck
docker compose logs paperless-app --follow
# Look for: "Listening at: http://:::8000"

# 6. Create the first admin user — the image's wrapper, which carries the
#    secrets the container read at start; `python manage.py` under exec does not
#    see them and stops on PAPERLESS_SECRET_KEY
docker compose exec paperless-app createsuperuser

# 7. Open the UI
# https://<APP_TRAEFIK_HOST>
```

### OCR languages

Two separate variables control OCR language support:

| Variable | Purpose | Example |
|----------|---------|---------|
| `PAPERLESS_OCR_LANGUAGE` | Default language used when auto-detection fails | `deu` |
| `PAPERLESS_OCR_LANGUAGES` | Language packs to install (**space-separated**) | `deu eng ron` |

`PAPERLESS_OCR_LANGUAGES` must include every language you want to OCR. The image reads it as a
space-separated list: a comma-separated one is a single package name — with `deu,eng` the start
log said `Skipped tesseract-ocr-deu,eng: Package not found!`. German, English, French, Italian and Spanish
ship in the image; any other pack is installed with apt **each time the container is created**,
which needs outbound access from the stack's edge network — without it the pack is skipped, the
container still turns healthy, and the language is missing. `PAPERLESS_OCR_LANGUAGE`
sets which language Paperless picks first when the document has no language metadata; several are
joined with `+` (`deu+eng`).

Common three-letter codes (ISO 639-2):

| Language | Code |
|----------|------|
| German | `deu` |
| English | `eng` |
| French | `fra` |
| Spanish | `spa` |
| Italian | `ita` |
| Romanian | `ron` |

Full list: [Tesseract language data](https://github.com/tesseract-ocr/tessdata)

The stack ships `access-vpn`, `limit-standard` and `headers-standard` — Paperless typically holds personal documents, so VPN-only is the right baseline. Switch to `access-public` only if you intentionally want it on the open internet (and then consider adding SSO via `sso.yml`).

### SMTP (optional)

Used for: password reset emails, workflow notifications, sending documents by mail.

E-mail ships **off**: Paperless treats it as off only while `PAPERLESS_EMAIL_HOST=localhost` and
`PAPERLESS_EMAIL_HOST_USER` is empty; it then reports `email_enabled: false` to the UI and the login
page offers no password reset. An empty host does not turn it off — the password reset answers 500,
as it does with a relay that cannot be reached; a reset posted directly with e-mail off answers 500
too.

```bash
echo -n 'your-smtp-password' > .secrets/email_pwd.txt
```

Set in `.env`:

```env
PAPERLESS_EMAIL_HOST=smtp.example.com
PAPERLESS_EMAIL_PORT=587
PAPERLESS_EMAIL_HOST_USER=paperless@example.com
PAPERLESS_EMAIL_USE_TLS=true
PAPERLESS_EMAIL_FROM=Paperless <paperless@example.com>
```

For implicit TLS on port 465: `PAPERLESS_EMAIL_PORT=465`, `PAPERLESS_EMAIL_USE_TLS=false` and
`PAPERLESS_EMAIL_USE_SSL=true` — with `USE_TLS=false` alone the connection to 465 is closed
(measured with the image's SMTP backend).

The application container reaches a relay on the internet through its edge network; Postgres,
Redis, Gotenberg and Tika have no outbound route. A sink such as `apps/greenmail` or
`apps/mailpit` sits on `proxy-public` and is reachable only with `TRAEFIK_NETWORK=proxy-public`
(their READMEs).

Then restart:

```bash
docker compose up -d --force-recreate paperless-app
```

### Enabling SSO (optional)

Authentik must be running with an OAuth2/OIDC provider configured for Paperless.

1. **In Authentik:**
   - Create an Application (slug `paperless`)
   - Create an OAuth2/OIDC Provider bound to that application
   - Redirect URI: `https://<APP_TRAEFIK_HOST>/accounts/oidc/<SSO_PROVIDER_ID>/login/callback/`
   - Copy the Client ID + Client Secret

2. **In Paperless `.env`:**

   ```text
   COMPOSE_FILE=docker-compose.yml,sso.yml
   SSO_PROVIDER_ID=authentik
   SSO_PROVIDER_NAME=Single Sign-On
   SSO_CLIENT_ID=<from authentik>
   SSO_CLIENT_SECRET=<from authentik>
   SSO_SERVER_URL=https://auth.example.com/application/o/paperless/.well-known/openid-configuration
   ```

3. `docker compose up -d` — regular login is now disabled and the login page redirects to Authentik.

Check the redirect once after enabling `sso.yml`: the login page should send you to Authentik, and a user who signs in there lands in Paperless-ngx.

## Verify

```bash
docker compose ps        # four services healthy; tika has no healthcheck and shows "running"
docker compose exec paperless-app /command/with-contenv python3 manage.py check   # no issues
```

Drop a PDF into `./volumes/consume/` and watch the logs — it should be consumed, OCR'd, and appear in the UI within a few seconds.

## Security Model

- Database, Redis, Gotenberg, and Tika are on `app-internal` (`internal: true`) — none reachable from outside
- `db` credentials, `SECRET_KEY` → Docker Secrets (files under `./.secrets/`)
- Gotenberg runs with JavaScript disabled (`--chromium-disable-javascript`) and only allowed to read from `/tmp` — defence against malicious uploaded HTML
- Redis runs `read_only: true` with tmpfs — no writable root filesystem
- `no-new-privileges:true` on every service
- Default access is VPN-only (`access-vpn`)
- **Documents from the consume folder have no owner**, and a document without an owner is visible to
  every user holding the view permission; one uploaded through the UI or API belongs to the uploader
  and stays hidden from other users until shared. Assign an owner with a workflow
  if the consume folder feeds more than one person.
- The token endpoint allows 5 requests a minute from one client address (`PAPERLESS_TOKEN_THROTTLE_RATE`);
  beyond that it answers 429, the right password included.
- Failed logins are logged with Traefik's address on the edge network, not the client's
  (`PAPERLESS_TRUSTED_PROXIES` is not set). The lab's probe has a loopback address, so what a real
  client's address would look like in the log was not measured.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `paperless-db` · database `paperless` · user `paperless_user` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` (database) · **`./volumes/media`** — the archived documents themselves |
| **Reproducible** | `./volumes/data` (search index — rebuildable) · `./volumes/redis` (queue) · `./volumes/consume` (inbox, transient) · `./volumes/export` |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: paperless
      username: paperless_user
      # The server's own client, inside its container (FA-03)
      pg_dump_command: docker exec paperless-db pg_dump
      pg_restore_command: docker exec -i paperless-db pg_restore
      psql_command: docker exec -i paperless-db psql
```

**The dump runs with the server's own client, inside `paperless-db`** (FA-03): no
PostgreSQL client on the host, no password, and the client's version follows `DB_TAG`
by itself. The database container has to be running for the backup, and its `memory`
and `pids` limits apply to `pg_dump` as well.

**`volumes/media` is the archive.** The database holds tags, correspondents and
the text extracted from each document; the documents themselves are files. Losing
media means losing the papers, and no amount of database is a substitute.

`.secrets/secret_key.txt` is required for existing sessions and tokens to remain
valid.

Paperless also has its own `document_exporter`, which writes documents plus
metadata into a single self-describing tree. That is the more portable restore
path — and the one to use when moving between major versions rather than
restoring in place.

**Restore order:** database first, then media, then the app. Without
`volumes/data/index` the app rebuilt the search index during its start, and search
answered as soon as the container was healthy.

The `document_exporter` writes mail-account passwords and other sensitive fields in
plain text unless it is given `--passphrase`; it says so in its output.

## Known Issues

- **`USERMAP_UID` / `USERMAP_GID` must match the host owner of `./volumes/`.** Wrong UID = permission errors on consume/media. The default (1000:1000) works for most Debian/Ubuntu users.
- **`user:` cannot be set on the app service.** Paperless uses s6-overlay which requires root for `/run` setup before dropping privileges. Adding `user:` breaks startup.
- **`SSO_CLIENT_SECRET` lives in `.env`, not in `.secrets/`.** `sso.yml` builds a JSON configuration string (`PAPERLESS_SOCIALACCOUNT_PROVIDERS`) and Paperless doesn't support `_FILE` for values embedded inside a JSON env var. This is a Paperless limitation, not a blueprint choice.
- **First OCR of a large document is slow.** Tesseract loads language data lazily; subsequent OCR on the same language is cached and fast.
- **A mail account's connection test answers 500** instead of a message when the IMAP server cannot be reached — unknown host, closed port, TLS on a plain port (3.1.3).
- **Notes are not found by full-text search** — a note's text gave no hit, also after `document_index reindex` (3.1.3, two instances).
- **Gotenberg's PID limit bounds Chromium.** At 100 PIDs Chromium could not start: every e-mail and HTML document failed with 503 while both health endpoints answered 200. 300 is the measured peak (149) with room.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `3.4.2` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `apache/tika:3.3.3.0` | 0 · 1 | 1 · 3 | 0 · 4 |
| `ghcr.io/paperless-ngx/paperless-ngx:3.4.2` | 0 · 3 | 0 · 8 | — |
| `gotenberg/gotenberg:8.40.0` | 0 · 2 | — | — |
| `postgres:18.6` | 0 · 2 | — | 1 · 25 |
| `redis:8.10.3-alpine` | — | — | — |

<!-- findings:end -->

The pinned Tika image, `apache/tika:3.3.3.0`, ships with 1 CRITICAL vulnerability that has a published fix, in Apache CXF (CVE-2026-49875, external entity resolution). The fix is only in Tika 4, which Paperless-ngx does not yet support, so Tika stays on the newest 3.x release.

**Risk:** Tika sits on the internal network with no outbound route, which blocks the out-of-band data leak this flaw relies on. Move to Tika 4 once Paperless-ngx supports it.

The PostgreSQL image, `postgres`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.

## Details

- [UPSTREAM.md](UPSTREAM.md) — source, upgrade checklist, consume/classify tuning
- [CONFIG.md](CONFIG.md) — full configuration reference bucketed by mandatory / nice-to-have / use-case-dependent, plus backup-lifecycle and management-command cheatsheet
- [sso.yml](sso.yml) — Authentik OIDC overlay
