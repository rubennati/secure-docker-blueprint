# Tasks

Current work items. Larger direction lives in [`../ROADMAP.md`](../ROADMAP.md);
this file is the short list.

## Blocked on a host

Ordered run: [`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md);
what v0.7.0's session left open is in
[`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md)

- [x] Borgmatic: install, initialise repository, first backup, export the key off-host
- [x] **Restore rehearsal — closed v0.7.0** and produced the first `ops-proven` stack
- [ ] Exercise append-only over a remote repository — the one Borgmatic mechanism
      a local rehearsal cannot establish. Not about owning an off-site target;
      about whether the documented protection behaves as written
- [ ] UrBackup: verify against the gate list in `backup/urbackup/README.md`
- [ ] Verify the nine pending major versions
- [ ] Decide the legacy verification stamps, per app — `LIFECYCLE.md` marks them ⚠️
- [ ] Verify `monitoring/healthchecks` and `monitoring/uptime-kuma` — borgmatic's run
      monitoring points at them, so backup's proof layer depends on them
- [ ] Verify `monitoring/ntfy` — `read_only: true`, the `sec-3` rate limit under a
      publish burst, and one message proven to arrive on a real device. Its Known
      Issues list is the check list.
- [ ] Boot `apps/_reference/` once to confirm the template actually runs

## Open decisions for the maintainer

Listed with context in [`state.md`](state.md). Nothing proceeds on these until decided.

## Doable without a host

- [x] Fill the `## Backup` section in every stack README — done for every stack
      except `backup/borgmatic`, which is `n/a` by declaration: the backup tool
      cannot describe backing itself up with itself. Coverage is the Backup docs
      column in `LIFECYCLE.md`
- [ ] `backup/urbackup` has no restore section — restoring a *client* backup is a
      real procedure and the one gap left in that column
- [ ] **`apps/vaultwarden` → Docker Secrets.** The blocker recorded in `UPSTREAM.md`
      was wrong: Vaultwarden does support `_FILE`. The real obstacle is that the
      password sits inside `DATABASE_URL`, so the secret must carry the whole URL
      (`DATABASE_URL_FILE`) or an entrypoint must assemble it. Needs a host test —
      it changes how a ✅ stack starts
- [ ] `business/invoiceninja` → Docker Secrets via entrypoint wrapper (Phase 2).
      Genuinely upstream-limited: Laravel has no `_FILE` for `APP_KEY`/`DB_PASSWORD`
- [ ] Decide the three questions in [`../docs/renovate-proposal.md`](../docs/renovate-proposal.md):
      marker comments vs. normalising 28 outliers · Renovate App vs. self-hosted
      Action · whether `site/` npm rides along. Nothing runs until then
- [ ] **`docker-compose.local.yml` for every stack** — `git ls-files
      '*docker-compose.local.yml'` lists the ones that have it. The
      pattern is canonical in `apps/_reference/`: no Traefik, no certificates, no
      Docker Secrets, a published port and plain environment variables. It exists
      so someone can try an app — locally, on a laptop, on a lab box — without
      first standing up a reverse proxy, DNS and a certificate chain. Today the
      blueprint asks for the whole pipeline before anything runs, which is a
      steep first step for a user who only wants to see whether the app suits
      them. Also the natural entry point for the operator site: *try it locally*
      before *deploy it properly*
- [x] Decide the `TROUBLESHOOTING.md` / `docs/standards/troubleshooting.md` overlap
      — index and method, declared in both files and in the File Map
- [ ] Add `Checker coverage`, `Docs QA` and `Workflow supply chain` to the required
      checks in branch protection — all three run, but nothing blocks on them yet
