# Upstream Reference

## Source

- **Repo:** https://github.com/nextcloud/docker
- **Image:** https://hub.docker.com/_/nextcloud
- **Docs:** https://docs.nextcloud.com/server/latest/admin_manual/
- **Example path:** `.examples/docker-compose/with-nginx-proxy/mariadb/fpm/`
- **License:** AGPL-3.0
- **Decision facts checked:** 2026-09-21
- **Origin:** Germany · Nextcloud GmbH · EU
- **Domain:** Files, wiki and collaboration
- **Role:** File sync and share with calendars, contacts and collaborative editing
- **Last verified:** 2026-11-09 (35.0.2-fpm-alpine) — lab host (VM), IPv4 LAN, a new installation with Collabora over office.yml and office-collabora.yml behind the closed route: a .docx opened, edited, saved and reopened in the browser, a .docx preview rendered, sign-in and redirects at the public name, the same after `down`/`up`
- **Supported until:** 2027-09-15

Nextcloud publishes a major version every four months and maintains each for one
year. 35 was released 2026-09-16, so it is the newest version carrying a full
support window — [release schedule](https://github.com/nextcloud/server/wiki/Maintenance-and-Release-Schedule).

### The database, and the upgrade that was performed

`DB_TAG=12.3` — the version Nextcloud 35 recommends of 10.11 · 11.4 · 11.8 ·
**12.3** (see Version notes). The step before, from 10.11 to 11.8, was taken by
upgrading a running instance rather than installing fresh, so the documented
path is the one that was taken:

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
| Service names: `app`, `db`, `redis`, `nextcloud-nginx`, `cron` | Blueprint naming convention |
| Traefik labels on `nextcloud-nginx` | Blueprint routing |
| CalDAV/CardDAV redirect left to `nginx.conf` | Upstream's own configuration already issues the documented 301; a Traefik rewrite runs first and suppresses it |
| `security_opt: no-new-privileges` on `db`, `redis`, `nextcloud-nginx` only | The Nextcloud entrypoint needs to chown files as root before dropping to `www-data`; with the flag set, `config.php` ends up root-owned and FPM returns 503 |
| Second network `app-egress` for `app` and `cron` | `app-internal` is `internal: true`, so the database and cache have no route out at all |
| MariaDB `healthcheck.sh --connect --innodb_initialized` | Official MariaDB healthcheck script |
| Named volumes | Upstream pattern |

## Fallback: Apache variant

If fpm-alpine + nginx causes issues:

1. Change `APP_TAG` to the matching `-apache` tag in `.env`
2. Remove the `nextcloud-nginx` service from `docker-compose.yml`
3. Move Traefik labels to the `app` service
4. Change loadbalancer port to `80`
5. Remove `nginx/nginx.conf` mount
6. The `cron` service stays unchanged

## Version notes

- Moved to `34.0.5-fpm-alpine` on 2026-11-05 (released 2026-10-15, image rebuilt
  2026-10-28), not run on a host at this tag. A maintenance release of the 34 line
  with no breaking change, no new requirement and no change to the environment
  variables or `nginx.conf`
  ([v34.0.5](https://github.com/nextcloud-releases/server/releases/tag/v34.0.5)).
  The three CRITICAL findings at `34.0.4` are all in Alpine packages, not in
  Nextcloud: `brotli-libs` 1.2.0 (CVE-2026-111497, fixed in 1.2.1, which this
  image carries) and `libraw` 0.22.1, pulled in by `imagemagick-raw`
  (CVE-2026-20884 and CVE-2026-24450, fixed in 0.22.2). **The two `libraw`
  findings stay**: both `34.0.5-fpm-alpine` and `35.0.2-fpm-alpine` still ship
  `libraw` 0.22.1 although Alpine 3.24 has published 0.22.2
  ([secdb](https://secdb.alpinelinux.org/v3.24/community.json)), so the move
  to Nextcloud 35 below does not remove them either. They clear with the next
  image rebuild. `libraw` is reached only when
  ImageMagick decodes a camera RAW file, for example in a preview. The
  rebuilt `35.0.2-fpm-alpine` image scanned on 2026-11-06 no longer carries
  them.

- The nginx front (`NGINX_TAG`) moved from `1.29-alpine-slim` to
  `1.31-alpine-slim` on 2026-11-05, not run on a host at this tag; it stays on the mainline branch (1.29 was mainline too, 1.30 is the
  stable branch). The "Change:" entries from 1.30.0 to 1.31.8 do not touch this
  configuration: HTTP/2 and HTTP/3 requests carrying `Connection`, `Upgrade`, `TE`
  and similar headers are rejected, requests to backends always carry `:authority`
  or `Host`, HTTP/2 uses RFC 9218 priorities, xslt external entities are off,
  `working_directory` is relative to the prefix, `$request_id` uses SipHash.
  Security fixes in 1.31.0 to 1.31.7: CVE-2026-42926, CVE-2026-42945,
  CVE-2026-42946, CVE-2026-42934, CVE-2026-40460, CVE-2026-40701, CVE-2026-9256,
  CVE-2026-42530, CVE-2026-42055, CVE-2026-48142, CVE-2026-42533, CVE-2026-60005,
  CVE-2026-56434, CVE-2026-90439, CVE-2026-15176, CVE-2026-93479, CVE-2026-95101,
  CVE-2026-97629, CVE-2026-97205.
- The nginx front is pinned to `1.31.8-alpine-slim` on 2026-11-05, not run on a
  host at this tag; until then it followed the floating `1.31-alpine-slim`. The
  image the scan had pulled under that tag carried `brotli-libs` 1.2.0
  (CVE-2026-111497); the 1.31.8 build on Alpine 3.24.3 ships no brotli library
  at all. CRITICAL findings 1 -> 0. No configuration change.
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
  unmaintained one. Nextcloud requires Redis 4.0.0 or later and names no upper
  limit. The image's entrypoint now drops to the `redis` user only when SETUID and
  SETGID are in the capability bounding set, empties that set while dropping, and
  fixes ownership only of `*.rdb` files and `appendonlydir` in `/data`. This service
  starts as root with Docker's default capabilities, so it drops to UID 999 as
  before; no compose change. Sources:
  https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/caching_configuration.html
- Moved to `35.0.2-fpm-alpine` on 2026-11-05 (35.0.2 released 2026-10-15, image
  built 2026-10-23), not run on a host at this tag. One major step, 34 to 35,
  as Nextcloud requires; 35.0.3 exists only as a release candidate. The image
  ships PHP 8.5, as the 34 image did. Nextcloud 35 drops PHP 8.2, MariaDB 10.6
  and MySQL 8.0 and adds MariaDB 12.3 as a supported LTS
  ([upgrade notes](https://docs.nextcloud.com/server/35/admin_manual/release_notes/upgrade_to_35.html),
  [system requirements](https://docs.nextcloud.com/server/35/admin_manual/installation/system_requirements.html)).
  No change to the environment variables or upstream's example `nginx.conf`;
  the image changes since June (PHP 8.5, Alpine 3.24, the Redis connection
  rework, `session.upload_progress.enabled=0`, fewer ImageMagick modules) were
  built into the 34 image too. Office connectors follow the server major: the
  Collabora app `richdocuments` 12.x supports only 35 (11.x only 34), and
  `occ richdocuments:activate-config` keeps `--wopi-url` and `--callback-url`;
  the OnlyOffice connector 10.2.1 supports 33 to 35. The app updater moves them
  during `occ upgrade`. Supported until 2027-09-15
  ([v35.0.2](https://github.com/nextcloud-releases/server/releases/tag/v35.0.2),
  [schedule](https://github.com/nextcloud/server/wiki/Maintenance-and-Release-Schedule)).
- Moved `mariadb` from `11.8` to `12.3.3`, the current LTS line, on 2026-11-05,
  not run on a host at this tag. Nextcloud 35 lists 12.3 as recommended;
  Nextcloud 34 supports it too, so take the two steps apart as README.md
  "Updates" says: first `DB_TAG` with `APP_TAG` still on 34, then `APP_TAG`.
  `MARIADB_AUTO_UPGRADE: "1"`, already set in both compose files, runs
  `mariadb-upgrade` at the first start on 12.3; there is no downgrade, so take
  the archive before the tag changes. The server options in `command:` are all
  still valid in 12.3. `innodb_snapshot_isolation` (on since 11.6) does not
  apply under `READ-COMMITTED`, and the new default collation
  `utf8mb4_uca1400_ai_ci` affects only new databases without an explicit
  collation; Nextcloud sets its own on install.

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
