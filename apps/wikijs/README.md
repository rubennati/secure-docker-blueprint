# Wiki.js

A wiki with Markdown, AsciiDoc and visual editors, per-page permissions, live
collaboration and its own authentication modules — all of them in the free
code. Pages and uploaded files live in PostgreSQL; the data volume holds
caches. Wiki.js 3.
Upstream: [requarks/wiki](https://github.com/requarks/wiki).

It sits beside [BookStack](../bookstack/) as the second wiki here. BookStack
organises by shelf, book and chapter; Wiki.js organises by path and keeps an
optional Git mirror of the content.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

```text
Readers and editors → Traefik (TLS) → app :3000
                                        │
                              ┌─────────┴─────────┐
                    volumes/data (cache)   PostgreSQL (pages, users, settings)
```

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p .secrets volumes/data volumes/postgres
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/admin_pwd.txt
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — sign in as ADMIN_EMAIL with .secrets/admin_pwd.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env                      # host name, admin e-mail, database name and user
mkdir -p .secrets volumes/data volumes/postgres
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/admin_pwd.txt
sudo chown -R 1000:1000 volumes/data      # the image runs as uid 1000
docker compose up -d
docker compose logs wikijs-app --follow   # migrations, then the HTTP server starts
```

The first start creates the root administrator from `ADMIN_EMAIL` and
`.secrets/admin_pwd.txt` — there is no setup wizard in 3.x. Sign in, then:

- *Administration → Security*: turn on **Trust X-Forwarded-\* Proxy Headers**,
  so that audit entries and rate limits see the client rather than Traefik.
- In the site's settings in the administration area, set the hostname to
  `APP_TRAEFIK_HOST`; mail is not sent without a fixed hostname.

Coming from 2.x: there is no in-place upgrade. Export on 2.x, import into a
fresh 3.x database — the steps are in [UPSTREAM.md](UPSTREAM.md), "Version
notes".

After setup, decide what the wiki should answer: `APP_TRAEFIK_ACCESS` opens it
at the router, and *Administration → Groups* decides what a guest may read.

## Authentication

Local accounts work out of the box. OpenID Connect, SAML, LDAP and about
fifteen other modules are in the free code and are configured under
*Administration → Auth*; [`core/authentik`](../../core/authentik/) or
[`core/keycloak`](../../core/keycloak/) can be the provider. Two-factor
authentication is available for local accounts.

## Known limits

- **3.x is new.** `3.0.1` (2026-11-01) is the first stable release; this
  stack moved to `3.1.0` without a host run.
- **Outbound calls**: the version check goes to `api.github.com`, icons are
  fetched from `api.iconify.design` on first use. Upstream lists both as
  required outbound endpoints.
- **Extensions cannot be installed from the administration area**: that
  writes under `/wiki/backend`, and the root filesystem is read-only. The
  Puppeteer extension for server-side rendering is already in the image;
  whether its headless Chrome runs under `read_only` has not been checked.
- **The rate limit is not measured.** `.env.example` ships `limit-standard` and
  the editor is a Vue application; no first-load count has been taken behind
  Traefik.
- **Nothing here has run behind Traefik yet.** The
  hardening, the setup and a login were verified on the 2.5 image, the route
  was not, and 3.x has not run at all.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `wikijs-db` · database `wikijs` (schema `wiki`) · user `wikijs` — pages, page history, uploaded files, users, groups, settings |
| **Password** | `.secrets/db_pwd.txt`; `.secrets/admin_pwd.txt` is only read at the first start |
| **State** | `./volumes/data` — if the Git storage module is enabled, the content mirror |
| **Reproducible** | The caches under `./volumes/data/cache` |
| **Quiescing** | Not needed: dump the database rather than copying its files |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/docker/apps/wikijs/volumes/data

postgresql_databases:
  - name: wikijs
    username: wikijs
    # The server's own client, inside its container (FA-03)
    pg_dump_command: docker exec wikijs-db pg_dump
    pg_restore_command: docker exec -i wikijs-db pg_restore
    psql_command: docker exec -i wikijs-db psql
```

Restore: database first, then the data directory, then start the application —
Wiki.js reads its configuration from the database at boot. Keep the ownership
of `volumes/data` at uid 1000.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `3.2.0` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `ghcr.io/requarks/wiki:3.2.0` | 0 · 2 | 0 · 22 | — |
| `postgres:18.6-alpine` | — | — | 1 · 25 |

<!-- findings:end -->

The PostgreSQL image, `postgres`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.
