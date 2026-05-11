# Upstream Reference

## Source

- **Project:** https://zammad.org
- **GitHub:** https://github.com/zammad/zammad
- **Docker setup:** https://github.com/zammad/zammad-docker-compose
- **Image registry:** https://github.com/zammad/zammad/pkgs/container/zammad
- **Image:** `ghcr.io/zammad/zammad`
- **License:** AGPL-3.0
- **Origin:** Germany · Zammad GmbH · EU
- **Based on version:** `7.0.1`
- **Last checked:** 2026-05-11

## What we use

- Official `ghcr.io/zammad/zammad` image (same image, different `command:` per service)
- PostgreSQL + Redis + Memcached + Elasticsearch (official Elastic registry) — all required by Zammad
- Docker Secrets for database password (`DB_PWD`)
- `POSTGRESQL_PASS` inline env var (Zammad Rails does not support `_FILE` pattern)
- Traefik labels on the `nginx` service for HTTPS routing
- YAML anchor `x-shared` / `*zammad-shared` to share image, env, restart, and security across all Zammad services

## What we changed vs. upstream

| Change from upstream | Reason |
|---|---|
| **Traefik labels on `nginx` instead of exposing ports** | Blueprint routing standard |
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
| `nginx` | `zammad-nginx` | Web gateway, static assets, reverse-proxy to rails + websocket |
| `railsserver` | `zammad-railsserver` | Rails app (API + core logic) |
| `websocket` | `zammad-websocket` | Agent live updates (ActionCable) |
| `scheduler` | `zammad-scheduler` | Background jobs (email import, SLA checks) |
| `init` | `zammad-init` | One-shot DB migrations on every start |
| `db` | — | PostgreSQL |
| `redis` | — | Background job queue |
| `memcached` | — | Rails fragment cache |
| `elasticsearch` | — | Full-text ticket search |

Minimum RAM: ~4 GB (Elasticsearch grabs 512 MB heap alone).

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
