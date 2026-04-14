# acme-certs Bugfixes — 2026-04-14

## Bug #1: `crond: unrecognized option: d`

**Symptom:** Container crashes in restart loop with:
```
crond: unrecognized option: d
```

**Root cause:** The `crond -f -d 8` command uses `-d` (debug level) which is not supported by the BusyBox crond shipped in `neilpang/acme.sh:3.1.2`. The older version used a different crond that accepted `-d`.

**Fix:** Changed to `crond -f` (foreground only, no debug flag).

**Lesson:** When bumping image versions, check if built-in tools have changed CLI flags. BusyBox tools are minimal and may drop flags between versions.

---

## Bug #2: Script permission denied

**Symptom:** `./scripts/wizard.sh: Permission denied`

**Root cause:** Scripts lost execute permission during copy/sync to server.

**Fix:** `chmod +x scripts/*.sh`

**Lesson:** Always verify script permissions after deploying to a new server.
