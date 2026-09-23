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
- **Last verified:** 2026-09-23 (v2.41.0) — behind Traefik with TLS: the first sign-up and workspace, a company over the interface and over REST, the interface under the shipped `sec-2-spa-xl` without a `429`, a restart, and the README's restore

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

## The interface and the rate limit

The first load issues 412 requests. Assets are served with
`cache-control: public, max-age=0`, so a returning browser revalidates every one
of them instead of using its cache. Measured under the shipped `acc-tailscale`:

| Chain | Load | Requests | `429` |
|---|---|---|---|
| `sec-2` (burst 50) | first | 412 | 302 |
| `sec-2-spa` (burst 200) | first | 412 | 130 |
| `sec-2` | warm browser | 379 | 289 |
| `sec-2-spa` | warm browser | 412 | 159 |
| `sec-1` (no rate limit) | warm browser | 518 | 0 |

Three cold loads in a row under `sec-2`: 1,216 requests, 919 of them `429`. The
interface stays blank under both.

Measured again on 2026-09-23 under `sec-2-spa-xl`, whose bucket holds one whole
first load: 516 requests cold, 505 on a reload, and three further cold loads of
516 each — every one answered, no `429`. That is the chain `.env.example` now
ships.

## Verification performed (2026-09-23)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2-spa-xl`:

- Five loads of the interface in a row — cold, a reload, and three more cold
  loads: 516, 505, 516, 516, 516 requests, every one answered, no `429`
- Signed in, and the company created in September read back over REST
  (`GET /rest/companies` `200`)
- The interface requests `twentyhq.github.io` in the visitor's browser; those
  requests were blocked in the browser and never left it

**Not yet exercised:** API keys (creating one through the session's GraphQL call
got `403`); mail and calendar sync.

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale`; the interface under
`sec-1` (see above):

- A client outside the access policy's ranges got `403`, over IPv4 and IPv6
- The first sign-up in the browser created the workspace and its first user; an
  uninvited second sign-up was refused
  (`SignUpInWorkspace: User does not have access to this workspace`)
- A company created in the interface and read back over REST with the session
  (`GET /rest/companies` `200`); REST writes with the session alone got `403`
- The interface requests company logos from `twenty-icons.com`, and
  `twentyhq.github.io`, in the visitor's browser
- After `docker compose down` and `up`: the interface in 572 requests, the company
  still there
- Backup as the README describes; restore into an empty database without errors,
  the archive unpacked — the interface loaded (572 requests) and the company was
  back
- Peaks: server 1,033 MiB, worker 751 MiB, PostgreSQL 106 MiB, Redis 20 MiB

**Not yet exercised:** API keys (creating one through the session's GraphQL call
got `403`); mail and calendar sync; the interface under the shipped `sec-2`.

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
