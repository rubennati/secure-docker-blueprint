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

---

## Bug #3: CF_Token missing when running wizard or docker compose exec

**Symptom:** Running `./scripts/wizard.sh` or `docker compose exec acme-certs /scripts/issue.sh` fails with:
```
CF_Token missing – check .secrets/cf_token.txt
```
Even though the secret file exists and contains a valid token.

**Root cause:** The entrypoint wrapper (`config/entrypoint.sh`) correctly loads `CF_Token` from `/run/secrets/CF_TOKEN` and exports it. But:

1. **`docker compose exec`** starts a new process inside the container that **bypasses the entrypoint**. The export from the initial entrypoint is only available to the PID 1 process (crond) and its children.
2. **crond** spawns cron jobs as separate processes that don't inherit the entrypoint's exported env vars either.
3. The **wizard** runs on the host and calls `docker compose exec` internally — same problem.

So even though the entrypoint runs on container start, the CF_Token is never available to manually executed or crond-spawned scripts.

**Fix:** Made `issue.sh` self-sufficient — it loads the Docker Secret directly if `CF_Token` is not already in the environment:

```sh
# Load CF_Token from Docker Secret if not already set
if [ -z "${CF_Token:-}" ] && [ -f /run/secrets/CF_TOKEN ]; then
  export CF_Token="$(cat /run/secrets/CF_TOKEN)"
fi
: "${CF_Token:?CF_Token missing – check .secrets/cf_token.txt}"
```

**Lesson:** Never rely on entrypoint-exported env vars for scripts that run via:
- `docker compose exec` (bypasses entrypoint)
- `crond` (spawns independent processes)
- Any process not directly started by `exec "$@"` in the entrypoint

If a script needs a secret, it should load it itself. The entrypoint pattern works for the main process (PID 1), but not for sidecar commands.
