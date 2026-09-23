# Plausible Community Edition

Cookie-free web analytics for your own sites: no consent banner to click away,
no cross-site identifiers, and the raw data on your own disk. Upstream:
[plausible/analytics](https://github.com/plausible/analytics), deployed the way
[plausible/community-edition](https://github.com/plausible/community-edition)
describes. It is the privacy-first counterpart to
[`business/matomo`](../matomo/), which measures the same thing in far more
detail and with far more to configure.

No feature is held back from the Community Edition. What the hosted service
adds is infrastructure, support, the Looker Studio connector, and continuous
releases instead of two a year.

## Architecture

```text
Traefik ──http──→ plausible-app :8000
                       │
                       ├──→ plausible-db        :5432  accounts, sites, settings
                       └──→ plausible-events-db :8123  every pageview (ClickHouse)
```

Both databases sit on an internal network with no published port. The event
store is why this stack wants more memory than its page count suggests, and the
four files under `config/clickhouse/` are what keep a single instance from
behaving like a cluster node.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # secrets and volume directories
sudo chown -R 999:999 volumes/plausible

docker compose up -d            # the start command migrates both databases
ops/create-admin.sh             # the first account — do this immediately
```

**`ops/create-admin.sh` is not optional.** Until one account exists, Plausible
sends `/login` and `/sites` to `/register` no matter what
`DISABLE_REGISTRATION` says, and whoever completes that form owns the instance.
The script creates the account from the command line and prompts for the
password, which is handed to the container as a file rather than as an argument
— so it stays out of the process list and out of your shell history. Once it
has run, `/register` redirects to `/login`.

Further accounts are invited from a site's settings, not created with this
script.

### Ownership of the data volume

The image runs as uid 999 and nothing in it runs as root, so it cannot fix the
ownership itself. Without the `chown` the application terminates on
`eacces` while starting its timezone database — a crash whose message says
nothing about permissions on the volume.

## Splitting the dashboard from the tracker

Plausible serves two different audiences on one host name:

| Path | Who has to reach it |
|---|---|
| `/js/script.js`, `/api/event` | every visitor's browser, from anywhere |
| everything else | you |

`APP_TRAEFIK_ACCESS=acc-tailscale` closes both, which is right while the first
account is created, and right for measuring an intranet site. For a public
website the tracker has to be reachable while the dashboard stays closed — and
that is a second router, not a different value here:

```yaml
# additional labels on plausible-app
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-tracker.rule=Host(`${APP_TRAEFIK_HOST}`) && (PathPrefix(`/js/`) || Path(`/api/event`))"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-tracker.entrypoints=websecure"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-tracker.tls=true"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-tracker.tls.options=${APP_TRAEFIK_TLS_OPTION}@file"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-tracker.middlewares=acc-public@file,${APP_TRAEFIK_SECURITY}@file"
```

Traefik matches the longest rule first, so the tracker router wins for those two
paths and the dashboard router keeps everything else VPN-only. It is the same
split [`business/listmonk`](../listmonk/) uses for its subscriber pages and
[`apps/shlink`](../../apps/shlink/) for its short links. **This has not been
run on a host** — it is written from the same rule that was measured there.

## Try it locally

Runs on `http://localhost:8000` without Traefik, and here the sign-up form is
what creates the first account — on a loopback port that is fine.

```bash
cp .env.local.example .env.local
ops/init.sh
sudo chown -R 999:999 volumes/plausible
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8000
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Security model

- **The sign-up window is closed from the command line**, before anyone else
  can reach the host name. See Setup.
- **`acc-tailscale` by default.** Read "Splitting the dashboard from the
  tracker" before changing it: opening this value opens the dashboard too.
- **Four settings are Docker Secrets, read natively.** Plausible looks in
  `/run/secrets/<NAME>` before the environment, so `SECRET_KEY_BASE`,
  `DATABASE_URL`, `CLICKHOUSE_DATABASE_URL` and `TOTP_VAULT_KEY` need no
  wrapper and no `_FILE` suffix. Upstream passes all four as environment
  variables, where `docker inspect` shows them.
- **ClickHouse has no password**, and the compose file says so rather than
  implying otherwise. It is on an internal network, publishes no port, and has
  `CLICKHOUSE_SKIP_USER_SETUP=1` — upstream's arrangement. If that stops being
  acceptable, a user and a password in `CLICKHOUSE_DATABASE_URL` is the change.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** on the
  application; upstream's compose sets none of them.
- **Visitor addresses are not stored.** Plausible derives a daily-rotating hash
  and a country from the address and keeps neither the address nor a cookie.
  That is what it measures with, and the reason this stack stands next to
  Matomo rather than instead of it.
- **One outbound call:** the timezone database. See below.

## What leaves the host

- **IANA, for timezone rules.** The Elixir release ships `tzdata` with
  auto-update enabled and polls for a newer timezone database. Nothing about
  the instance is sent — it is a download — but it is a connection, and it is
  the only one this stack makes on its own. To stop it, uncomment `ERL_ZFLAGS`
  in `docker-compose.yml` and accept that timezone rules go stale; measured
  working, see `UPSTREAM.md`.
- **Nothing else by default.** Geolocation comes from a DB-IP database inside
  the image; no MaxMind key, no download. Sentry, OpenTelemetry and the Google
  integration are all off unless you give them credentials.

## Known limits

- **`sec-2` is not measured against the dashboard**, which is a LiveView
  application and therefore holds a WebSocket open. Nor has a rate limit been
  measured on `/api/event`, where one request per visitor is the normal case
  and a shared limit is the wrong shape.
- **Mail is not configured.** Invitations and password resets need
  `MAILER_ADAPTER` and the `SMTP_*` settings; without them the only account is
  the one `ops/create-admin.sh` made.
- **ClickHouse is one version upstream does not test.** Upstream's compose
  pins 24.12, which is out of support; upstream's CI runs 25.11. This pins a
  current release and verifies the migrations and ingestion against it, which
  is not the same as upstream supporting it.
- **The two-router split is written, not run.** See above.
- **Nothing here has run behind this repository's Traefik yet.** The stack is
  `scaffolded`.

## Backup

| | |
|---|---|
| **The events** | `./volumes/clickhouse` — every pageview ever recorded, and the part of this stack that grows. ClickHouse's own `BACKUP` command is the supported way; copying the directory from a running server is not |
| **Accounts and sites** | `./volumes/postgres` — dump it: `docker compose exec plausible-db sh -c 'pg_dump -U plausible plausible' > plausible.sql` |
| **The key** | `.secrets/totp_vault_key.txt` — encrypts the two-factor secrets. Without it every account with 2FA is locked out. Keep a copy off this host |
| **Sessions** | `.secrets/secret_key_base.txt` — changing it signs everyone out and nothing more |
| **Reproducible** | `./volumes/plausible` (timezone cache), `./volumes/clickhouse-logs` |
| **Quiescing** | `pg_dump` is consistent on its own. For ClickHouse, stop the container or use `BACKUP` |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/business/plausible/volumes/clickhouse
```

Restore: put the volumes back with `volumes/plausible` owned by `999:999`,
restore the secrets, start the databases, load the PostgreSQL dump, then start
the application. Sites and accounts come back from PostgreSQL; the statistics
come back from ClickHouse, and one without the other is a dashboard with no
numbers or numbers with no dashboard.
