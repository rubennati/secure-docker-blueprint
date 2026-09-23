# Upstream Reference

## Source

- **Image:** https://github.com/plausible/community-edition/pkgs/container/community-edition
- **GitHub:** https://github.com/plausible/analytics
- **Deployment:** https://github.com/plausible/community-edition
- **Docs:** https://github.com/plausible/community-edition/wiki
- **License:** AGPL-3.0 (application) / MIT (the JavaScript tracker, deliberately, so a website that embeds it is not pulled into the AGPL)
- **Use restrictions:** none — the name and logo are trademarks with published guidelines, which is a naming rule rather than a use restriction — https://plausible.io/trademark · checked 2026-09-23
- **Edition gating:** no feature is held back from Community Edition. Upstream's own comparison names infrastructure, support, the Looker Studio connector, and a release cadence of twice a year instead of continuous — https://github.com/plausible/analytics#can-plausible-be-self-hosted · checked 2026-09-23
- **Commercial model:** free self-hosted — https://plausible.io/self-hosted-web-analytics · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** Estonia · Plausible Insights OÜ · EU
- **Domain:** Business operations
- **Role:** Cookie-free, GDPR-oriented web analytics — the measurement side of a company website, without a consent banner
- **Based on version:** `v3.2.1`

## Project maturity

29 192 stars on the application, pushed 2026-09-23; 2 873 on the deployment
repository, pushed 2026-05-15. CE is described by upstream as a long-term
release published **twice a year**, so the image lagging the cloud service is
the design rather than neglect.

## What we use

- `ghcr.io/plausible/community-edition:v3.2.1`, one container.
- `postgres:18.6-alpine` for accounts, sites and settings.
- `clickhouse/clickhouse-server:26.8.10.6-alpine` for the events.
- Four ClickHouse configuration files from the community-edition repository
  (MIT), vendored under `config/clickhouse/` so the stack does not depend on a
  checkout of it:

  | File | What it does |
  |---|---|
  | `logs.xml` | Log level `warning`, a 30-day TTL on `query_log`, and seven other system log tables removed. Without it a small instance spends most of its writes on its own telemetry tables |
  | `ipv4-only.xml` | `listen_host 0.0.0.0`. Docker bridge networks have no IPv6 by default, and the server otherwise logs a failure to bind `[::]` |
  | `low-resources.xml` | `mark_cache_size` 500 MB instead of the default 5 GB |
  | `users.d/default-profile-low-resources-overrides.xml` | One thread, 8192-row blocks, no parallel parsing or formatting |

## What we changed and why

| Change | Reason |
|--------|--------|
| The first account is created by `ops/create-admin.sh` | Until one exists, Plausible sends `/login` and `/sites` to `/register` whatever `DISABLE_REGISTRATION` says, and that form makes whoever completes it the owner |
| `DISABLE_REGISTRATION=true` | Upstream's CE default is `invite_only`. Once the owner exists, further accounts are invited from a site's settings, so nothing needs the sign-up form again |
| ClickHouse `26.8` instead of upstream's `24.12` | Upstream's compose pins a December 2024 release that is out of support, while upstream's own CI runs `25.11` — so the pin is stale rather than a requirement. Verified here against the migrations and an ingested event |
| `postgres:18.6-alpine` with `PGDATA` set | Upstream pins `16-alpine`. Same `PGDATA` pattern as `apps/defectdojo` |
| Docker Secrets named `SECRET_KEY_BASE`, `DATABASE_URL`, `CLICKHOUSE_DATABASE_URL`, `TOTP_VAULT_KEY` | Plausible reads each setting from `/run/secrets/<NAME>` before the environment (`CONFIG_DIR`, default `/run/secrets`), so no wrapper and no `_FILE` suffix is needed. Upstream's compose passes all four as environment variables |
| `read_only: true`, `cap_drop: ALL`, `no-new-privileges` | Upstream's compose sets none of them. The image already runs as uid 999 and writes only to its data volume and `/tmp` |
| No `ports:` | Upstream publishes `HTTP_PORT` to the host. Traefik reaches the container over the proxy network instead |
| ClickHouse and PostgreSQL on `internal: true` | Upstream puts all three on one bridge network |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | The safe start. It also means no measurement from outside the VPN — the README says what to change for a public website, and why it is a second router rather than a different value here |

## Verified on the images (2026-09-23)

Not a host verification: this ran the stack's own files with a throwaway
network and no Traefik router.

- `ops/init.sh` → `docker compose up -d` → `ops/create-admin.sh`: the account
  was created (`id 1`, `email_verified: true`), and its password verifies
  against the stored bcrypt hash while a wrong one does not.
- **Migrations and ingestion run on ClickHouse 26.8.** Two events posted to
  `/api/event` came back out of `events_v2` with hostname, path, browser and
  operating system parsed.
- **Geolocation needs no download.** The image ships
  `priv/geodb/dbip-country.mmdb.gz`, and an event from a routable address was
  recorded with the right country code. A MaxMind licence key is an option, not
  a requirement, and without either setting the application refuses to start.
- **The sign-up form is open until the first account exists.** With
  `DISABLE_REGISTRATION=true`, a fresh instance still answered `/register` with
  200 and redirected `/login` and `/sites` to it. After `ops/create-admin.sh`,
  `/register` redirects to `/login`.
- **Registration and login are LiveView forms**, so they submit over a
  WebSocket; a scripted form POST is answered 404 and 403 respectively. That is
  why the bootstrap goes through the release console rather than through curl.
- **There is no upstream CLI for creating a user.** `/entrypoint.sh` dispatches
  `run` and `db <name>`, where `<name>` is one of the four scripts in `/app`:
  `createdb`, `migrate`, `pending-migrations`, `rollback`, `seed`.
- **`rpc` evaluates on the running node**, so values passed with
  `docker compose exec -e` never reach it — `ops/create-admin.sh` hands its
  three values over as files in the container's tmpfs and removes them
  afterwards.
- **The one outbound call is the timezone database.** `tzdata` ships with
  `autoupdate: :enabled` and polls IANA; the volume grows a
  `tzdata_data/latest_remote_poll.txt` and a `tmp_downloads/` to match.
  `ERL_ZFLAGS="-tzdata autoupdate disabled"` turns it off — measured: the
  application stays healthy and `Application.get_env(:tzdata, :autoupdate)`
  reads `:disabled`. It is commented out rather than set, because stale
  timezone rules are a correctness problem in an analytics tool.
- Session cookie: `secure; HttpOnly; SameSite=Lax`.
- The data volume must belong to uid 999 before the first start; otherwise
  `tzdata` fails with `eacces` on `/var/lib/plausible/tzdata_data` and the VM
  terminates. The container does not chown it — nothing in it runs as root.
- Idle after migrations: application 298 MiB anonymous plus 67 MiB page cache,
  ClickHouse 165 MiB plus 5 MiB, PostgreSQL 29 MiB plus 92 MiB.
- A restart of the application came back healthy with no read-only errors.

What a host run still has to establish: the route through `core/traefik`, the
`sec-2` chain against the dashboard, a browser completing the LiveView sign-in,
the two-router split for a public website, a mail path for invitations and
password resets, and a restore from the volumes.

## Upgrade checklist

1. Read the release notes — https://github.com/plausible/analytics/releases
2. Check the wiki's upgrade page for a required intermediate version —
   https://github.com/plausible/community-edition/wiki/upgrade
3. Raise `APP_TAG` in `.env` and in `.env.local.example`
4. `docker compose pull && docker compose up -d` — the start command runs
   `db createdb && db migrate` itself, so there is no separate step
5. `docker compose logs plausible-app` — no stack traces, and the health check
   green
6. Post one event and confirm it appears in the dashboard
7. Record the result in `Last verified` once it ran behind `core/traefik`

A PostgreSQL major upgrade is a separate procedure —
https://github.com/plausible/community-edition/wiki/upgrade-postgresql

## Diff against upstream

```bash
# Upstream's own compose — published port, no read_only, secrets as env vars
curl -s https://raw.githubusercontent.com/plausible/community-edition/master/compose.yml

# Every setting the release reads, with its defaults
docker run --rm --entrypoint sh ghcr.io/plausible/community-edition:v3.2.1 \
    -c 'cat /app/releases/*/runtime.exs'
```
