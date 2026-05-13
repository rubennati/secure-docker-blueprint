# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/wordpress
- **GitHub:** https://github.com/docker-library/wordpress
- **License:** GPL-2.0
- **Origin:** US · Automattic / WordPress Foundation · non-EU
- **Based on version:** 6.8.3-php8.3-apache
- **Last checked:** 2026-04-15

## What we use

- Official WordPress image (Apache variant, PHP 8.3)
- Official MariaDB 11.4 image
- `WORDPRESS_DB_PASSWORD_FILE` for Docker Secrets support (built into image)

## What we changed and why

| Change | Reason |
|--------|--------|
| `uploads.ini` mounted | Increase PHP upload limit to 64MB (default 2MB blocks plugin uploads) |
| `utf8mb4` charset via command | Explicit full Unicode support for database |
| `MARIADB_AUTO_UPGRADE: "1"` | Auto-upgrade database on MariaDB version bumps |
| `cap_drop: ALL` on database | Security hardening, re-add only needed capabilities |

## Upgrade checklist

1. Check [WordPress Docker tags](https://hub.docker.com/_/wordpress/tags) for new PHP/Apache versions
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` then `docker compose up -d`
4. Check WordPress admin → Dashboard → Updates
5. Verify site loads + plugin functionality

## Useful commands

```bash
# WordPress shell
docker compose exec app bash

# wp-cli (install plugins, manage users, etc.)
docker compose exec app wp plugin list --allow-root
docker compose exec app wp plugin install <plugin-name> --activate --allow-root
docker compose exec app wp user list --allow-root

# Database backup
docker compose exec db mariadb-dump -u root -p"$(cat .secrets/db_root_pwd.txt)" wordpress > backup.sql

# Database restore
docker compose exec -T db mariadb -u root -p"$(cat .secrets/db_root_pwd.txt)" wordpress < backup.sql
```
