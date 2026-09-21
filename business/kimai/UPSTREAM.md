# Upstream Reference

## Source

- **Project:** https://www.kimai.org
- **GitHub:** https://github.com/kimai/kimai
- **Docker Hub:** https://hub.docker.com/r/kimai/kimai2
- **License:** AGPL-3.0
- **Decision facts checked:** not yet
- **Origin:** Germany · Kevin Papst · EU
- **Domain:** Business operations
- **Role:** Time tracking with reports and invoicing hooks
- **Based on version:** `2.66.0` (see Version / tag notes — the `apache-` prefix is gone)
- **Last checked:** 2026-05-03

## What we use

- Official `kimai/kimai2` image (`apache` variant — includes built-in Apache server)
- MariaDB as backing database
- Docker Secrets for database password
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p` port mapping** | Blueprint routing standard |
| **Docker Secrets for `DATABASE_URL` password** | Security baseline — no credentials in env |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Healthcheck on `/api/ping`** | Proper readiness gate |

## Version / tag notes

- **Upstream dropped the `apache-` tag prefix.** The pin was `apache-2.61.0`, which no
  longer resolves — Docker Hub answers 404, so `docker compose pull` fails on it. The
  newest prefixed tag is `apache-2.57.0` (2026-05-21); everything after that is published
  as a bare semver tag. `2.66.0` and `apache` carry the same digest, so the bare tag is
  the Apache variant this stack expects. Corrected on 2026-09-13.

## Upgrade checklist

1. Check [Kimai releases](https://github.com/kimai/kimai/releases) — the image tag is a bare
   `X.Y.Z` and carries the Apache variant; the older `apache-X.Y.Z` form stopped at `apache-2.57.0`
2. Back up:

   ```bash
   docker compose exec db mysqldump -u ${DB_USER} -p kimai > kimai-$(date +%Y%m%d).sql
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Watch logs for DB migrations:

   ```bash
   docker compose logs app --follow
   ```

6. Verify: log in, create a timesheet entry, generate a report

## Useful commands

```bash
# Reload environment (after .env changes)
docker compose exec app bin/console kimai:reload --env=prod

# Run migrations manually (if automatic migration fails)
docker compose exec app bin/console doctrine:migrations:migrate --env=prod

# Create an admin user
docker compose exec app bin/console kimai:user:create admin admin@example.com ROLE_SUPER_ADMIN
```
