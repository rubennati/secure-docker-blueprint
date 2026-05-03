# Upstream Reference

## Source

- **Project:** https://www.kimai.org
- **GitHub:** https://github.com/kimai/kimai
- **Docker Hub:** https://hub.docker.com/r/kimai/kimai2
- **License:** AGPL-3.0
- **Based on version:** `apache-2.56.0`
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

## Upgrade checklist

1. Check [Kimai releases](https://github.com/kimai/kimai/releases) — tag format is `apache-X.Y.Z`
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
