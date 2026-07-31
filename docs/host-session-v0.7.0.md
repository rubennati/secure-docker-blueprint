# Host session — closing v0.7.0

**Blocks 1 and 2 ran on 2026-07-29 and closed the milestone** — the rehearsal is
logged in [`backup/borgmatic/RESTORE.md`](../backup/borgmatic/RESTORE.md#rehearsal-log),
what the run corrected is in [`host-session-findings.md`](host-session-findings.md).
Two things were deliberately left: the repository sits on the same machine, so
the off-site target is still only written, and the timer stays off until
Healthchecks or Uptime Kuma exists to notice a failed run — that is v0.8.0.
**Blocks 3 to 5 remain open** and still need the host.

Everything left for v0.7.0 needs a reachable host. This is that work in one ordered run, so it happens once instead of four times. The checklists stay as written: they are the procedure for repeating this, not only the record of one run.

**Ordered so a failure blocks as little as possible.** Each block is independent — if one fails, note it and move on; only Block 2 depends on Block 1.

> Update `docs/maintenance.md` (Progress Log) and the rehearsal log in `backup/borgmatic/RESTORE.md` as you go, not afterwards from memory.

---

## Before you start

- [ ] Host reachable, Docker running, blueprint deployed
- [ ] An SSH-reachable backup target exists and you can log into it
- [ ] Somewhere off this host to put the repository key and passphrase — a password manager is fine

---

## Block 1 · Borgmatic — first backup (~45 min)

Full walkthrough in [`backup/borgmatic/README.md`](../backup/borgmatic/README.md). Condensed:

- [ ] `sudo apt install borgmatic` — then `borgmatic --version`, **must be ≥ 2.0.8** (the `container:` database option does not exist before that)
- [ ] Dedicated SSH key: `ssh-keygen -t ed25519 -f /root/.ssh/id_borg`, copy to the target
- [ ] Passphrase: `openssl rand -base64 32 | tr -d '\n' | sudo tee /root/.borg-passphrase`, then `chmod 600`
- [ ] `borg init --encryption=repokey-blake2 ssh://…`
- [ ] **`borg key export` → move the file off this host.** Do not defer this. Without it, losing the host loses every backup.
- [ ] `/etc/borgmatic/config.yaml` from the example: source directories, the real database containers, retention, the Healthchecks or Uptime Kuma URL
- [ ] `sudo borgmatic config validate`
- [ ] `sudo borgmatic create --verbosity 1 --list --stats` — first run
- [ ] `sudo borgmatic list` shows an archive
- [ ] `systemctl list-unit-files | grep borgmatic` — use the packaged units if present, otherwise install the timer example
- [ ] `sudo systemctl enable --now borgmatic.timer` and confirm with `systemctl list-timers`

**Watch for:** database dumps failing quietly. Check the run output actually names each database. An archive that exists is not an archive that contains what you think.

## Block 2 · Borgmatic — the restore rehearsal (~30 min)

**This is the block that closes v0.7.0.** Everything else is preparation.

Follow [`backup/borgmatic/RESTORE.md`](../backup/borgmatic/RESTORE.md), rehearsal section. Restore into a scratch location, never into the live deployment.

- [ ] Extract one application directory, confirm the files are non-empty and a known file has the expected content
- [ ] Restore one database into a throwaway container, then run a real query — a row count you can sanity-check, not an exit code
- [ ] Clean up the scratch container and directory
- [ ] **Fill in the rehearsal log** at the bottom of `RESTORE.md`

Then:

- [ ] `backup/borgmatic/UPSTREAM.md` → record `Last verified: DATE (vX.Y.Z)`
- [ ] `backup/borgmatic/` gets an `UPSTREAM.md`-equivalent `Last verified` — or record the date in the README status line
- [ ] `backup/README.md` and root `README.md` status rows updated
- [ ] `python3 scripts/ci/lifecycle-report.py --write`

## Block 3 · UrBackup (~45 min)

Gate list is in [`backup/urbackup/README.md`](../backup/urbackup/README.md) under "Verify on first deploy".

- [ ] `docker compose up -d`, container healthy
- [ ] **Check the healthcheck tool first:** `docker exec urbackup-app sh -c 'which curl wget'`. The compose file assumes `curl`; if it is absent the container reports unhealthy and the healthcheck needs changing.
- [ ] Web interface reachable through Traefik, TLS valid, access policy enforced
- [ ] **Create the administrator account immediately** — until one exists the interface is open
- [ ] Add one client by hostname (your laptop), first backup completes
- [ ] Restore one file from it and open the file to confirm the content
- [ ] Confirm `BACKUP_STORAGE_PATH` is **excluded** from borgmatic's `source_directories`
- [ ] Status → `✅` if every gate passed, otherwise note which failed and leave it at 🚧

## Block 4 · The nine major versions (~60 min)

Pinned during the July sweep, never started. Bring each up and check the core function actually works — not just that the container runs.

- [ ] `apps/paperless-ngx` 3.x — **search index migration** (Whoosh → tantivy), needs a reindex; API v1 removed
- [ ] `apps/wordpress` 7.x
- [ ] `apps/immich` 3.x
- [ ] `apps/nocodb` — CalVer switch
- [ ] `apps/adminer` 5.x (major 4 → 5)
- [ ] `apps/homepage` 1.13.x
- [ ] `apps/opnform` 2.2.x
- [ ] `monitoring/healthchecks` 4.x
- [ ] `monitoring/uptime-kuma` 2.x — **1.x → 2.x is a real migration**, take the database backup first
- [ ] `apps/caldiy` v6.2.0-4 — fork rebuild, only needs a start and a booking flow

For each that passes: update `Last verified: YYYY-MM-DD (vX.Y.Z)` in its `UPSTREAM.md`. For each that fails: write a `docs/bugfixes/<app>-<date>.md` and drop the status to 🚧.

## Block 5 · The legacy verification stamps (~30 min)

22 stacks carry the pre-v0.5.1 `Last checked:` field instead of `Last verified: DATE (vX.Y.Z)`. `scripts/ci/lifecycle-report.py` lists them as `legacy-stamp`.

The date exists, so the evidence probably does too — but converting the field asserts that evidence is real. **That is a judgement per app, never a search-and-replace.**

- [ ] `python3 scripts/ci/lifecycle-report.py` — get the current list
- [ ] For each: is it running and working right now? Then convert the field and set today's date with the running version
- [ ] If you are not sure it was ever properly verified: leave the legacy field and drop the status to 🚧

## Block 6 · Close the release

- [ ] Consistency Chain from `docs/maintenance.md`
- [ ] `python3 scripts/ci/check-structure.py` and `lifecycle-report.py --check` both clean
- [ ] `CHANGELOG.md`: `[Unreleased]` → `[0.7.0]`, comparison links
- [ ] `ROADMAP.md`: v0.7.0 into "Shipped", "Last updated" bumped
- [ ] `README.md`: version badge → `v0.7.0`
- [ ] Progress Log row
- [ ] `git tag v0.7.0` and `gh release create v0.7.0 --draft`

---

## What "done" means

v0.7.0 is finished when **one restore has actually been performed and written down**. Not when the configuration is complete, not when the timer runs, not when the archive exists.

That also produces the repository's first `ops-proven` stack — a state nothing currently holds, because there has never been restore evidence for anything here.

## If time runs short

Do Blocks 1 and 2. They are v0.7.0. Blocks 3–5 are valuable and share the same precondition, but the milestone does not depend on them.
