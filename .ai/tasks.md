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
- [ ] Boot `apps/_reference/` once to confirm the template actually runs

## Open decisions for the maintainer

Listed with context in [`state.md`](state.md). Nothing proceeds on these until decided.

## Doable without a host

- [ ] Fill the `## Backup` section in app READMEs as apps are touched — the pattern
      is in `apps/_reference/README.md`; `LIFECYCLE.md` reports which still lack it
- [ ] Decide the `TROUBLESHOOTING.md` / `docs/standards/troubleshooting.md` overlap
- [ ] A check that reports any content directory no checker covers — three coverage
      blind spots surfaced in one day, all found by accident
