# Upstream Reference

## Source

- **Repo:** https://github.com/nextcloud/docker
- **Image:** https://hub.docker.com/_/nextcloud
- **Docs:** https://docs.nextcloud.com/server/latest/admin_manual/
- **Example path:** `.examples/docker-compose/with-nginx-proxy/mariadb/fpm/`
- **License:** AGPL-3.0
- **Origin:** Germany · Nextcloud GmbH · EU
- **Based on version:** `34.0.2-fpm-alpine`
- **Last verified:** 2026-07-29 (34.0.2-fpm-alpine)
- **Supported until:** 2027-06-08

Nextcloud publishes a major version every four months and maintains each for one
year. 34 was released 2026-06-09, so it is the newest version carrying a full
support window — [release schedule](https://github.com/nextcloud/server/wiki/Maintenance-and-Release-Schedule).

### The database, and the upgrade that was performed

`DB_TAG=11.8` — the version Nextcloud 34 recommends of 10.11 · 11.4 · **11.8** ·
12.3.

It was reached by upgrading a running instance from 10.11, not by installing
fresh, so the documented path is the one that was taken:

- **Skipping majors is supported** for a standalone server; only Galera requires
  one step at a time.
  [Upgrade paths](https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/upgrading/mariadb-community-server-upgrade-paths)
- **None of this stack's server options were affected.** The removals across the
  11.x line are `innodb_defragment*`, `old_alter_table` and
  `debug_no_thread_alarm`; none are set here. `tx_isolation` was replaced by
  `transaction_isolation`, which is the spelling already in use.
- **The one behavioural change does not apply.** From 11.6,
  `innodb_snapshot_isolation` changes *Repeatable Read* semantics and can raise
  `ERROR 1020`. Nextcloud requires `READ-COMMITTED`, which this stack sets.
- **`MARIADB_AUTO_UPGRADE` does the work.** The entrypoint runs `mariadb-upgrade`
  and writes `system_mysql_backup_*.sql.zst` into the data directory first.
- **There is no downgrade.** Across majors the only way back is a restore, which
  is why the archive is taken before the tag changes.

Result: 10.11.16 → 11.8.8, 131 tables and every row count unchanged, `CHECK
TABLE` clean, `needsDbUpgrade: false`. Procedure in
[README.md](README.md#updates).

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
| Docker Secrets for all six credentials — database, database root, Redis, admin name, admin password, SMTP key | Blueprint standard; Nextcloud supports `_FILE` natively, and Redis reads its own from the secret at startup |
| Unattended install via `NEXTCLOUD_ADMIN_USER_FILE` / `_PASSWORD_FILE` | Repeatable, and no unauthenticated setup form is ever reachable |
| Service names: `app`, `db`, `redis`, `nginx`, `cron` | Blueprint naming convention |
| Traefik labels on nginx | Blueprint routing |
| CalDAV/CardDAV redirect left to `nginx.conf` | Upstream's own configuration already issues the documented 301; a Traefik rewrite runs first and suppresses it |
| `security_opt: no-new-privileges` on `db`, `redis`, `nginx` only | The Nextcloud entrypoint needs to chown files as root before dropping to `www-data`; with the flag set, `config.php` ends up root-owned and FPM returns 503 |
| Second network `app-egress` for `app` and `cron` | `app-internal` is `internal: true`, so the database and cache have no route out at all |
| MariaDB `healthcheck.sh --connect --innodb_initialized` | Official MariaDB healthcheck script |
| Named volumes | Upstream pattern |

## Fallback: Apache variant

If fpm-alpine + nginx causes issues:

1. Change `APP_TAG` to the matching `-apache` tag in `.env`
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

## Post-install steps

See [README.md](README.md#post-install). They are kept in one place so the two
files cannot drift apart.

No admin-overview warning is treated as expected here. The configuration in this
stack reaches 60 passing checks with none outstanding; a warning means something
is genuinely unset.

## Upstream diff commands

```bash
# Fetch latest upstream nginx.conf
curl -sL https://raw.githubusercontent.com/nextcloud/docker/master/.examples/docker-compose/insecure/mariadb/fpm/web/nginx.conf > /tmp/nc-nginx-upstream.conf
diff /tmp/nc-nginx-upstream.conf apps/nextcloud/nginx/nginx.conf
```
