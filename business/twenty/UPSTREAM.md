# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/twentycrm/twenty
- **GitHub:** https://github.com/twentyhq/twenty
- **Docs:** https://twenty.com/developers/section/self-hosting
- **License:** AGPL-3.0 (core; files marked `@license Enterprise` are under a separate enterprise licence, and the SDK and UI packages are MIT)
- **Use restrictions:** none for the AGPL-3.0 portion; individual files carrying a `/* @license Enterprise */` comment at the top are under a separate commercial licence — https://github.com/twentyhq/twenty/blob/main/LICENSE · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** United States · Twenty.com PBC · non-EU
- **Domain:** Business operations
- **Role:** CRM: companies, people, opportunities and tasks, with an extensible data model and an API
- **Edition gating:** files marked `@license Enterprise` at the top are covered by a commercial licence rather than the AGPL-3.0 — https://github.com/twentyhq/twenty/blob/main/LICENSE · checked 2026-09-21
- **Based on version:** `v2.41.0`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

The origin comes from Twenty's terms of service, which name Twenty.com PBC as a
public benefit corporation incorporated in Delaware.

## What we use

- `twentycrm/twenty:v2.41.0` for both server and worker, as upstream's compose does.
  Upstream pins `:latest`; not used here.
- `postgres:16.14` — upstream's compose runs the PostgreSQL 16 line.
- `redis:7.4-alpine` — upstream's compose uses an untagged `redis`.
- Local file storage, upstream's default; the S3 option is not configured.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` builds `PG_DATABASE_URL`, `REDIS_URL` and `ENCRYPTION_KEY` from Docker Secrets | None has a `_FILE` variant; upstream sets them as plain variables, with a default database password of `postgres` |
| `command` restated on both services | Overriding the entrypoint clears the image's `CMD` |
| Redis with a password | Upstream runs it without one; here it is set from a secret, through a tmpfs config file rather than the command line |
| `read_only: true` on server and worker | Verified: migrations, sign-up, workspace activation, records and a restart |
| Worker on `app-internal` only | It needs no route out for the CRM itself; mail and calendar sync would, see README |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The first account creates the workspace |

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, wrapper,
`app-internal`) on a throwaway `proxy-public` network without Traefik, with calls
made through the application's own GraphQL and REST APIs from inside the server
container:

- All four services started; the server migrated the empty database and reported
  healthy
- The first sign-up succeeded; a second sign-up with the same address was refused
  ("User already exists")
- The first user created a workspace and activated it
- A second, uninvited person was refused: "New workspace setup is disabled"
- With a workspace token, a company was created over `POST /rest/companies` and
  listed; an invalid token returned 403; a wrong password returned "Wrong password"
- Upstream seeds sample companies into a new workspace; they were present
- The worker processed jobs from the shared Redis queues — completed jobs in the
  entity-event, workspace and webhook queues, none failed, none waiting
- After `docker compose down` and `up`, the created company was still there
- Hardening from `docker inspect`: server and worker uid 1000, read-only, all
  capabilities dropped; Redis uid 999, read-only; no published port; the secret
  values absent from the configured environment; worker and database without a
  route out

**Not yet exercised:** Traefik routing and TLS; the browser interface; invitations;
mail and calendar sync (which need outbound access, see README); SSO; S3 storage;
backup and restore; an upgrade across versions.

## Upgrade checklist

1. Read the release notes: https://github.com/twentyhq/twenty/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database, `volumes/storage` and `encryption_key.txt`
4. Bump `APP_TAG` in `.env.example` — server and worker move together
5. `docker compose pull && docker compose up -d`; the server runs the upgrade
   commands at start
6. Log in and open a record
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
