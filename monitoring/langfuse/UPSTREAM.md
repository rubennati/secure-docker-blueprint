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
- **Based on version:** `4.38.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-19)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

## What we use

- `docker.langfuse.com/langfuse/langfuse:4.38.0` and `…/langfuse-worker:4.38.0`.
  Upstream's compose file uses the floating `:4`; not used here.
- `postgres:17.6`, `clickhouse/clickhouse-server:25.12`, `redis:7.4-alpine` and
  `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` — the same five components as
  upstream's compose, pinned. Upstream's MinIO is `cgr.dev/chainguard/minio` with no
  tag; the quay image is a versioned release of the same server.
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
| `HOSTNAME: 0.0.0.0` on web; its healthcheck on `127.0.0.1` | Next.js binds to the address `HOSTNAME` resolves to — the container ID, which resolved to the `app-internal` address on the host, so Traefik got `502` while the healthcheck on `$(hostname)` passed |
| Worker healthcheck on `$(hostname)` | The worker binds to the container's hostname address and refuses loopback; nothing outside the stack connects to it |
| PostgreSQL data mounted at `/var/lib/postgresql/data` | The 17.x image declares that path as a `VOLUME`; mounted one level up, the cluster stayed in an anonymous volume and each `down` + `up` started on a new, empty one |
| ClickHouse: `user: 101:101`, `read_only`, tmpfs on `users.d` | The image's entrypoint writes the user definition there at start. A tmpfs over `config.d` was tried and removed: it hid the image's `listen_host` file, so port 9000 was refused from other containers |
| ClickHouse `pids: 2000` | At 500 the entrypoint failed with `fork: retry: Resource temporarily unavailable`; ClickHouse's threads count against the limit |
| `TELEMETRY_ENABLED=false` | Upstream's usage telemetry |

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

**Not yet exercised:** Traefik routing and TLS; the browser UI beyond the login
API; media uploads (not supported, see README); prompt management, evaluations and
the in-app agent; the legacy `/api/public/ingestion` endpoint (in v4 it accepts only
score events, so traces go through OpenTelemetry); backup and restore; upgrade from
a v3 database.

## Upgrade checklist

1. Read the release notes: https://github.com/langfuse/langfuse/releases and the
   upgrade guides at https://langfuse.com/self-hosting/upgrade
2. Check the GitHub Security tab for advisories against the current version
3. Back up PostgreSQL, the ClickHouse and MinIO volumes, and the secrets
4. Bump `APP_TAG` in `.env.example` (web and worker move together)
5. `docker compose pull && docker compose up -d`; migrations run at start
6. Log in, then send a test trace
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install

A move from v3 to v4 is a separate procedure: upstream's guide covers the
ClickHouse migration.
