# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-07-27

- **Phase:** pre-1.0. Latest tag `v0.6.0` (2026-06-04). Work happens on `dev`.
- **Current milestone:** v0.7.0 — Backup.
- **Definition of done for v0.7.0:** one restore performed and written down. Not
  when the configuration validates, not when the timer runs, not when an archive
  exists.

## Snapshot

- 59 stacks tracked. 39 `ready`, 20 `preview`, **0 `ops-ready`** — no stack has
  restore evidence, which is exactly what v0.7.0 changes. Numbers come from
  `LIFECYCLE.md`; regenerate rather than editing them here.
- Backup architecture designed (`backup/README.md`): five layers, host-installed
  agent, snapshot/backup/archive kept distinct.
- `backup/borgmatic/` — configuration, systemd timer, setup and restore playbook.
  Host-installed, no Compose stack. Never exercised on a host.
- `backup/urbackup/` — client and endpoint backup, bridge networking with the web
  interface behind Traefik, host-networking overlay opt-in. Never started.
- Status model unified (`docs/standards/status-model.md`); `LIFECYCLE.md` generated
  by `scripts/ci/lifecycle-report.py`; both structure and status enforced in CI.
- CI: 7 required checks on `main`, all green.

## Immediate next steps

1. Host session — the ordered run is in [`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md).
   Blocks 1 and 2 (Borgmatic first backup, restore rehearsal) are the milestone.
2. Monitoring verification is planned for the same session: borgmatic's run
   monitoring points at `monitoring/healthchecks` and `monitoring/uptime-kuma`,
   which are themselves unverified. Backup's proof layer depends on them.

## Open decisions

Carried until the maintainer decides. Each blocks a clean resolution somewhere.

1. **Commit procedure** — `docs/standards/commit-rules.md` requires asking before
   every commit; the external `ai-project-standard` allows agents to commit to
   non-`main` branches. Which governs here?
2. **Backup repository isolation** — `docs/architecture.md` states one repository
   per app as a rule; `backup/README.md` currently presents it as an option. The
   owner is `architecture.md`. Revert the demotion, or change it at the owner?
3. **Two troubleshooting documents** — `TROUBLESHOOTING.md` (root) and
   `docs/standards/troubleshooting.md` overlap. Merge or split responsibilities?
4. **Commit message format** — the standard specifies `scope: subject`; recent
   history uses conventional commits. Correct the standard or the practice?
5. **Neutral language** — does the "no direct address" rule apply to the English
   documentation, or only to German drafts?
6. **Host-installed backup agent vs. the portability goal** in
   `docs/architecture.md`. Record as a documented exception, or revisit?

## Active constraints

- **No host available.** Everything requiring a running server waits.
- Nine major version bumps are pinned but never started; 22 stacks still carry the
  pre-v0.5.1 `Last checked:` field. Both ride along with the host session.
- Public repository: no real domains, IPs, hostnames or personal data; no session
  context or personal attribution in committed content. `.ai/` is committed and
  therefore public — it holds working context, never internal process detail.
