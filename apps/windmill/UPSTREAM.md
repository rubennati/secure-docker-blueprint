# Upstream Reference

## Source

- **Image:** https://github.com/windmill-labs/windmill/pkgs/container/windmill
- **GitHub:** https://github.com/windmill-labs/windmill
- **Docs:** https://www.windmill.dev/docs/
- **License:** AGPL-3.0 (Community Edition core, with Apache-2.0 components); Enterprise features are under a separate commercial licence
- **Edition gating:** code behind the `enterprise` compile flag in `backend/`, and frontend code that requires a positive licence check to activate, is under a proprietary and commercial licence rather than the AGPLv3; forks must not include it — https://github.com/windmill-labs/windmill/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** Windmill Labs · no country stated in its published terms · no country
- **Domain:** Automation and data
- **Role:** Code-first scripts, flows, APIs and scheduled jobs on a queue
- **Based on version:** `1.814.0`

## What we use

- Official image, pinned tag: `ghcr.io/windmill-labs/windmill:1.814.0`. Upstream's
  own `.env` defaults to the floating `:main` tag; not used here.
- `postgres:18.6` — Windmill's own requirement (upstream's compose moved from 16
  to 18). Debian-based, not the `-alpine` variant most other stacks here pin,
  because upstream tests against the Debian image and this is a stateful
  component with a documented major-version migration.
- `DB_USER=postgres` (the superuser), matching upstream's own
  `DATABASE_URL` default rather than the dedicated per-app role most stacks
  here create — not evidenced to be required, kept to avoid an untested
  permissions deviation.
- Three services from one image: `windmill-server` (`MODE=server`, API and UI),
  `worker` (`MODE=worker`, `WORKER_GROUP=default`, general jobs) and
  `worker-native` (`WORKER_GROUP=native`, `NATIVE_MODE=true`, in-process jobs).
  Upstream ships the same three (plus Postgres) in its standard compose file.
- The image has no init system and ships a pre-created `windmill` user at
  uid/gid 1000, so `user: "1000:1000"` with `HOME=/tmp` is safe — the shape
  upstream's own compose comments document for non-root use.

## Not carried, and why

| Upstream component | Why not |
|---|---|
| Caddy | Traefik is this repository's reverse proxy; Caddy in upstream's compose only terminates TLS and fronts the server |
| `windmill_extra` (LSP, debugger, multiplayer) | Optional upstream, and published only as `:latest` — no versioned tag exists, which conflicts with the pinning rule. The web editor works without LSP autocomplete |
| `windmill_indexer` | Full-text job/log search, an Enterprise feature; `replicas: 0` in upstream's own file |
| `windmill_worker_reports` | Commented out in upstream's own file |
| Port `2525` (server SMTP listener for email triggers) | Not HTTP; not routed, not published. The server logs "SMTP server not started because email domain is not set" by default |

## Architecture

```text
Internet → Traefik (TLS, port 443) → windmill-server :8000
                                       │
                          app-internal (internal: true)
                                       │
            db (Postgres 18) ← worker, worker-native ──→ app-egress → internet
```

## What we changed and why

| Change | Reason |
|--------|--------|
| Docker Secret for the database password, `DATABASE_URL` built by `config/entrypoint.sh` | Windmill reads one combined `DATABASE_URL`, with no `_FILE` variant; the same secret file feeds `POSTGRES_PASSWORD_FILE` on the database |
| Worker runs **without** `privileged: true` | Upstream's default worker is privileged for PID-namespace job isolation (`--mount-proc`). This repository grants no privileged containers. The worker logs `unshare … Operation not permitted … Unshare isolation will NOT be available` at start — expected, not a fault |
| `DISABLE_NSJAIL` left at the image default (sandboxing off) | See the NSJAIL finding below |
| `worker` mounts `/tmp` and `/tmp/windmill` as long-syntax tmpfs with `mode: 1023`, plus a bind mount at `/tmp/windmill/cache` | See the two mount findings below |
| `read_only: true` on the server and both workers | Verified with real jobs on read-only workers. The only writable paths are `/tmp` and `/tmp/windmill` (tmpfs) and the worker's cache bind mount |
| `windmill-server` memory 1 GiB | Measured: 470–535 MiB idle and under UI load, 558 MiB peak at start; at 512 MiB the kernel killed it every 30 s |
| Workers join `app-egress`, a per-stack outbound network | On `app-internal` alone a Python job cannot download its interpreter (`dns error … failed to lookup address information`) and dependency installs fail; the native TypeScript job, which downloads nothing, passed. The database stays on `app-internal` only — `getent hosts github.com` from it fails. Same pattern as `apps/nextcloud` and `business/invoiceninja` |
| `APP_TRAEFIK_ACCESS=acc-deny` in `.env.example` | A fresh instance carries a published superadmin password; the router stays closed until `ops/bootstrap-admin.sh` has replaced it |
| `ops/bootstrap-admin.sh` | Replaces `admin@windmill.dev` with an operator account and proves the built-in one no longer authenticates — see below |
| Server healthcheck on `/api/health/status` | Upstream's own unauthenticated status endpoint; it reports database reachability and live workers, which `/api/version` does not |

### Default administrator

A fresh database is seeded with the superadmin `admin@windmill.dev` and the
password `changeme`. Upstream's documented first-login flow logs in with it and
creates a replacement account in the UI; nothing in Windmill's environment
presets either credential. `ops/bootstrap-admin.sh` does the same through the
API, from inside the server container:

1. logs in with the built-in account;
2. creates the operator account as superadmin with a generated 48-character
   hex password, written to `.secrets/windmill_admin_pwd.txt` (mode 600);
3. logs in as the operator, deletes `admin@windmill.dev`;
4. requires the built-in login to answer `400`/`401` before reporting success.

Verified on a fresh database, on the local and the production compose file:
the built-in login returned `200` before and `400` after; the operator login
returned `200`; a second run reported "already bootstrapped" and changed
nothing; both survived a server restart, so the built-in account is not
re-seeded. With the server stopped the script fails with a non-zero exit
instead of reporting success. Until it has run, the default credential is
valid — which is why the router starts at `acc-deny`.

### NSJAIL was tried and did not work

Upstream offers NSJAIL sandboxing (`DISABLE_NSJAIL=false`) as the unprivileged
alternative to PID-namespace isolation. With it enabled and every other
control in place, the first job failed:

```text
nsjail::standaloneMode(nsjconf_t*)():272 Couldn't launch the child process
clone(flags=CLONE_NEWNS|CLONE_NEWCGROUP|CLONE_NEWUTS|CLONE_NEWIPC|CLONE_NEWUSER|CLONE_NEWPID) failed: Operation not permitted
```

Run directly against the image, each step below moved the failure and none
cleared it:

| Added | Result |
|---|---|
| nothing (`cap_drop: ALL`) | `clone(…)` — `Operation not permitted` |
| `cap_add: SYS_ADMIN` | `clone` succeeds; `mount('/', '/', NULL, MS_REC\|MS_PRIVATE)` — `Permission denied` |
| `SYS_ADMIN` + `seccomp=unconfined` | same `mount(…)` error |
| `SYS_ADMIN` + `apparmor=unconfined` | same `mount(…)` error |

`kernel.unprivileged_userns_clone` was `1` on the test VM. The remaining blocker
was not identified; the test VM is a nested-virtualisation Docker host (Colima),
and whether the same call succeeds on a bare-metal Debian host is untested. The
stack therefore ships with NSJAIL off, and job code has no isolation beyond the
worker container itself — non-root, all capabilities dropped, `no-new-privileges`,
read-only root filesystem, and per-stack networks shared with no other stack. **Anyone running untrusted scripts on this worker
should treat that as the boundary.** Windmill's own log also notes NSJAIL for
untrusted environments is an Enterprise feature "allowed to be used for testing
purposes".

### Two mount findings

- **Docker's `tmpfs:` shorthand mounts `noexec`.** Windmill downloads and
  executes language runtimes (Python via `uv`) into `/tmp/windmill/cache`; on
  the default tmpfs the job fails with `Permission denied` on the interpreter.
  The cache is a real bind mount for this reason, and it also persists across
  restarts.
- **A bind mount under `/tmp/windmill` makes Docker pre-create
  `/tmp/windmill` root-owned**, so the worker's own uid then cannot create
  its log directory (`create_dir_all` panics in `tracing_init.rs`). The
  worker mounts `/tmp/windmill` as its own tmpfs, and Compose's `tmpfs.mode`
  takes the decimal value of the bit pattern: `mode: 1777` produced octal
  `3361` (`d-wxrwS--t`); `mode: 1023` produced `1777`.

`windmill-server` and `worker-native` bind-mount nothing under `/tmp/windmill`,
so a plain `tmpfs: [/tmp]` is enough for them.

## Data egress observed

The worker logged a request to `https://hub.windmill.dev/getip` at start
(`external_ip.rs`: "failed to get external IP, workers of this process will
report it as unretrievable"). The server's `hub_api_secret` setting loaded as
`None`. Neither was traced further; `docs/sovereignty/data-egress.md` is the
place to record it once a host run has captured the full picture.

## Known limitation: the UI and the rate limit

The UI's first load issues about 850 requests. Under `sec-2` (burst 50), the
shipped chain, and under `sec-2-spa` (burst 200) part of them get `429` and the
page shows `500 Internal Error`; under `sec-1`, which has no rate limit, it
loads. The chain stays `sec-2` until the security chains are reviewed against
the applications before v1.0 —
[`ROADMAP.md`](../../ROADMAP.md#v10--complete-and-hand-off-ready).

## Verification performed (2026-09-22)

Behind Traefik with TLS:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- Set up as the README describes; the route answered `403` for every path while
  `APP_TRAEFIK_ACCESS=acc-deny`; `ops/bootstrap-admin.sh` created the operator,
  removed `admin@windmill.dev` and reported "already bootstrapped" on a second
  run; after switching to `acc-private` the built-in login answered `400`
  through the route
- `windmill-server` at the shipped 512 MiB was killed by the kernel's cgroup
  OOM killer about every 30 s (`Memory cgroup out of memory: Killed process …
  (windmill) anon-rss:454704kB`), and Traefik answered `404` and `502` between
  restarts. With a 2 GiB ceiling it settled at 500–535 MiB idle, reached
  535 MiB while two browser sessions loaded the UI and 558 MiB starting on a
  restored database; the limit is now 1 GiB, where it ran at 470 MiB with no
  kill
- Through the route as the operator: a Python job on `worker` (`42`), a native
  TypeScript job on `worker-native`; both made an outbound HTTPS call from job
  code and got `200`. Each job's `worker` field named the worker group it ran on
- The UI's first load issues about 850 requests: headless Chromium (Playwright
  1.63) got 584 × `429` under `sec-2` and 412 × `429` under `sec-2-spa`, and the
  page showed `500 Internal Error` both times. Under `sec-1` (no rate limit) all
  requests passed and the operator signed in to the workspace list. The stack
  keeps `sec-2` — see [Known limitation](#known-limitation-the-ui-and-the-rate-limit)
- The UI shows the newest release beside the running one (`v1.816.0` at the
  time); the stack does not switch that lookup off
- A saved script ran before and after `docker compose down` and `up -d`; the job
  history survived
- Restore with the README's single-database dump (`pg_dump windmill`) into a
  fresh cluster: 806 errors, all `role "windmill_user" does not exist` or
  `role "windmill_admin" does not exist`. The server started `healthy` and
  sign-in worked, but every workspace call failed with `role "windmill_admin"
  does not exist`, and `pg_policies` was empty. Loading `pg_dumpall
  --roles-only` first, then the dump: no error, 366 policies, jobs ran. A full
  `pg_dumpall` restored into a fresh cluster the same way (two errors: the
  database and the `postgres` role already exist). borgmatic 2.1.6 dumps with
  `pg_dumpall` when `name: all` has no `format`, and with `pg_dump` for a named
  database; the README now uses `name: all`

**Not yet exercised:** NSJAIL on bare metal; job isolation of any kind.

## Verification performed (2026-09-18)

Against the local test stack (`db`, `windmill-server`, `worker`, `worker-native`)
and against the production `docker-compose.yml` (Docker Secret,
`entrypoint.sh`, `app-egress`) on a throwaway `proxy-public` network, without
Traefik:

- `docker manifest inspect` confirms `ghcr.io/windmill-labs/windmill:1.814.0`
  exists; the pinned image pulled and started
- All services reached `healthy`; `GET /api/health/status` reported
  `"status":"healthy"`, `"database_healthy":true` with the workers alive
- Production: the server connected to Postgres through `DATABASE_URL` built by
  `entrypoint.sh` from the Docker Secret; `DATABASE_URL` is absent from the
  container's configured environment
- Hardening via `docker inspect`, production: no privileged container, no
  published port, uid 1000 and `cap_drop: ALL` on the three Windmill services,
  `read_only` on all three, `no-new-privileges` on all four
- Real jobs through the API as the bootstrapped operator, on read-only workers:
  a Python job on `worker` (`21 * 2` → `42`, and `"hello final-stack"` on the
  local stack) and a native TypeScript job on `worker-native` (`40 + 2` →
  `42`); on the local stack each job id appears in the log of the worker that
  ran it
- The Python job failed on `app-internal` alone and passed once the workers
  joined `app-egress`; the database has no route out
- The default-administrator replacement above

## Upgrade checklist

1. Read the release notes for breaking changes: https://github.com/windmill-labs/windmill/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database and `volumes/postgres` before upgrading
4. Bump `APP_TAG` in `.env.example`
5. `docker compose pull && docker compose up -d`
6. Verify `/api/version`, then submit a real job
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was actually exercised on a real install

A move from an existing Postgres 16 install to 18 is a separate procedure:
dump the whole cluster with `pg_dumpall`, not just the `windmill` database —
Windmill keeps further databases beside it and grants RLS policies to
cluster-level roles. Upstream: https://www.windmill.dev/docs/advanced/self_host#upgrade-postgresql-to-18

## Useful commands

```bash
# Tail logs
docker compose logs windmill-server --follow
docker compose logs worker --follow

# Health, as the server itself reports it
curl -s https://windmill.example.com/api/version
```
