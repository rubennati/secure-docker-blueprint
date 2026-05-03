# Upstream Reference

## Source

- **Project:** https://zammad.org
- **GitHub:** https://github.com/zammad/zammad
- **Registry:** https://github.com/zammad/zammad-docker-compose (Docker setup)
- **Image:** `ghcr.io/zammad/zammad`
- **License:** AGPL-3.0
- **Origin:** Germany · Zammad GmbH · EU
- **Based on version:** `7.0.1`
- **Last checked:** 2026-05-03

## What we use

- Official `ghcr.io/zammad/zammad` image
- PostgreSQL + Redis + Memcached + Elasticsearch (Bitnami) — all required by Zammad
- Docker Secrets for database and secret key
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of nginx reverse proxy** | Blueprint routing standard |
| **`MEMCACHE_SERVERS` / `REDIS_URL` via env** | Blueprint standard for service discovery |
| **Docker Secrets for `DATABASE_URL` password** | Security baseline |
| **`security_opt: no-new-privileges:true`** | Baseline hardening; skipped on Elasticsearch (Bitnami image requirement) |

## Architecture note

Zammad is one of the heavier stacks in the blueprint — it requires 5 services:

| Service | Purpose |
|---|---|
| `app` | Main Rails application |
| `db` | PostgreSQL |
| `redis` | Sessions, ActionCable |
| `memcached` | Fragment caching |
| `elasticsearch` | Full-text search across tickets |

Minimum RAM: ~2 GB for all services combined. Not suitable for low-resource hosts.

## Upgrade checklist

1. Check [Zammad releases](https://github.com/zammad/zammad/releases) — major version upgrades may require sequential stepping (e.g. 6.x → 7.0)
2. Back up:
   ```bash
   docker compose exec app bundle exec rake zammad:backup:create
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch for migration output:
   ```bash
   docker compose logs app --follow
   ```
6. Verify: create a ticket, search for it, send an email notification

## Useful commands

```bash
# Create admin user (first install)
docker compose exec app bundle exec rails r "User.create!(login: 'admin', firstname: 'Admin', lastname: 'User', email: 'admin@example.com', password: 'CHANGE_ME', roles: Role.where(name: 'Administrator'))"

# Run DB migrations manually
docker compose exec app bundle exec rails db:migrate RAILS_ENV=production

# Re-index Elasticsearch
docker compose exec app bundle exec rake searchindex:rebuild
```
