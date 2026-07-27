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

### 3 · A database comes back

Restore into a throwaway database, not the live one:

```bash
docker run -d --name restore-test -e POSTGRES_PASSWORD=test -p 15432:5432 postgres:17
docker exec restore-test createdb -U postgres myapp

sudo borgmatic restore --archive latest --database myapp \
  --hostname 127.0.0.1 --port 15432 --username postgres
```

Then verify the data, not just the exit code:

```bash
docker exec restore-test psql -U postgres -d myapp -c '\dt'
docker exec restore-test psql -U postgres -d myapp -c 'SELECT count(*) FROM <a_real_table>;'
```

A row count you can sanity-check is the evidence. "The command exited 0" is not.

### 4 · Clean up

```bash
docker rm -f restore-test
rm -rf /tmp/restore-test
```

### 5 · Write it down

Record the date, the archive used, what was restored, and anything that surprised you. An undocumented rehearsal cannot be pointed at later — and the surprises are the whole value.

---

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

# 3 · Restore
sudo borgmatic restore --archive latest --database myapp

# 4 · Start and verify
docker compose start app
docker compose logs app --tail 50
```

The database must already exist — Borgmatic will not create it.

## Real restore — whole stack onto a new host

1. Install Docker and borgmatic on the new host.
2. Place the passphrase at `/root/.borg-passphrase` and, if the repository key is not reachable, import it: `borg key import <repo> /path/to/exported-key.txt`
3. Extract the deployment: `sudo borgmatic extract --archive latest --path srv/docker --destination /`
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

| Date | Archive | Scope | Result | Notes |
|---|---|---|---|---|
| — | — | — | — | No rehearsal has been performed yet. |
