# Wiki.js

A wiki with a Markdown and a visual editor, per-page permissions, and about
twenty authentication modules — all of them in the free code. Pages live in
PostgreSQL; the data volume holds caches and uploads.
Upstream: [requarks/wiki](https://github.com/requarks/wiki).

It sits beside [BookStack](../bookstack/) as the second wiki here. BookStack
organises by shelf, book and chapter; Wiki.js organises by path and keeps an
optional Git mirror of the content.

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
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — the setup wizard creates the administrator
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env                      # host name, database name and user
mkdir -p .secrets volumes/data volumes/postgres
openssl rand -hex 32 | tr -d '\n' > .secrets/db_pwd.txt
sudo chown -R 1000:1000 volumes/data      # the image runs as uid 1000
docker compose up -d
docker compose logs wikijs-app --follow   # watch for: Browse to … to complete setup!
```

**Then complete the setup immediately.** The first request opens a wizard, and
whoever completes it becomes the administrator — there is no setup password in
front of it. The shipped router is VPN-only for exactly this window.

The wizard asks for the administrator's e-mail and password, the site URL, and
carries a **telemetry checkbox that is ticked by default**. Untick it there, or
turn it off afterwards under *Administration → Utilities → Telemetry*.

After setup, decide what the wiki should answer: `APP_TRAEFIK_ACCESS` opens it
at the router, and *Administration → Groups* decides what a guest may read.

## Authentication

Local accounts work out of the box. OpenID Connect, SAML, LDAP and about
fifteen other modules are in the free code and are configured under
*Administration → Auth*; [`core/authentik`](../../core/authentik/) or
[`core/keycloak`](../../core/keycloak/) can be the provider. Two-factor
authentication is available for local accounts.

## Known limits

- **2.5 is the maintenance line.** It receives security fixes; 3.0 is in beta
  and its release notes say it is not for production. Upstream's documentation
  lists the 2.x upgrade path as coming soon. This stack starts on PostgreSQL —
  the only engine 3.0 supports — so the migration is one less thing to change.
- **Update and locale checks** go to `graph.requarks.io` every 24 hours. There
  is no environment variable for it; the telemetry switch is in the
  administration area.
- **The rate limit is not measured.** The chain ships `sec-2` and the editor is
  a Vue application; no first-load count has been taken behind Traefik.
- **Nothing here has run behind Traefik yet.** The stack is `scaffolded`: the
  hardening, the setup and a login were verified on the image, the route was
  not.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL · container `wikijs-db` · database `wikijs` · user `wikijs` — pages, page history, users, groups, settings |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/data` — uploads staged for the database and, if the Git storage module is enabled, the content mirror |
| **Reproducible** | The caches under `./volumes/data/cache` |
| **Quiescing** | Not needed: dump the database rather than copying its files |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/apps/wikijs/volumes/data

postgresql_databases:
  - name: wikijs
    container: wikijs-db
    username: wikijs
    password: "${WIKIJS_DB_PASSWORD}"
```

Restore: database first, then the data directory, then start the application —
Wiki.js reads its configuration from the database at boot. Keep the ownership
of `volumes/data` at uid 1000.
