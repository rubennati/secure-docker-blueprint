# Restore

A backup that has never been restored is a hypothesis. This document is both the **rehearsal** — run it on a schedule, on a scratch target — and the **procedure** for the day it is real.

Read it once now, while nothing is broken. The worst time to learn that the key is missing is during an outage.

---

## Before you start

You need three things. If any is missing, stop and fix that first — no restore is possible without all three.

| | Check |
|---|---|
| Repository access | `sudo borgmatic list` returns archives |
| Passphrase | `/root/.borg-passphrase`, or your copy of it |
| Repository key | the file from `borg key export`, if this host is gone |

---

## Rehearsal — quarterly, ~30 minutes

Restore into a scratch location. **Never rehearse into the live deployment** — restore is destructive and the rehearsal is not worth the outage.

### 1 · Is there anything to restore?

```bash
sudo borgmatic list
sudo borgmatic info
```

Look at the date of the newest archive. If it is older than your backup interval, the schedule has been failing silently — that is a finding, and it is the most common one.

### 2 · Files come back

```bash
mkdir -p /tmp/restore-test && cd /tmp/restore-test
sudo borgmatic extract --archive latest --path srv/docker/apps/myapp --destination .
```

Paths inside an archive are **relative** — no leading slash. Confirm the files are there, non-empty, and that a file you recognise has the content you expect. A directory tree of correctly-named empty files is a failure mode, not a success.

Compare a file you can check against the live one rather than eyeballing it:

```bash
docker exec -u www-data myapp-app sha256sum /var/www/html/config/config.php
sudo sha256sum /tmp/restore-test/<the same path from the archive>
```

A difference is not automatically a failure — see [what a quiesced backup looks like](#a-restored-instance-may-come-back-in-maintenance-mode) — but it is always worth explaining.

### 3 · A database comes back

Restore into a throwaway database, not the live one. `--container` is the safest override: it names the target explicitly, so there is no chance of the configured one being used.

PostgreSQL — the throwaway server runs the **same major version** as the live one,
and the restore runs the `pg_restore_command` and `psql_command` of the database's
entry, so the client that wrote the dump restores it ([README](README.md#postgresql-the-clients-major-version-is-the-servers)).
Check the entry first; an entry without them uses the newest client on the `PATH`:

```bash
sudo grep -A12 'name: myapp' /etc/borgmatic/config.yaml | grep -E '_command|container'
docker exec myapp-db postgres --version     # the live server's major, e.g. 16

PW=$(openssl rand -hex 16)
docker run -d --name restore-test -e POSTGRES_PASSWORD="$PW" postgres:16
docker exec restore-test createdb -U postgres myapp

sudo borgmatic restore --archive latest --database myapp \
  --container restore-test --username postgres --password "$PW"
```

With a client of another major the restore can stop on a statement the server does
not know — measured with client 17 against server 16 (`SET transaction_timeout = 0`,
the Paperless entries in the [rehearsal log](#rehearsal-log)). A rehearsal that fails
there is the finding: the backup it tested would fail the same way on the day.

MariaDB — no published port needed, and the database has to exist first:

```bash
PW=$(openssl rand -hex 16)
docker run -d --name restore-test -e MARIADB_ROOT_PASSWORD="$PW" \
  --tmpfs /var/lib/mysql:rw mariadb:11.8
docker exec restore-test mariadb -uroot -p"$PW" -e 'CREATE DATABASE myapp;'

sudo borgmatic restore --archive latest --database myapp \
  --container restore-test --username root --password "$PW"
```

Then verify the data, not just the exit code:

```bash
docker exec restore-test mariadb -uroot -p"$PW" myapp -e "
  SELECT COUNT(*) AS tables_restored FROM information_schema.tables
    WHERE table_schema='myapp';
  SELECT COUNT(*) FROM <a_real_table>;"
```

A row count you can sanity-check is the evidence. "The command exited 0" is not.

### 4 · Clean up

```bash
docker rm -f restore-test
rm -rf /tmp/restore-test
```

### A restored instance may come back in maintenance mode

If the backup quiesces the application through a command hook, the flag is part
of what gets captured. For Nextcloud that flag lives in `config.php`, so the
restored file differs from the live one by exactly one line:

```text
< 'maintenance' => false,
> 'maintenance' => true,
```

That is the backup working, not a fault — but a restored instance will refuse to
serve until it is cleared:

```bash
docker exec -u www-data myapp-app php occ maintenance:mode --off
```

Arguably the safer default: nothing is served before someone has looked at it.
Know it in advance, or the first restore looks like a broken one.

### 5 · Write it down

Record the date, the archive used, what was restored, and anything that surprised you. An undocumented rehearsal cannot be pointed at later — and the surprises are the whole value.

---

## Just looking — browse an archive as a filesystem

"Where are my backups?" has an unsatisfying answer if you go looking on disk: a
Borg repository is not a folder of copies. It holds `config`, `data/`, an index
and a nonce — encrypted, deduplicated chunks, owned by root and unreadable
without the passphrase. There is nothing there to recognise.

Mount one instead and it becomes an ordinary directory tree:

```bash
sudo mkdir -p /mnt/borg
sudo borgmatic mount --mount-point /mnt/borg
ls /mnt/borg                      # one directory per archive
ls /mnt/borg/<archive>            # the filesystem as it was
sudo umount /mnt/borg
```

Database dumps appear under `borgmatic/` at the top of each archive, the rest
mirrors the original paths.

**`borg mount` needs FUSE**, which the Debian package does not pull in:

```text
Runtime Error: borg mount not available: no FUSE support
```

```bash
sudo apt install python3-llfuse
```

Without it, everything else still works — `list` and `extract` do not need
FUSE. Only browsing does.

## Real restore — single file or directory

```bash
sudo borgmatic list                                   # pick an archive
sudo borgmatic list --archive <name> | grep <file>    # find the path
sudo borgmatic extract --archive <name> --path <relative/path> --destination /tmp/recovered
```

Inspect it in `/tmp/recovered`, then move it into place yourself. Extracting straight over live data removes the chance to compare first.

## Real restore — a database

> **Destructive.** This replaces the live database. Take a dump of the current state first, even if you believe it is broken — a broken state you can inspect later beats one you destroyed.

```bash
# 1 · Safety copy of what is there now
docker exec myapp-db pg_dump -U myapp myapp > /root/pre-restore-$(date +%Y%m%d-%H%M).sql

# 2 · Stop the application, leave the database running
cd /srv/docker/apps/myapp && docker compose stop app

# 3 · Restore — PostgreSQL with the programs the entry names, of the server's major
sudo borgmatic restore --archive latest --database myapp

# 4 · Start and verify
docker compose start app
docker compose logs app --tail 50
```

The database must already exist — Borgmatic will not create it.

## Real restore — whole stack onto a new host

1. Install Docker and borgmatic on the new host.
2. Place the passphrase at `/root/.borg-passphrase` and, if the repository key is not reachable, import it: `borg key import <repo> /path/to/exported-key.txt`
3. Extract the deployment **and the named volumes**:

   ```bash
   sudo borgmatic extract --archive latest \
     --path srv/docker --path var/lib/docker/volumes --destination /
   ```

   Both paths, not just the first. `srv/docker` carries the compose files, `.env`, `.secrets/` and every bind mount — which is most stacks. Four stacks keep their file data in Docker named volumes instead: `apps/nextcloud` (`nextcloud_html`), `business/invoiceninja` (`app_public`, `app_storage`), `business/vikunja` (`vikunja_files`) and `business/openproject` (`op_assets`). Those live under `/var/lib/docker/volumes`, `config.yaml.example` backs them up, and extracting only `srv/docker` leaves them in the archive. The stacks then start, answer, and are missing their files.

   Confirm your Docker root first — rootless and custom `data-root` setups put it elsewhere:

   ```bash
   docker info --format '{{.DockerRootDir}}'
   ```

4. Check `.env` and `.secrets/` came through — these are what make the stack runnable, and they are the reason the archive is encrypted.
5. Start the databases only, restore each one, then start the applications.
6. Repoint DNS once the stack answers locally.

## If the original host is gone

Everything above still works from any machine with Borg, the passphrase and the exported key:

```bash
borg key import ssh://backup-user@backup.example.com:22/./borg/myhost /path/to/exported-key.txt
borg list ssh://backup-user@backup.example.com:22/./borg/myhost
```

This is exactly why the key copy does not live on the host being backed up.

## If archives are missing after a compromise

With append-only enforced on the target, deleted archives are usually recoverable — the data was never physically removed. **Stop and read [Borg's documented procedure](https://borgbackup.readthedocs.io/en/stable/usage/notes.html) before touching anything**, because the wrong move makes it permanent:

- **Do not run `borg compact`.** Compaction is what actually frees the deleted data. Until it runs, recovery is possible.
- **Copy the repository directory first** (`cp -al` is enough), then work on the copy.
- Use the repository's `transactions` log to pick a transaction from before the compromise, then remove the segment files written after it.

If `borg compact` has already run since the deletion, the data is gone. That is why the monitoring hook matters: it is the difference between noticing in hours and noticing after compaction.

---

## Rehearsal log

The `Stack` column carries the repository key, which is what
`scripts/ci/lifecycle-report.py` reads to show *with restore* beside the stack's
last test date.

| Date | Stack | Archive | Scope | Result | Notes |
|---|---|---|---|---|---|
| 2026-07-29 | `apps/nextcloud` | first archive of a Nextcloud stack — 27,840 files, 912 MB → 440 MB deduplicated, 22 s | `config.php` from the archive against the live file; full MariaDB dump into a throwaway container | Pass | 131 tables, the expected account, 114 rows in the file index. The extracted `config.php` differed by one line, `'maintenance' => true` — the quiescing hook, captured as intended. Three things had to be fixed first: the packaged borgmatic was too old, `mariadb-dump` was missing on the host, and the distribution client demanded TLS the pinned server does not offer. |
| 2026-11-02 | `apps/heimdall` | first archive of a Heimdall stack on the lab host — 35 files, 196 kB → 35 kB deduplicated, borgmatic 2.2.0, borg 1.4.0, a local throwaway repository | the stack directory extracted and compared with the live one (31 files, 16 directories, `config/www/.env` byte-identical); the SQLite dump restored into a scratch path through a second configuration; a throwaway container started from the restored data | Pass | 14 tables and the test item created through the UI before the backup; the restored instance listed it under `/items`, as the live one does. `borgmatic restore` has no path override for SQLite — it writes to the configured path, so the scratch target needs its own configuration. On an `--internal` network the restored instance answered 500: its first request fetches the app list from `appslist.heimdall.site`; with egress it answered 200. `host-files.sh install-commands` printed `install` without `-D`, which fails while `/etc/borgmatic` does not exist — corrected. |
| 2026-11-02 | `apps/vaultwarden` | archive of a Vaultwarden stack with its MariaDB dump on the lab host — 314 files, 171 MB → 3.4 MB deduplicated, a local throwaway repository | `volumes/data` extracted (`rsa_key.pem` byte-identical); the dump restored into a throwaway `mariadb:11.4` with `--container`; a throwaway Vaultwarden started from both | Pass | 29 tables, the test account and its one item, as live. The restored instance was healthy, and the account logged in through the client API's password grant and synced its item — the database and `rsa_key.*` from the same archive, as the stack's README requires. The first run stopped on `mariadb-dump` missing on the host, a prerequisite the README names; the example's Healthchecks ping, a placeholder, was removed for the lab. |
| 2026-11-02 | `apps/seafile` | archive of a Seafile CE 13.0.20 stack with its three MariaDB dumps on the lab host — 150 files, 328 MB, a local throwaway repository, `volumes/mysql` excluded so the dumps carry the databases | the stack directory extracted (the block store identical to the live one); `ccnet_db`, `seafile_db` and `seahub_db` restored into a fresh `mariadb:10.11` through `restore_container`; a throwaway Seafile started from both, without Traefik | Pass | 13, 48 and 127 tables. The restored instance listed the test library with the same six files; four of them downloaded with checksums identical to the live ones (300 MB the largest), the sync API answered `commit/HEAD`, and `seaf-fsck` finished clean. It first failed every request with `Access denied for user 'seafile'`: a dump holds the databases, not the account — the README now creates it before the app starts. |
| 2026-11-02 | `apps/seafile-pro` | archive of a Seafile Pro 13.0.21 stack with its three MariaDB dumps on the lab host — 150 files, 325 MB, a local throwaway repository, `volumes/mysql` and the SeaSearch index excluded | the stack directory extracted (the block store identical to the live one); the three databases restored into a fresh `mariadb:10.11` through `restore_container`; a throwaway Seafile Pro started from both, without Traefik, SeaSearch or ClamAV | Pass | 13, 48 and 127 tables; the same eight files listed, four downloaded with identical checksums, the sync API answered and `seaf-fsck` finished clean. The README's `printf '%s' "$SEAFILE_MYSQL_DB_PASSWORD"` wrote an empty credential file — the variable lives in `.env`, not the shell — and the account had to be created as for CE; both corrected in the README. |
| 2026-11-02 | `apps/paperless-ngx` | archive of a Paperless-ngx 3.1.3 stack with its Postgres 16.14 dump on the lab host — 113 files, 2 MB, a local throwaway repository, `volumes/postgres` excluded so the dump carries the database | the README's `postgresql_databases` entry: the dump restored into a fresh `postgres:16.14` through `restore_container`; then the same with the server's own client | Fail | The shipped path failed: the host's `pg_dump` 17 (Debian 13's `postgresql-client`) writes `SET transaction_timeout = 0`, which server 16 rejects, and `pg_restore --exit-on-error` stopped — open for a decision, as it holds for every Postgres stack whose server is older than the host's client. With `pg_dump_command` and `pg_restore_command` through `docker exec` — a lab variant, not in the repository — the data came back: 74 tables, the 42 media files identical by SHA-256, and a throwaway instance whose documents, metadata, users, checksums and search hits matched the live ones; `document_sanity_checker` clean. |
| 2026-11-02 | `apps/paperless-ngx` | archive of the same stack after the correction — 132 files, 3.45 MB; the dump written by `pg_dump` 16.15 from server 16.14 | the README's corrected `postgresql_databases` entry, which names the PostgreSQL 16 client (`postgresql-client-16` from the PostgreSQL project's repository, beside Debian's 17); the stack directory extracted; the dump restored with `--container` into the throwaway instance's `postgres:16.14`, as section 3 describes; a throwaway Paperless started from both, without Traefik | Pass | `pg_restore` 16 ran with `--exit-on-error` and exited 0, no error in its output. All 74 tables hold the same row counts as the live database; the 48 media files are identical by SHA-256; the restored instance started healthy with no migration to apply, and its 15 documents matched the live ones in title, owner, tags, correspondent, type, custom field, note, both checksums and content, as did the six users and every search hit; `document_sanity_checker` reported no issues. The failed rehearsal above stays: it is why the entry names the client. |
| 2026-11-03 | `apps/tymeslot` | archive of a Tymeslot 1.15.1 stack with its PostgreSQL 17.11 dump on the lab host, `volumes/postgres` excluded, a local throwaway repository | the README's `postgresql_databases` entry, verbatim (the host's client 17 matches the server); the stack directory extracted into a throwaway instance on the same edge network; the dump restored with `--container` into its database | Pass | `pg_restore` exited 0. 39 tables with the live row counts (233 rows — one verified account, a small data set); the throwaway instance started healthy with the restored secrets and the account logged in. |
| 2026-11-03 | `business/invoiceninja` | archive of an Invoice Ninja 5.13.52 stack with its MySQL 8.4 dump and the `app_storage` volume on the lab host | the README's `source_directories` and `mysql_databases` entries (`/srv/blueprint` read as this host's `/srv/docker`); the dump restored with `--container` into a throwaway instance's MySQL; the volume's 513 files copied into the throwaway's volume | Pass | 80 tables, 1,493 rows identical. The throwaway instance answered the API with the same client, products, invoice (325.50, balance 225.50 after the payment) and payment, and rendered the invoice PDF. `mysqldump` warned that the user lacks `PROCESS` for tablespaces; the dump was complete. |
| 2026-11-03 | `apps/easyappointments` | archive of an Easy!Appointments 1.6.1 stack with its MariaDB 11.4 dump on the lab host, `volumes/mysql` excluded | the README's `mariadb_databases` entry; the dump restored with `--container` into a throwaway instance | Pass | 14 tables, 94 rows identical; the throwaway's API returned the same customers and appointment, and its backend login worked. |
| 2026-11-03 | `apps/monicahq` | archive of a Monica 4.1.2 stack with its MariaDB 11.4 dump on the lab host, `volumes/mysql` excluded | the README's `mariadb_databases` entry; the dump restored with `--container` into a throwaway instance | Pass | 95 tables, 863 rows identical; the throwaway instance logged the account in with the restored `APP_KEY` and listed its contact. |
| 2026-11-03 | `business/kimai` | archive of a Kimai 2.66.0 stack with its MariaDB 11.4 dump on the lab host, `volumes/mysql` excluded | the README's `mariadb_databases` entry; the dump restored with `--container` into a throwaway instance | Pass | 35 tables, 121 rows identical; the throwaway's API returned the same customer, project, activity and timesheet. |
| 2026-11-03 | `business/listmonk` | archive of a listmonk v6.2.0 stack with its PostgreSQL 16 dump on the lab host, `volumes/postgres` excluded | the README's `postgresql_databases` entry, verbatim, with the host's client 17; then the same with the PostgreSQL 16 client named in the entry, a lab variant | Fail | The shipped entry: `pg_restore` 17 stopped at `transaction_timeout`, the client mismatch recorded for `apps/paperless-ngx`. With client 16 the restore exited 0, 16 tables and 94 rows were identical, and the throwaway instance showed the same subscribers, lists and campaigns. |
| 2026-11-03 | `apps/immich` | archive of an Immich v3.2.0 stack with its PostgreSQL 14 (vectorchord) dump on the lab host | the README's `postgresql_databases` entry with the host's client 17; then the README's Restore pipeline with a plain `pg_dump` taken with the app stopped, into a fresh throwaway database, and the library copied | Fail | The entry: `pg_restore` 17 stopped at `transaction_timeout`. The pipeline with upstream's `pg_dumpall --clean` dump exited 3 (`DROP DATABASE cannot run inside a transaction block`); with the plain `pg_dump`, now named in the README, it exited 0: 71 tables, 232,793 rows identical, and the throwaway instance served the same assets with byte-identical originals and thumbnails. |
| 2026-11-03 | `apps/n8n` | archive of an n8n 2.41.7 stack on the lab host, taken with the container stopped as the README asks | the README's `source_directories`-only backup; the stack directory extracted into a throwaway instance | Pass | The throwaway instance logged the owner in, held the workflow, answered its webhook (`{"sum":42}`) and decrypted the stored credential with the restored key. |
| 2026-11-03 | `apps/ghost` | archive of a Ghost 6.63.0 stack with its MySQL 8.4 dump on the lab host, `volumes/mysql` excluded | the README's `mysql_databases` entry as shipped; then with `tls: false`, now in the README | Fail | As shipped `mysqldump` refused MySQL's self-signed certificate and no archive was written. |
| 2026-11-03 | `apps/ghost` | the same stack, the corrected entry | the README's corrected `mysql_databases` entry; the dump restored with `--container` into a throwaway instance | Pass | 96 tables, 1,138 rows identical; the throwaway site rendered the post with its theme, and the staff login with the mailed device code worked. The failed attempt above stays: it is why the entry carries `tls: false`. |
| 2026-11-03 | `apps/paperless-gpt` | archive of a paperless-gpt v0.28.0 stack on the lab host | the README's `source_directories` and `sqlite_databases` entries | Pass, in place | borgmatic's SQLite restore writes to the configured path, so it replaced the live database rather than a throwaway one, and left the file `root:root` (the README says uid 1000). Integrity check and row counts matched the archive; not counted as a rehearsal into a separate instance. |
| 2026-11-03 | `core/crowdsec` | archive of the CrowdSec v1.7.8 stack directory on the lab host, taken with the container stopped as the README asks — 7.5 MB, a local throwaway repository | the README's backup, `source_directories` only; the stack directory extracted into a throwaway instance on its own network, its central API off (`DISABLE_ONLINE_API=true`) and its log source empty | Pass | The restored engine started healthy: the same two decisions, all 100 alerts, the eight collections, the machine and the `traefik-bouncer`. The bouncer key from `core/traefik/.env` was accepted by the restored local API (a wrong key 403), and the restored AppSec answered `/.env` with 403. |
| 2026-11-08 | `business/listmonk` | archive of a listmonk v6.2.0 stack with its PostgreSQL 18.6 dump on the lab host (VM), borgmatic 2.2.0, borg 1.4.0, a local throwaway repository, `volumes/uploads` included | the README's `postgresql_databases` entry as shipped, with the host's client 17.11; then `pg_dump_command`/`pg_restore_command` through `docker exec`, a lab variant, into a fresh `postgres:18.6-alpine` | Fail | As shipped no archive was written: `pg_dump` 17.11 aborts on server 18.6 (`server version mismatch`). Through `docker exec` the dump and the restore exited 0: 17 tables, 87 rows identical, and a throwaway listmonk v6.2.0 on the restored database logged the admin in and listed the test subscriber. FA-03 stays open. |
| 2026-11-08 | `apps/opnform` | archive of an OpnForm 2.8.4 stack with its PostgreSQL 16.15 dump on the lab host (VM), `volumes/storage` included | the README's entry as shipped; then the `docker exec` lab variant, into a fresh `postgres:16.15-alpine` | Fail | As shipped the archive was written, and `pg_restore` 17.11 stopped at `unrecognized configuration parameter "transaction_timeout"`; borgmatic reported only a `utf-8` decode error, the real one only with `-v 2`. Through `docker exec`: exit 0, 45 tables, 133 rows identical. |
| 2026-11-08 | `apps/immich` | archive of an Immich v3.3.6 stack with its PostgreSQL 14.23 (vectorchord) dump on the lab host (VM), `volumes/library` included | the README's entry as shipped; then the `docker exec` lab variant, into a fresh container of the same image digest | Fail | As shipped `pg_restore` 17.11 stopped at `transaction_timeout`. Through `docker exec`: exit 0, 73 tables, 233,636 rows identical. |
| 2026-11-08 | `apps/lycheeorg` | archive of a Lychee v7.12.1 stack with its MariaDB 12.3.3 dump on the lab host (VM), `volumes/uploads` included — after the correction of the v7 mount paths | the README's `mariadb_databases` entry as shipped; restored with `--container` into a fresh `mariadb:12.3.3` | Pass | 55 tables, 1,149 rows identical (a first count, taken while the app still wrote, differed; the second matched). |
| 2026-11-08 | `business/invoiceninja` | archive of an Invoice Ninja 5.13.53 stack with its MySQL 8.4.13 dump on the lab host (VM) | the README's `mysql_databases` entry as shipped (`tls: false`); restored with `--container` into a fresh `mysql:8.4.13` | Pass | 80 tables, 1,484 rows identical, the test client and invoice among them. `mysqldump` warned about the missing `PROCESS` privilege for tablespaces and wrote the archive. |
| 2026-11-08 | `business/openproject` | archive of an OpenProject 17.9.6 stack with its PostgreSQL 18.6 dump on the lab host (VM) | the `docker exec` lab variant only — the README's entry cannot dump server 18 with client 17 (the `business/listmonk` row) | Not run as shipped | Through `docker exec`: exit 0, 218 tables, 3,502 rows identical. |
| 2026-11-08 | `business/vikunja` | archive of a Vikunja 2.8.0 stack with its PostgreSQL 18.6 dump on the lab host (VM) | the `docker exec` lab variant only, as above | Not run as shipped | Through `docker exec`: exit 0, 44 tables, 195 rows identical. |
| 2026-11-08 | `business/zammad` | archive of a Zammad 7.2.2-0045 stack with its PostgreSQL 18.6 dump on the lab host (VM), `volumes/zammad-storage` included, the Elasticsearch index not (rebuildable) | the `docker exec` lab variant only, as above | Not run as shipped | Through `docker exec`: exit 0, 132 tables, 251,722 rows identical. |
| 2026-11-08 | `core/authentik` | archive of an authentik 2026.8.5 stack with its PostgreSQL 18.6 dump on the lab host (VM), `volumes/data` included | the `docker exec` lab variant only, as above | Not run as shipped | Through `docker exec`: exit 0, 231 tables, 3,456 rows identical. |
| 2026-11-08 | `core/dockhand` | archive of a Dockhand v1.0.57 stack with its PostgreSQL 16.15 dump on the lab host (VM) | the `docker exec` lab variant only — the README's entry with client 17 fails at `pg_restore` on server 16 (the `apps/opnform` row) | Not run as shipped | Through `docker exec`: exit 0, 40 tables, 76 rows; identical except `container_events`, which the running instance writes continuously (64 live, 62 in the dump). |
