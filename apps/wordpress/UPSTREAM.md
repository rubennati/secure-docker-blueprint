# Upstream Reference

## Source

- **Image:** https://hub.docker.com/_/wordpress
- **GitHub:** https://github.com/docker-library/wordpress
- **License:** GPL-2.0
- **Decision facts checked:** not yet
- **Origin:** US · Automattic / WordPress Foundation · non-EU
- **Domain:** Publishing, forms and scheduling
- **Role:** Content management system for sites and blogs
- **Last verified:** 2026-11-08 (7.1.4-php8.3-apache) — lab host (VM), IPv4 LAN, at the closed default: the installer run, the administrator logged in before and after `down`/`up`, the REST index answering, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

## What we use

- Official WordPress image (Apache variant, PHP 8.3)
- Official MariaDB 12.3 image
- `WORDPRESS_DB_PASSWORD_FILE` for Docker Secrets support (built into image)

## What we changed and why

| Change | Reason |
|--------|--------|
| `uploads.ini` mounted | Increase PHP upload limit to 64MB (default 2MB blocks plugin uploads) |
| `utf8mb4` charset via command | Explicit full Unicode support for database |
| `MARIADB_AUTO_UPGRADE: "1"` | Auto-upgrade database on MariaDB version bumps |
| `cap_drop: ALL` on database | Security hardening, re-add only needed capabilities |

## Version notes

- Moved to `7.1.4-php8.3-apache` on 2026-11-05 (image built 2026-11-03), not
  run on a host at this tag. WordPress 7.1 raises the database version to
  61833: the first visit to the admin area asks for a database update. The
  image copies WordPress into `/var/www/html` only when that directory is
  empty, so an existing `volumes/wordpress` keeps its core files until
  WordPress's own updater (Dashboard → Updates) moves them; the new tag brings
  PHP, Apache and the image's packages. The 7.0 branch's security release
  7.0.8 exists upstream but is not published as a Docker image, so the pin moves
  to 7.1. Advisories fixed: CVE-2026-87902 (GHSA-7hp8-65ch-5whp, critical,
  unauthenticated path traversal, 7.1.2); the 2026-09-18 release with
  GHSA-qg7r-fjh2-wvx8, GHSA-w57f-v787-qhpf, GHSA-33wf-p63q-w25f and further
  medium and low issues (7.1.1); the 2026-10-29 release with
  GHSA-83c2-c4pc-wmp3 (high), GHSA-4w3m-c66w-69mg, GHSA-p2r6-rwjp-phv3,
  GHSA-9vrg-x932-q57q, GHSA-j255-3x8q-7q7g, GHSA-wjwj-p342-9fq7,
  GHSA-7q86-3j97-744j, GHSA-2p22-wv7j-cvfv, GHSA-mqjw-vvgg-xfvf,
  GHSA-vchg-92fx-636p, GHSA-j3rg-rwgx-7wx7 (7.1.4).
- Moved `mariadb` from `11.4` to `12.3.3`, the current LTS line, on 2026-11-05,
  not run on a host at this tag. Support: WordPress recommends "MariaDB version
  10.11 or greater" (https://wordpress.org/about/requirements/).
  `MARIADB_AUTO_UPGRADE: "1"`, already set in both compose files, runs
  `mariadb-upgrade` at the first start on 12.3 after a backup of the system
  tables; the data directory `./volumes/mysql` is reused. Take the
  `mariadb-dump` before the tag changes: going back to 11.4 is only a restore of
  that dump. Changed on the way (11.8 and 12.x): `innodb_snapshot_isolation` is
  on by default, so a transaction that writes a row another transaction changed
  after its snapshot fails with error 1020 instead of overwriting it; the new
  default collation `utf8mb4_uca1400_ai_ci` does not apply, as the stack sets
  `utf8mb4_unicode_ci` explicitly.

## Upgrade checklist

1. Check [WordPress Docker tags](https://hub.docker.com/_/wordpress/tags) for new PHP/Apache versions
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` then `docker compose up -d`
4. Check WordPress admin → Dashboard → Updates — an existing
   `volumes/wordpress` is not replaced by the image, so core moves only through
   this updater; run the database update when WordPress asks for it
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
