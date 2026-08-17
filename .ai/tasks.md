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
- [ ] Point `monitoring/beszel` and `monitoring/beszel-agent` at a socket proxy while
      bringing them up. Upstream supports `DOCKER_HOST`, and documents a proxy with
      `CONTAINERS=1` as the safer setup — so the exception's old claim that Beszel
      has no proxy support was wrong. The agent runs in host network mode, so the
      proxy binds `127.0.0.1:2375`. Until then the agent holds the full Docker API,
      which is root on the host; `:ro` on the socket does not change that
- [ ] Verify `monitoring/ntfy` — `read_only: true`, the `sec-3` rate limit under a
      publish burst, and one message proven to arrive on a real device. Its Known
      Issues list is the check list.
- [ ] Validate `apps/caldiy` on `v6.2.0-5` — the pin and the documentation moved,
      the verification did not. `UPSTREAM.md` still reads `Last verified: 2026-07-26
      (v6.2.0-3)`, so the stamp is now two fork releases behind the pin. Issue #30
      lists what has to pass: entrypoint against the non-root `node` user, every
      mounted secret readable without widening permissions, database migration,
      `/api/health` and the container healthcheck, login plus one booking, SMTP and
      cron, and a log read for permission or migration errors. Rollback pin is in
      `.env.example`
- [ ] Boot `apps/_reference/` once to confirm the template actually runs
- [ ] Count the first-load requests for the four photo galleries — `apps/photoprism`,
      `apps/librephotos`, `apps/lycheeorg`, `apps/photoview`. All four sit at `sec-2`,
      whose `rl-soft` allows a burst of 50 per client address, and a thumbnail grid
      is the shape that exceeds it. `apps/immich` already needed `sec-2-spa` for the
      same reason. The method is in `docs/standards/traefik-security.md` under
      Choosing the level for an app; above 50 the answer is the `-spa` variant, which
      leaves the sustained rate untouched. `apps/it-tools` is the same question — a
      Vue single-page app at `sec-3`, never counted. `core/portainer` first: it runs
      `sec-4`, whose burst is 40, and its interface is a single-page app. Load it
      once with an empty cache and read the request count
- [ ] Decide `APP_TRAEFIK_SECURITY` for Seafile's four path-scoped routers.
      They carry the access policy; the chain is deliberately absent until an
      instance shows what it survives. `/sdoc-server` is the open one — `sec-2`
      sets `frameDeny` and upstream documents neither the header nor whether
      SeaDoc is framed, so it is `sec-2` or `sec-2e` and only a running editor
      answers it. `/socket.io` and `/notification` are WebSockets and
      `/thumbnail` issues many parallel requests, all against `rl-soft`
- [ ] `business/openproject` after `internal: true` — whether mail leaves `worker`
      and whether first-run seeding completes without an outbound path. If either
      fails, `worker` and `cron` get a second network, not a removed flag.
      `business/vikunja` carries the same change with only `db` behind it

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
