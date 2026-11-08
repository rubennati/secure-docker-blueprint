# Upstream Reference

## Source

- **Project:** https://zammad.org
- **GitHub:** https://github.com/zammad/zammad
- **Docker setup:** https://github.com/zammad/zammad-docker-compose
- **Image registry:** https://github.com/zammad/zammad/pkgs/container/zammad
- **Image:** `ghcr.io/zammad/zammad`
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** Germany · Zammad GmbH · EU
- **Domain:** Business operations
- **Role:** Helpdesk and ticket system across mail, chat and phone
- **Pinning:** Zammad publishes no clean semver — only `X.Y.Z-NNNN`; pin the highest
  build of the target release, not the first
- **Last checked:** 2026-08-16

## What we use

- Official `ghcr.io/zammad/zammad` image (same image, different `command:` per service)
- PostgreSQL + Redis + Memcached + Elasticsearch (official Elastic registry) — all required by Zammad
- Docker Secrets for database password (`DB_PWD`)
- `POSTGRESQL_PASS` inline env var (Zammad Rails does not support `_FILE` pattern)
- Traefik labels on the `zammad-nginx` service for HTTPS routing
- YAML anchor `x-shared` / `*zammad-shared` to share image, env, restart, and security across all Zammad services

## What we changed vs. upstream

| Change from upstream | Reason |
|---|---|
| **Traefik labels on `zammad-nginx` instead of exposing ports** | Blueprint routing standard |
| **`app-internal` network without `internal: true`** | railsserver + scheduler need outbound internet for SMTP and webhooks |
| **`security_opt: no-new-privileges:true` on all services** | Baseline hardening |
| **`restart: on-failure` on `init`** | Overrides inherited `unless-stopped`; init is one-shot, must not loop |
| **Switched Elasticsearch from bitnami to `docker.elastic.co`** | bitnami/elasticsearch moved behind a paid registry |
| **`xpack.security.enabled=false` on Elasticsearch** | Official image enables xpack by default; ES is on `app-internal` only |
| **`ZAMMAD_FQDN` + `ZAMMAD_HTTP_TYPE: https`** | Required for correct ActionCable origin and email link URLs |
| **`RAILS_TRUSTED_PROXIES: 0.0.0.0/0`** | Rails must trust Traefik's `X-Forwarded-*` headers |
| **`NGINX_SERVER_SCHEME: https`** | nginx vhost must know scheme for correct redirects |
| **`POSTGRESQL_OPTIONS: ?pool=50`** | Connection pool tuning |

## Architecture

9 services — all use the same `ghcr.io/zammad/zammad` image with different `command:` values:

| Service | Command | Purpose |
|---|---|---|
| `zammad-nginx` | `zammad-nginx` | Web gateway, static assets, reverse-proxy to rails + websocket |
| `railsserver` | `zammad-railsserver` | Rails app (API + core logic) |
| `websocket` | `zammad-websocket` | Agent live updates (ActionCable) |
| `scheduler` | `zammad-scheduler` | Background jobs (email import, SLA checks) |
| `init` | `zammad-init` | One-shot DB migrations on every start |
| `db` | — | PostgreSQL |
| `redis` | — | Background job queue |
| `memcached` | — | Rails fragment cache |
| `elasticsearch` | — | Full-text ticket search |

Minimum RAM: ~4 GB (Elasticsearch grabs 512 MB heap alone).

## Version notes

- memcached moved to `1.6.45` on 2026-10-31, not run at this tag. 1.6.42
  (2026-05-18) is upstream's security release — a timing side channel in SASL
  password authentication and a crash on an oversized auth token, no CVEs
  assigned; 1.6.43 tags three more fixes as security (binary-protocol refcount
  overflows, ascii auth enforcement) and prefixes `lru_crawler metadump` output
  with `OK`, which touches tooling only; 1.6.44 and 1.6.45 fix crashes and
  overflows. No changed default.

- Moved to `7.2.2-0038` on 2026-11-05, not run on a host at this tag — the
  highest 7.2.2 build in the registry that day (built 2026-11-05); 7.2.2 is the
  newest stable release, the only 7.3 tag is `7.3.0-alpha`. Breaking changes
  added to the 7.2 section since 7.2.0 (`BREAKING_CHANGES.md`): verifying a
  signup address no longer signs the user in; the getting-started endpoints
  require `admin.wizard` once the system is set up; the legacy WebSocket login
  is authenticated from the session cookie and `signshow` no longer returns
  `session_id`. The 7.2 note that the request scheme comes only from
  `X-Forwarded-Proto` or `NGINX_SERVER_SCHEME` is covered: this stack sets
  `NGINX_SERVER_SCHEME`. Elasticsearch 8.15 stays the minimum (`ES_TAG` is
  8.17.4). Migrations run at start. No advisory IDs are listed; the 7.2.1 and
  7.2.2 commit logs carry authorization hardening (knowledge base, GraphQL
  attribute assignment, ActionCable sessions, link and activity-stream
  access).
- Moved `postgres` from `16-alpine` to `18.6-alpine` on 2026-11-05, not run on a
  host at this tag. PostgreSQL 18 support: the docs require PostgreSQL 15 or
  newer (https://docs.zammad.org/en/latest/prerequisites/software.html) and
  upstream's CI runs against `postgres:18`. The 18 image keeps its cluster under
  `/var/lib/postgresql/18/docker`; `PGDATA: /var/lib/postgresql/data` in both
  compose files keeps it on the existing mount. A new major does not read the
  old cluster, so existing data moves by dump and restore: before the tag
  changes, `docker compose exec db sh -c 'pg_dumpall -U "$POSTGRES_USER"' >
  dump.sql`; `docker compose down`; move `./volumes/postgres` aside; set the new
  tag; `docker compose up -d db`; `docker compose exec -T db sh -c 'psql -U
  "$POSTGRES_USER" -d postgres' < dump.sql` (errors that the bootstrap role and
  database already exist are expected); then `docker compose up -d`. A return to
  the old major is only a restore of that dump.
- Moved Elasticsearch from `8.17.4` to `9.5.6` on 2026-11-05, not run on a host
  at this tag. Zammad 7.2 and later support Elasticsearch ">= 8.15, < 10"
  (https://docs.zammad.org/en/latest/prerequisites/software.html); upstream's
  zammad-docker-compose ships 9.5.5. Elasticsearch upgrades in place to 9 only
  from 8.19, and the index here is derived data that the backup leaves out, so
  the move drops it instead: `docker compose stop elasticsearch`, empty
  `./volumes/elasticsearch`, set the new tag, `docker compose up -d`, then run
  the searchindex rebuild (Useful commands). Search returns nothing until the
  rebuild finishes. `vm.max_map_count` and `xpack.security.enabled: "false"`
  carry over unchanged.
- Moved `redis` from `7.4-alpine` to `8.10.3-alpine` on 2026-11-05, a new major, not
  run on a host at this tag; the tag follows the 8.10 patch releases (8.10.3,
  2026-10-26). Redis 8 is offered under RSALv2, SSPLv1 or AGPLv3 at the user's
  choice (7.4: RSALv2 or SSPLv1). The image bundles the Query Engine, JSON, time
  series and probabilistic data types as modules, which the image's entrypoint loads
  at start on amd64 and arm64; this stack uses none of them. 8.x reads the 7.4 data
  files in place, but Redis does not load files written by a newer version, so a
  rollback needs the backup of the Redis data. The one potentially breaking change
  upstream lists: `GETRANGE` with an out-of-range negative end returns an empty
  string. Security fixes in the 8.10 line: CVE-2026-62356 (8.10.1, heap write when
  loading a Count-min sketch from an RDB file), queued `MULTI` commands keeping
  access to keys whose ACL permission was revoked (8.10.2), and a cluster-bus
  overflow that needs cluster mode (8.10.3). The 7.4 line still receives fixes
  (7.4.12, 2026-10-26); the move is to the newest stable line, not away from an
  unmaintained one. Zammad requires Redis 7 or newer. The image's entrypoint now
  drops to the `redis` user only when SETUID and SETGID are in the capability
  bounding set, empties that set while dropping, and fixes ownership only of `*.rdb`
  files and `appendonlydir` in `/data`. This service starts as root with Docker's
  default capabilities, so it drops to UID 999 as before; no compose change.
  Sources: https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://docs.zammad.org/en/latest/prerequisites/software.html

## Upgrade checklist

1. Check [Zammad releases](https://github.com/zammad/zammad/releases) — major version upgrades may require sequential stepping (e.g. 6.x → 7.0 before 7.x → 8.0)
2. Back up Postgres:

   ```bash
   docker compose exec db pg_dump -U zammad zammad_production > zammad-backup-$(date +%Y%m%d).sql
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch init run migrations:

   ```bash
   docker compose logs init --follow
   docker compose logs railsserver --follow
   # Watch for: "* Listening on http://[::]:3000"
   ```

6. Verify: create a ticket, search for it, send an email notification

## Useful commands

```bash
# Re-index Elasticsearch (after ES reset or upgrade)
docker compose exec railsserver bundle exec rake searchindex:rebuild

# Run DB migrations manually
docker compose exec railsserver bundle exec rails db:migrate RAILS_ENV=production

# Open Rails console
docker compose exec railsserver bundle exec rails console

# Check all services healthy
docker compose ps
```
