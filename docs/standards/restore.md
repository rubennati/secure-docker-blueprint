# Restore

How to bring an application back into a known-good running state once its
data has already been restored — the step most stack READMEs stop short of.

This is not a new backup mechanism. [`backup/README.md`](../../backup/README.md)
is the backup architecture (what gets backed up, the four layers, RPO/RTO).
[`backup/borgmatic/RESTORE.md`](../../backup/borgmatic/RESTORE.md) is the
Borgmatic mechanics — the exact commands, the rehearsal log, what to do if
the source host is gone. This document is the layer between them: given a
successful Borgmatic restore, how does the *application* come back, not just
its bytes.

---

## Backup restore ≠ application recovery

A successful `borgmatic extract` or `borgmatic restore --database` proves the
archive is intact and readable. It does not prove the application works:

- a database dump can restore cleanly and still be one schema version behind
  what the currently-pinned image expects;
- a restored `config.php`/`.env`/state file can reference a secret that no
  longer exists, or a hostname that has changed;
- an application that quiesces into maintenance mode as part of a consistent
  backup comes back in that mode, refusing to serve until told otherwise
  (see the [Nextcloud restore](../../apps/nextcloud/README.md#restore)
  rehearsal for exactly this).

The canonical flow below exists because "the restore command exited 0" and
"the application works" are different claims, and this repository already
has real evidence they diverge.

---

## Canonical recovery flow

```text
stop/quiesce
  → restore data
  → restore/import database
  → correct ownership/permissions
  → start dependencies
  → start application
  → run required migrations/recovery commands, if documented
  → verify
  → only then return to service
```

Every step is generic; what it means for a given stack depends on the
persistence pattern below. A stack with no database skips the database step
entirely rather than substituting something for it.

---

## Persistence patterns actually found

Surveyed from every production `docker-compose.yml`/`.env.example` in
`core/`, `apps/`, `business/` and `monitoring/`, cross-checked against
`backup/borgmatic/config.yaml.example`'s own database hooks — not assumed:

| Pattern | Stacks | Restore mechanic |
|---|---|---|
| File-based only (bind mount or named volume, no database) | ~23 stacks — e.g. `core/traefik`, `core/portainer`, most single-container apps | Plain file restore |
| PostgreSQL | ~15 stacks — `core/authentik`, `core/keycloak`, `core/infisical`, `apps/immich`, `apps/paperless-ngx`, `business/openproject`, `business/vikunja`, and others | Logical dump restore |
| MariaDB / MySQL | ~15 stacks — `apps/nextcloud`, `apps/seafile`, `apps/wordpress`, `business/dolibarr`, `business/invoiceninja`, and others | Logical dump restore |
| SQLite, dump-hook-backed | `apps/n8n`, `apps/nocodb`, `monitoring/gatus`, `monitoring/healthchecks`, `monitoring/uptime-kuma`, `monitoring/beszel` | Logical dump restore |
| SQLite, file-only (no dump hook, by the stack's own documented choice) | `monitoring/ntfy`, `apps/heimdall`, `apps/homarr` | Plain file restore, stopped first |
| MongoDB | `apps/unifi`, `business/opensign` | Logical dump restore |

**Redis is not a pattern here.** It appears in roughly a dozen `.env.example`
files, but every stack that documents its role names it cache, session or
locking state (`apps/nextcloud/README.md`: *"File locking + session cache"*)
— never the authoritative store. `config.yaml.example` has no Redis dump
hook, which is the backup mechanism's own confirmation of the same fact:
nothing here treats Redis as data that needs to come back. There is
therefore no Redis restore playbook, and none is needed.

**A named-volume detail, not a separate pattern.** Four stacks keep
application files in a Docker named volume rather than a bind mount —
`apps/nextcloud` (`nextcloud_html`), `business/invoiceninja` (`app_public`,
`app_storage`), `business/vikunja` (`vikunja_files`), `business/openproject`
(`op_assets`), per `backup/borgmatic/RESTORE.md`'s own "whole stack onto a
new host" section. Everything else uses `./volumes/` bind mounts. This
changes *where* the file-based restore extracts to
(`/var/lib/docker/volumes/<name>/_data` vs. the deployment's own `volumes/`
directory), not what the restore does.

**Two shapes of "SQLite," not one.** `monitoring/uptime-kuma`'s own README
states the database is "written continuously" and provides a
`sqlite_databases:` Borgmatic hook — restore that one as a database.
`monitoring/ntfy`'s own README states plainly: *"Database: None. SQLite
files, not a database server — no dump hook needed"* — restore that one as a
file, stopped first. Follow each stack's own documentation on this; do not
assume one SQLite-backed stack behaves like another.

---

## Restoring data

### A. File-based restore

Covers a stack with no database, and a SQLite-backed stack the stack's own
README documents as file-only (above).

```bash
cd /srv/docker/<category>/<stack>
docker compose stop <affected-service>          # stop first for a live single-file store
sudo borgmatic extract --archive latest \
  --path srv/docker/<category>/<stack> --destination /tmp/recovered
# inspect, then move into place — never extract straight over live data
rsync -a /tmp/recovered/srv/docker/<category>/<stack>/volumes/ ./volumes/
```

For one of the four named-volume stacks, extract
`--path var/lib/docker/volumes/<name>` instead (or in addition — most of
those stacks also have a bind-mounted `.env`/`.secrets/`), and restore under
`/var/lib/docker/volumes/<name>/_data`. Confirm the Docker root first:
`docker info --format '{{.DockerRootDir}}'`.

### B. Database dump-based restore

Covers PostgreSQL, MariaDB/MySQL, a dump-hook-backed SQLite stack, and
MongoDB — all restored the same way, because Borgmatic's database hooks
always produce a logical dump, never a raw copy of the data directory:
*"Copying a running database's files can capture a torn, mid-transaction
state that only reveals itself at restore. Always dump."*
(`backup/borgmatic/config.yaml.example`). This standard follows that
mechanism; it does not invent a separate one, and does not recommend
raw-directory replacement as a shortcut.

```bash
# 1 · Safety copy of what is there now, even if you believe it is broken
docker exec <db-container> pg_dump -U <user> <db> > /root/pre-restore-$(date +%Y%m%d-%H%M).sql

# 2 · Stop the application, leave the database running
docker compose stop <app-service>

# 3 · Restore — the database must already exist; Borgmatic does not create it
sudo borgmatic restore --archive latest --database <name>

# 4 · Start and verify
docker compose start <app-service>
docker compose logs <app-service> --tail 50
```

This is `backup/borgmatic/RESTORE.md`'s own "Real restore — a database"
procedure; it is not repeated in full here. Substitute the engine-specific
step 1/verification command:

| Engine | Safety-copy / verify command |
|---|---|
| PostgreSQL | `pg_dump -U <user> <db>` |
| MariaDB / MySQL | `mariadb-dump -u<user> -p<pass> <db>` (one client covers both engines, per `config.yaml.example`) |
| SQLite | `sqlite3 <path> .dump` |
| MongoDB | `mongodump --uri <uri>` |

Restoring onto a fresh instance instead of the live one — the rehearsal
pattern — is documented per engine in `backup/borgmatic/RESTORE.md`'s
"Rehearsal" section.

---

## Ordering

1. **Database** first — everything else depends on it being present and
   consistent before the application starts.
2. **Application files / uploads** — bind mount or named volume, alongside
   or after the database; the application will not serve correctly with one
   restored and not the other.
3. **Configuration / secrets** — `.env` and `.secrets/` must already be in
   place before step 4; see the boundary below.
4. **Dependent services** (cache, search index, socket proxy) before the
   application container itself, matching each stack's own `depends_on`.
5. **The application**, last.

---

## Secrets/config boundary

A restored application needs the same secrets that were live when its data
was written — generation, storage and rotation are
[Secrets](secrets.md)'s job, not repeated here. Two restore-specific risks:

- **A rotated secret since the backup was taken.** If the database password
  changed after the archive but the `.secrets/` files were restored from a
  different point in time than the database dump, the application will
  fail to authenticate — restore `.secrets/` and the database dump from the
  *same* archive, not a mix of two.
- **A lost or mismatched signing/encryption key makes restored data
  unusable, not just inaccessible.** If a stack's encryption-at-rest or
  session-signing key is not restored alongside its data — or was rotated
  without the app's own re-encryption support — the restored data may be
  permanently unreadable rather than merely locked. [Secrets](secrets.md#3-signing--encryption--session-key)
  already flags this for rotation; the same risk applies in reverse during a
  restore. Confirm the stack's own documentation before assuming a restored
  key-protected value is recoverable.

---

## Verification

Containers starting is not verification. A restore is complete when:

- [ ] every service `docker compose ps` reports involved in the stack is
      healthy, not just running
- [ ] the application is reachable through its normal route (Traefik, not a
      published port used only for the restore)
- [ ] authentication works — a real login, not just the login page loading
- [ ] representative persistent data is actually present — a specific file,
      a row count you can sanity-check, not "the command exited 0"
      (`backup/borgmatic/RESTORE.md`'s own MariaDB rehearsal step is the
      model: `SELECT COUNT(*) FROM <a_real_table>`)
- [ ] application/database logs show no migration or startup error in the
      first few minutes
- [ ] one meaningful application-specific check where the stack's own docs
      name one — Keycloak's schema-migration-on-boot behavior
      (`core/keycloak/README.md`), Nextcloud's maintenance-mode flag, or
      similar

Keep this list small and run all of it every time; a partially-checked
restore is how "the restore worked" turns out to mean "it started."

---

## Rehearsal

Three distinct claims, easy to conflate:

| Claim | What it means | Where it's recorded |
|---|---|---|
| **Documented** | A restore procedure exists for this stack — this standard, plus whatever the stack's own README adds | The stack's README, pointing here |
| **Restore-tested** | Someone has walked the procedure by hand and it worked, informally | Wherever the operator notes it — not a status this repository tracks |
| **`ops-proven`** | The restore is logged with real evidence — archive, scope, result, numbers — in the rehearsal log | [`backup/borgmatic/RESTORE.md`](../../backup/borgmatic/RESTORE.md#rehearsal-log), which is what `scripts/ci/lifecycle-report.py` reads to award the status, per [Status Model](status-model.md) |

`ops-proven`'s definition is unchanged by this document — it already meant
exactly this. What changes is that a stack now has somewhere to point
*before* it reaches that bar: "documented" is a real, useful intermediate
state this repository did not previously give a name to.

---

## Stack-specific boundary

This standard is the reusable baseline: what must be restored, in what
order, how database consistency is handled, and how to verify the result. It
does not invent what a specific application needs beyond that — a
migration-on-boot behavior, a maintenance-mode flag, a required CLI command
— without evidence. Where a stack's own README already documents that
(Keycloak's schema-migration note, Nextcloud's maintenance-mode section),
that stays there; this document is what those pages point back to for the
mechanics they don't need to repeat.
