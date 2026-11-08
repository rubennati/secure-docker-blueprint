# Upstream Reference

## Source

- **Image:** https://github.com/langfuse/langfuse/pkgs/container/langfuse
- **GitHub:** https://github.com/langfuse/langfuse
- **Docs:** https://langfuse.com/self-hosting
- **License:** MIT (core; the `ee/` directories are under a separate enterprise licence)
- **Use restrictions:** none for the MIT-licensed portion; content under `ee/`, `web/src/ee/` and `worker/src/ee/` is under the separate licence in `ee/LICENSE` — https://github.com/langfuse/langfuse/blob/main/LICENSE · checked 2026-09-21
- **Edition gating:** project-level RBAC roles, audit logs, data retention policies, server-side data masking, SCIM with the organisation management API, and the instance management API require a paid licence key when self-hosting — https://langfuse.com/self-hosting/license-key · checked 2026-09-21
- **Commercial model:** paid self-hosted edition — https://langfuse.com/self-hosting/license-key · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** United States · ClickHouse, Inc. (Langfuse has been part of it since 2026-01) · non-EU
- **Domain:** AI and local AI
- **Role:** LLM observability: traces, scores and prompts from any instrumented application
- **Last verified:** 2026-09-22 (4.38.0) — behind Traefik with TLS: the UI, the Python SDK sending traces, scores and a prompt, a restart, and a restore

## What we use

- `docker.langfuse.com/langfuse/langfuse:4.76.0` and `…/langfuse-worker:4.76.0`.
  Upstream's compose file uses the floating `:4`; not used here.
- `postgres:18.6`, `clickhouse/clickhouse-server:26.10.3.7`, `redis:8.10.3-alpine` and
  `pgsty/silo:RELEASE.2026-10-26T00-00-00Z` — the same five components as upstream's compose, pinned.
  Upstream's object store is `cgr.dev/chainguard/minio` with no tag; Silo is a
  maintained MinIO fork with release tags (see "Object store: Silo instead of MinIO").
- This is upstream's smallest self-hosted shape (Docker Compose). Nothing is
  collapsed: the worker, ClickHouse, Redis and blob storage are all required by the
  v4 architecture.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `NAME__FILE` into `NAME` | None of the images has `_FILE` variants; upstream sets secrets as plain environment variables |
| `config/redis-entrypoint.sh` | Password in a tmpfs config file instead of `--requirepass` on the command line |
| Provisioning through `LANGFUSE_INIT_*` | Creates the organisation, project, key pair and first user without opening registration; `AUTH_DISABLE_SIGNUP=true` afterwards (verified: sign-up returns "Sign up is disabled") |
| Traefik only in front of `langfuse-web`; MinIO, ClickHouse, Redis, PostgreSQL and the worker on `app-internal` | Upstream publishes MinIO's port 9090 and the web port on all interfaces; only the UI and API need to be reachable |
| Explicit `command` on web and worker | Overriding `entrypoint` clears the image's `CMD`; without it the container exits `0` immediately |
| Web at 2 GB with `NODE_OPTIONS=--max-old-space-size=1536` | At a 1 GB limit the Node heap (~512 MB default) was exhausted during startup and the container restarted in a loop |
| `HOSTNAME: 0.0.0.0` on web; its healthcheck on `127.0.0.1` | Next.js binds to the address `HOSTNAME` resolves to — the container ID, which can resolve to the `app-internal` address; Traefik then gets `502` while the healthcheck on `$(hostname)` passes |
| Worker healthcheck on `$(hostname)` | The worker binds to the container's hostname address and refuses loopback; nothing outside the stack connects to it |
| PostgreSQL data mounted at `/var/lib/postgresql/data` | The 17.x image declares that path as a `VOLUME`; mounted one level up, the cluster stayed in an anonymous volume and each `down` + `up` started on a new, empty one |
| ClickHouse: `user: 101:101`, `read_only`, tmpfs on `users.d` | The image's entrypoint writes the user definition there at start. A tmpfs over `config.d` was tried and removed: it hid the image's `listen_host` file, so port 9000 was refused from other containers |
| ClickHouse `pids: 2000` | At 500 the entrypoint failed with `fork: retry: Resource temporarily unavailable`; ClickHouse's threads count against the limit |
| `TELEMETRY_ENABLED=false` | Upstream's usage telemetry |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-private` and `sec-2`:

- A client outside the access policy's ranges got `403` on the route, over IPv4
  and IPv6
- The route answered `502` on the first start: `langfuse-web` listened on its
  `app-internal` address only (`192.168.160.7:3000`), Traefik connected to the
  `proxy-public` one, and the healthcheck on `$(hostname)` passed. With
  `HOSTNAME: 0.0.0.0` it listened on all addresses and the route answered
- Headless Chromium (Playwright 1.63): sign-in and the organisation page,
  152 requests, all `200` under `sec-2`
- Python SDK 4.15.4 from a container sending to the routed host: `auth_check`
  `True`; a span with a generation and a trace score; a text prompt created and
  fetched back (`v1`, compiled). The UI listed the trace under Tracing and the
  prompt under Prompts; `/api/public/v2/observations` returned the span and the
  generation. The spans went through `/api/public/otel/v1/traces` into the
  `events_core` and `events_full` tables; `traces` and `observations` stayed
  empty, so `/api/public/traces/<id>` answered `404`
- 300 traces with a generation and a score each, sent in 4.3 s: 602 rows in
  `events_core`, 301 scores. Peaks during these checks: ClickHouse 1.28 GiB and
  739 PIDs, web 951 MiB, worker 618 MiB, MinIO 268 MiB, PostgreSQL 145 MiB,
  Redis 8 MiB
- The worker logged `Queue job trace-upsert errored: Error: Socket timeout`
  from `ioredis` every 30 s from the first start, before any trace was sent;
  ingestion was not affected
- After `docker compose down` and `up -d`, and in the first backup, the prompt
  was gone from PostgreSQL: the mount was one level above the 17.x image's data
  `VOLUME`, and three dangling anonymous volumes held one cluster each — from
  the first start, the restart and the restore. The organisation, project, key
  pair and administrator reappeared each time from `LANGFUSE_INIT_*`. With the
  data mounted at `/var/lib/postgresql/data` the prompt survived the restart
- Backup as the README described: `tar` warned `file changed as we read it` on
  ClickHouse's `store/`, which kept running; with ClickHouse and MinIO stopped
  the archive was clean. The README now stops both
- Restore into empty volumes: the dump loaded with `ON_ERROR_STOP` and no error,
  the archive unpacked — the prompt came back through the API, ClickHouse held
  606 events and 303 scores, and the SDK sent again with the restored keys

**Not yet exercised:** evaluations, which the `trace-upsert` queue feeds; media
uploads (not supported, see README); the in-app agent; upgrade from a v3
database.

## Verification performed (2026-09-19)

Against the production `docker-compose.yml` (Docker Secrets, `entrypoint.sh`,
`app-internal`) on a throwaway `proxy-public` network without Traefik, and against
`docker-compose.local.yml` on empty volumes:

- All six services reached `healthy`; migrations for PostgreSQL (438) and
  ClickHouse applied on the empty stores
- Provisioning from the environment: the project key pair from the Docker Secrets
  authenticated (`200`); no key and a wrong key returned `401`
- A real OpenTelemetry trace with one generation was sent to
  `/api/public/otel/v1/traces`, stored as an event file in MinIO, processed by the
  worker and read back from ClickHouse through `/api/public/v2/observations`
- The administrator logged in through the UI's credentials provider and the session
  returned the account; a wrong password produced no session
- Sign-up with a valid password was refused ("Sign up is disabled")
- After `docker compose down` and `up`, the trace was still readable
- Hardening from `docker inspect`: uid, `read_only`, `cap_drop: ALL`,
  `no-new-privileges` as documented, no published port; the secret values are absent
  from the configured environment of web, worker, ClickHouse and MinIO; the worker
  and ClickHouse have no route out

## Object store: Silo instead of MinIO

MinIO withdrew its public container images on 2026-09-24: `quay.io/minio/minio`
answers `401 Unauthorized`, the Docker Hub repository is gone, and
[`minio/minio`](https://github.com/minio/minio) was archived on GitHub with its last
push on 2026-04-24. The tag pinned here before, `RELEASE.2025-09-07T16-13-09Z`,
could not be pulled from anywhere public, so the stack did not start.

The store is now [`pgsty/silo`](https://github.com/pgsty/silo) (AGPL-3.0), a
maintained MinIO fork with release tags on Docker Hub. Upstream's compose uses `cgr.dev/chainguard/minio`, which publishes `latest` only and cannot be pinned; `business/plane`'s upstream names Silo. It reads
MinIO's variables (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD_FILE`) and serves the S3
API on port 9000, so the service keeps the name `minio` and its clients are
unchanged. The image has no `mc`; the healthcheck is Silo's own
`silo healthcheck ready`. It runs as uid 1000 with `cap_drop: ALL` and no
capability added.

Not tested: a data directory written by the old MinIO image. Every run of this
stack since the withdrawal started empty.

## Version notes

- Moved to `4.76.0` on 2026-11-08 (released 2026-11-05), web and worker
  together, run on the lab host. No breaking change, variable or migration is
  labelled; the release is small fixes and refactoring, and web and worker move
  to the current Langfuse SDK internally.
- Moved to `4.75.0` on 2026-11-05 (released 2026-11-04), web and worker
  together, not run on a host at this tag. The releases from 4.51.0 to 4.75.0
  carry no breaking-change section; migrations still run at start. The web and
  worker images moved from `node:24-alpine` to Red Hat UBI 9 micro with the
  `nodejs:24` RPM: no busybox and no package manager, but bash, sed, wget and
  coreutils remain; uid 1001 and the `dumb-init` entrypoint are unchanged.
  The image has no `hostname` binary, so the healthchecks that called
  `$(hostname)` now read Docker's `HOSTNAME` variable. ClickHouse migration
  0050 now materializes the `scores` columns it indexes (PR #19443); an
  install left on a dirty migration 50 recovers with `migrate force 49` and a
  redeploy. Upstream's compose moved ClickHouse to `26.3.62.3`; the release
  notes do not make it a requirement, and `CH_TAG` stays at `25.12`. New
  optional variables: `LANGFUSE_LLM_CONNECTION_ALLOWED_HOSTS`,
  `LANGFUSE_WEBHOOK_ALLOWED_HOSTS`,
  `LANGFUSE_BLOB_STORAGE_ENDPOINT_ALLOWED_HOSTS`,
  `LANGFUSE_EXTERNAL_MEDIA_STORAGE_ENDPOINT_ALLOWED_HOSTS`,
  `LANGFUSE_OUTBOUND_BLOCKED_IP_SEGMENTS`, `LANGFUSE_TRUSTED_PROXY_COUNT`,
  `LANGFUSE_DISABLE_SIGNUP_ONBOARDING`,
  `LANGFUSE_S3_MEDIA_UPLOAD_REQUEST_TIMEOUT_MS`. Security items in the notes:
  Node.js 24.22.1 fixes in the images, and webhook, PostHog and storage
  secrets are required again when their destination changes (PRs #19261,
  #19566); no GHSA published.
- Moved `postgres` from `17.6` to `18.6` on 2026-11-05, not run on a host at
  this tag. PostgreSQL 18 support: Langfuse supports Postgres 12 and newer (v4
  needs 15 or newer), with no upper bound
  (https://langfuse.com/self-hosting/deployment/infrastructure/postgres). The 18
  image keeps its cluster under `/var/lib/postgresql/18/docker`; `PGDATA:
  /var/lib/postgresql/data` in both compose files keeps it on the existing
  mount. A new major does not read the old cluster, so existing data moves by
  dump and restore: before the tag changes, `docker compose exec postgres sh -c
  'pg_dumpall -U "$POSTGRES_USER"' > dump.sql`; `docker compose down`; move
  `./volumes/postgres` aside; set the new tag; `docker compose up -d postgres`;
  `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d postgres'
  < dump.sql` (errors that the bootstrap role and database already exist are
  expected); then `docker compose up -d`. A return to the old major is only a
  restore of that dump.
- Moved `clickhouse/clickhouse-server` from `25.12` to `26.10.3.7` on 2026-11-05,
  not run on a host at this tag. The tag keeps the minor precision the stack
  used; `26.10` points at 26.10.3.7 (2026-10-26), the newest stable release.
  Langfuse v4 needs ClickHouse 25.12 or newer and names no upper bound
  (https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse).
  ClickHouse upgrades its data in place at the first start; the way back is a
  restore of the volume backup. Upstream's own compose runs 26.3.62.3; the 26.1
  to 26.8 notes were not reviewed item by item here. Backward-incompatible
  changes in 26.9 and 26.10 that touch this stack
  (https://clickhouse.com/docs/whats-new/changelog): the pre-analyzer query path
  is removed (the analyzer has been the default since 24.3); 26.9 moves the
  default compression for larger MergeTree parts and network traffic to ZSTD(3);
  `system.metric_log` switches to a bucketed schema and the old table is renamed
  to `metric_log_0` at the first start; system log tables are configured through
  `system_tables.*` and some fall back to a default TTL; and the server installs
  a seccomp filter at start (`trap` in the image's `config.xml`). The seccomp
  filter is the item to watch on a host: the container keeps Docker's default
  seccomp profile, which allows the `seccomp` call, and `no-new-privileges` is
  already set; if the server refuses to start in a sandbox that blocks it,
  upstream's fix is `seccomp` set to `log` or `disabled` in a `config.d` file.
  `arrayCount` now returns `UInt64` and `accurateCast` to `Nullable` throws
  instead of returning NULL; neither appears in Langfuse's release notes as a
  problem.
- Moved `redis` from `7.4-alpine` to `8.10.3-alpine` on 2026-11-05, a new major, not
  run on a host at this tag; the tag follows the 8.10 patch releases (8.10.3,
  2026-10-26). Redis 8 is offered under RSALv2, SSPLv1 or AGPLv3 at the user's
  choice (7.4: RSALv2 or SSPLv1). The image bundles the Query Engine, JSON, time
  series and probabilistic data types as modules, which the image's entrypoint loads
  at start on amd64 and arm64; this stack uses none of them. 8.x reads the 7.4 data
  files in place, but Redis does not load files written by a newer version, so a
  rollback needs the backup of the Redis data. The one potentially breaking change
  upstream lists: `GETRANGE` with an out-of-range negative end returns an empty
  string. Security fixes in the 8.10 line: CVE-2026-62356 (8.10.1, heap write when
  loading a Count-min sketch from an RDB file), queued `MULTI` commands keeping
  access to keys whose ACL permission was revoked (8.10.2), and a cluster-bus
  overflow that needs cluster mode (8.10.3). The 7.4 line still receives fixes
  (7.4.12, 2026-10-26); the move is to the newest stable line, not away from an
  unmaintained one. Langfuse requires Redis 7 or newer with `maxmemory-policy
  noeviction`, which this stack's entrypoint script sets. This service starts as UID
  999 through its own `config/redis-entrypoint.sh`, which execs `redis-server`
  directly, so the image entrypoint's privilege handling and module loading do not
  apply; no compose change. Sources:
  https://github.com/redis/redis/releases/tag/8.0.0,
  https://github.com/redis/redis/releases/tag/8.10.3,
  https://github.com/redis/docker-library-redis/blob/release/8.10/alpine/docker-entrypoint.sh,
  https://langfuse.com/self-hosting/deployment/infrastructure/cache

## Upgrade checklist

1. Read the release notes: https://github.com/langfuse/langfuse/releases and the
   upgrade guides at https://langfuse.com/self-hosting/upgrade
2. Check the GitHub Security tab for advisories against the current version
3. Back up PostgreSQL, the ClickHouse and MinIO volumes, and the secrets
4. Bump `APP_TAG` in `.env.example` (web and worker move together)
5. `docker compose pull && docker compose up -d`; migrations run at start
6. Log in, then send a test trace
7. Add **Last verified** only if the
   upgrade was exercised on a real install

A move from v3 to v4 is a separate procedure: upstream's guide covers the
ClickHouse migration.
