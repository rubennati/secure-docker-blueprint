# Authentik — first-setup permission bug — 2026-04-20

## Symptom

Fresh install. `docker compose up -d` brings up `db` and `redis` clean,
but `server` and `worker` enter a crash loop with:

```
authentik-worker  | {"event": "Not running as root, disabling permission fixes", "level": "info"}
authentik-worker  | 2026-04-20 23:17:20 [info] Migration needs to be applied  migration=tenant_files.py
authentik-worker  | Traceback (most recent call last):
authentik-worker  |   File "/lifecycle/system_migrations/tenant_files.py", line 18, in run
authentik-worker  |     TENANT_MEDIA_ROOT.mkdir(parents=True)
authentik-worker  |   File "/usr/local/lib/python3.12/pathlib.py", line 1311, in mkdir
authentik-worker  |     os.mkdir(self, mode)
authentik-worker  | PermissionError: [Errno 13] Permission denied: '/media/public'
```

Both `authentik-worker` and `authentik-server` restart every few
seconds. No web UI is ever reachable.

## Root cause

Two independent issues in the pre-2026-04-20 compose, both surfaced by
the same fresh install:

### 1. Image runs as UID 1000 and refuses to self-fix permissions

Recent `goauthentik/server` images run as a non-root user (UID 1000).
When the image detects it is not running as root it logs:

```
Not running as root, disabling permission fixes
```

and skips the `chown -R` step that would otherwise prepare the volume
mount points. On a fresh install `./volumes/data/` (mounted into the
container) is owned by `root:root` because Docker creates bind-mount
target directories with the daemon's UID. UID 1000 cannot create the
`public/` subdirectory the `tenant_files` migration needs, and the
process dies.

This is deliberate on the upstream side — the image explicitly refuses
to escalate — and documented at
https://docs.goauthentik.io/troubleshooting/image_upload/

### 2. Legacy `/media` mount path

The blueprint compose mounted `./volumes/media:/media`. Authentik has
migrated from `/media` to `/data`. Current images still read the old
path for backwards compatibility but new uploads target `/data`, and
the startup migration (`tenant_files.py`) creates `public/` under
whichever path is mounted. Staying on `/media` means chasing a
deprecated path that will eventually stop working.

## Fix

### New `init-perms` service

A short-lived Alpine container runs as root, chowns
`./volumes/data`, `./volumes/certs`, and `./volumes/custom-templates`
to `1000:1000` with the right modes, and exits. `server` and `worker`
`depends_on: init-perms (service_completed_successfully)`, so they
only start once the init container has finished.

The long-running Authentik containers stay non-root. Only the init
container needs root — for the ~500ms until it exits.

### `/media` → `/data`

Both `server` and `worker` now mount `./volumes/data:/data` instead
of `./volumes/media:/media`. The `custom-templates` mount stays at
`/templates`, unchanged.

### Ops script

The chown/chmod logic lives in
`core/authentik/ops/scripts/init-volumes.sh` (POSIX sh, idempotent).
The init container mounts it read-only and invokes it as its
entrypoint — script stays versioned, testable, and reviewable
independently of the compose.

## Apply

```bash
cd core/authentik

# For an upgrade from the legacy layout:
docker compose down
# Rename the old bind mount if you want to preserve state
# (Authentik migrates the contents on next boot)
mv volumes/media volumes/data 2>/dev/null || true

docker compose up -d
docker compose logs -f
```

## Verify

```bash
# 1. Init container ran and exited cleanly
docker compose ps init-perms
# Expected: STATUS = Exited (0)

# 2. Volumes are owned by UID 1000 inside the worker
docker compose exec worker stat -c '%u:%g' /data /certs
# Expected: 1000:1000 on both lines

# 3. Server is serving
curl -fsSI https://<APP_TRAEFIK_HOST>/-/health/live/
# Expected: HTTP/2 200
```

## Why an init container, not a manual pre-script

Considered both. Init container won because:

1. Permission setup is one-off per volume. Manual sudo wrappers add
   a step that users forget on fresh installs → crashloop → confusion.
2. Self-healing: if permissions get damaged (backup restore, moved
   data, user error), the next `up -d` fixes it automatically.
3. The "root container" footprint is minimal — Alpine, 5 MB, runs for
   under a second, exits. The baseline hardening (`no-new-privileges`,
   non-root) stays intact on the long-running services.

The chown lives in a standalone script (`ops/scripts/init-volumes.sh`)
so future changes (new directories, different modes) are a
one-file edit, not a compose rewrite.
