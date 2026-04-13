# Upstream Reference

## Source

- **Repo:** https://github.com/nextcloud/docker
- **Example path:** `.examples/docker-compose/with-nginx-proxy/mariadb/fpm/`
- **Based on version:** Nextcloud 32 (fpm-alpine)
- **Last checked:** 2026-04-13

## What we use from upstream

| File | Used as | Notes |
|------|---------|-------|
| `nginx.conf` | 1:1 copy | From `.examples/.../insecure/mariadb/fpm/web/nginx.conf` |
| `compose.yaml` | Reference for service topology | Adapted: Traefik, secrets, naming, no proxy containers |
| Environment vars | Reference | Restructured to Blueprint conventions |

## What we changed and why

| Change | Reason |
|--------|--------|
| Removed nginx-proxy + letsencrypt-companion | Replaced by Traefik |
| Docker Secrets for DB + admin passwords | Blueprint standard; Nextcloud supports `_FILE` natively |
| Service names: `app`, `db`, `redis`, `nginx`, `cron` | Blueprint naming convention |
| Traefik labels on nginx | Blueprint routing |
| CalDAV/CardDAV redirect via Traefik middleware | Cleaner than nginx-only redirect, works with Traefik routing |
| `security_opt: no-new-privileges` on all services | Blueprint security baseline |
| MariaDB `healthcheck.sh --connect --innodb_initialized` | Official MariaDB healthcheck script |
| Named volumes | Upstream pattern |

## Fallback: Apache variant

If fpm-alpine + nginx causes issues:

1. Change `APP_TAG=32-apache` in `.env`
2. Remove the `nginx` service from `docker-compose.yml`
3. Move Traefik labels to the `app` service
4. Change loadbalancer port to `80`
5. Remove `nginx/nginx.conf` mount
6. The `cron` service stays unchanged

## Upgrade checklist

When bumping the Nextcloud version:

1. Check [Nextcloud releases](https://nextcloud.com/changelog/) for breaking changes
2. Check [docker repo](https://github.com/nextcloud/docker) for changes to:
   - `nginx.conf` (compare with ours)
   - Supported environment variables
   - Service architecture changes
3. Check [system requirements](https://docs.nextcloud.com/server/stable/admin_manual/installation/system_requirements.html) for MariaDB/PHP version changes
4. Bump `APP_TAG` in `.env`
5. `docker compose pull` → `docker compose up -d`
6. Check `docker compose logs -f app` for migration output
7. Run `docker compose exec -u www-data app php occ status` to verify

## Upstream diff commands

```bash
# Fetch latest upstream nginx.conf
curl -sL https://raw.githubusercontent.com/nextcloud/docker/master/.examples/docker-compose/insecure/mariadb/fpm/web/nginx.conf > /tmp/nc-nginx-upstream.conf
diff /tmp/nc-nginx-upstream.conf apps/nextcloud/nginx/nginx.conf
```
