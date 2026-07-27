# Tasks

Current work items. Larger direction lives in [`../ROADMAP.md`](../ROADMAP.md);
this file is the short list.

## Blocked on a host

Ordered run: [`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md)

- [ ] Borgmatic: install, initialise repository, first backup, export the key off-host
- [ ] **Restore rehearsal — this closes v0.7.0** and produces the first `ops-ready` stack
- [ ] UrBackup: verify against the gate list in `backup/urbackup/README.md`
- [ ] Verify the nine pending major versions
- [ ] Decide the 22 legacy verification stamps, per app
- [ ] Verify `monitoring/healthchecks` and `monitoring/uptime-kuma` — borgmatic's run
      monitoring points at them, so backup's proof layer depends on them
- [ ] Verify `monitoring/ntfy` — `read_only: true`, the `sec-3` rate limit under a
      publish burst, and one message proven to arrive on a real device. Its Known
      Issues list is the check list.
- [ ] Boot `apps/_reference/` once to confirm the template actually runs

## Open decisions for the maintainer

Listed with context in [`state.md`](state.md). Nothing proceeds on these until decided.

## Doable without a host

- [x] Fill the `## Backup` section in every stack README — done, 58 of 59.
      `backup/borgmatic` is `n/a` by declaration: the backup tool cannot describe
      backing itself up with itself
- [ ] `backup/urbackup` has no restore section — restoring a *client* backup is a
      real procedure and the one gap left in that column
- [ ] **`apps/vaultwarden` → Docker Secrets.** The blocker recorded in `UPSTREAM.md`
      was wrong: Vaultwarden does support `_FILE`. The real obstacle is that the
      password sits inside `DATABASE_URL`, so the secret must carry the whole URL
      (`DATABASE_URL_FILE`) or an entrypoint must assemble it. Needs a host test —
      it changes how a ✅ stack starts
- [ ] `business/invoiceninja` → Docker Secrets via entrypoint wrapper (Phase 2).
      Genuinely upstream-limited: Laravel has no `_FILE` for `APP_KEY`/`DB_PASSWORD`
- [ ] Decide the `TROUBLESHOOTING.md` / `docs/standards/troubleshooting.md` overlap
- [ ] Add `Checker coverage` to the required checks in branch protection — the job
      runs, but nothing blocks on it yet
