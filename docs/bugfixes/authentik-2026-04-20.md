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

---

## Bug #3 — Healthchecks reported unhealthy forever

### Symptom

After the permission + path fixes above, `authentik-server` and
`authentik-worker` start cleanly and the app responds normally —
but `docker compose ps` keeps showing both as `unhealthy`
indefinitely. Traefik picks up the server on the `proxy-public`
network regardless, so the app works, but any orchestrator that
gates on container health (Portainer, Dockhand, monitoring) sees a
permanent red light.

### Root cause

Two separate issues:

**1. Image ships no `wget` / `curl`.** The blueprint shipped with:

```yaml
test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:9000/-/health/live/ ..."]
```

The `goauthentik/server` image is a minimal distroless-style build
with Python + `dumb-init` and nothing else. `wget` is not on `PATH`,
so every healthcheck invocation exits non-zero, and after `retries`
attempts the container is flagged unhealthy — regardless of whether
the HTTP endpoint is actually responding. Upstream issue:
https://github.com/goauthentik/authentik/issues/15769

**2. No official worker healthcheck exists anymore.** Upstream
explicitly removed the worker's HTTP healthcheck in 2025.10.2
(`cmd/server/healthcheck: remove worker HTTP healthcheck`). The
worker has no HTTP listener — there is no endpoint to probe. Any
healthcheck on it is fiction.

**3. `start_period` too short.** 30s doesn't cover cold-start Django
migrations on a fresh DB. First boot takes 60–120s; the healthcheck
starts failing before the app is even listening, burning retry budget
before there's anything to check.

### Fix

**Server** — Python-based healthcheck (Python *is* in the image,
it's what the server runs on):

```yaml
healthcheck:
  test:
    - "CMD"
    - "python3"
    - "-c"
    - "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9000/-/health/live/').status==200 else 1)"
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s   # was 30s
```

**Worker** — no explicit healthcheck. The 2024.12.x image ships a
built-in HEALTHCHECK for the worker that queries Celery internals;
it works, it just takes ~60s to flip from `starting` to `healthy`
on cold boot. Leave it alone.

When we move to 2025.10.2 or later, the built-in worker healthcheck
is gone upstream — at that point add `healthcheck: { disable: true }`
to the worker service so Docker doesn't report a spurious
"starting" state indefinitely.

### Verify

```bash
docker compose ps
# Expected: server = Up (healthy)
#           worker = Up (no health column / no healthcheck)

# Confirm the healthcheck command is actually being run:
docker inspect --format '{{json .State.Health}}' authentik-server | jq
```

### Upstream reference

- https://github.com/goauthentik/authentik/issues/15769 — wget missing
- https://github.com/goauthentik/authentik/releases/tag/version/2025.10.2 — worker healthcheck removed
- Canonical `docker-compose.yml` (goauthentik.io) ships **no**
  healthchecks for server or worker. Our Python-based server check
  is the community consensus.
