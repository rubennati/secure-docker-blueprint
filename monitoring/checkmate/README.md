# Checkmate

Uptime, certificate, hardware and container monitoring with incidents,
maintenance windows and public status pages. Ten monitor types — HTTP, ping,
TCP, DNS, WebSocket, gRPC, PageSpeed, Docker, hardware via an agent, and game
servers — behind one login. Upstream:
[bluewave-labs/Checkmate](https://github.com/bluewave-labs/Checkmate),
formerly BlueWave Uptime.

It is the fourth uptime monitor here, beside
[`uptime-kuma`](../uptime-kuma/), [`gatus`](../gatus/) and [`ciao`](../ciao/),
and the largest of them: those three answer "is it up"; this one also keeps
incidents with timelines, maintenance windows, hardware metrics and role-based
access. Run one, not several, unless you are comparing them.

Every feature is in the open-source build: no monitor limit, no paid tier, no
paid support.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## Architecture

```text
Traefik ──http──→ checkmate-app :52345   API + dashboard + worker
                        │      :52346    /livez, not routed
                        │
                        └──→ checkmate-db :27017  (MongoDB, app-internal)
```

The application container keeps no state — there is no data volume for it.
Monitors, their history, incidents, users and status pages are all in MongoDB.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # secrets and the data directory
docker compose up -d
```

**Then open the dashboard and create the first account immediately.**
`POST /api/v1/auth/register` is unauthenticated until one account exists, and
the first one to arrive becomes `superadmin` — no invite token needed.
Afterwards the same endpoint answers `404 Invite not found`, and further
accounts come from invitations sent inside the application.

There is a second reason not to leave the window open:
`GET /api/v1/auth/users/superadmin` is also unauthenticated and answers `true`
or `false`. It is how the dashboard decides which screen to show — and it tells
anyone who can reach the port whether the instance is still unclaimed.

`access-vpn` is what makes that window survivable. See below before opening
it.

## Publishing a status page

The dashboard is yours; a status page has a different audience. That is a
second router rather than a change of `APP_TRAEFIK_ACCESS`:

```yaml
# additional labels on checkmate-app
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-status.rule=Host(`${APP_TRAEFIK_HOST}`) && PathPrefix(`/status/public`)"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-status.entrypoints=websecure"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-status.tls=true"
- "traefik.http.routers.${COMPOSE_PROJECT_NAME}-status.middlewares=${APP_TRAEFIK_HEADERS}@file,access-public@file,${APP_TRAEFIK_LIMIT}@file,${APP_TRAEFIK_AUTH}"
```

Traefik matches the longest rule first, so the status router wins for that path
and the dashboard keeps everything else VPN-only. It is the same split
[`business/listmonk`](../../business/listmonk/) uses for its subscriber pages.
**This has not been run on a host** — it is written from the rule that was
measured there.

Checkmate also supports serving a status page on its own custom domain, which
it detects by comparing the request's host against `CLIENT_HOST`. That needs a
second `Host()` router and is untested here.

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:52345 — the first sign-up becomes superadmin
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Security model

- **Claim the instance immediately.** See Setup. This is the one step that
  cannot be postponed.
- **`access-vpn` by default.** Beyond the registration window, the dashboard
  is a list of every host this installation watches — which is a map of the
  estate, useful to exactly the wrong reader.
- **MongoDB requires a password**, which upstream's compose does not do at all:
  it runs `mongod --bind_ip_all` with no credentials. Here the user is created
  by `MONGO_INITDB_ROOT_*`, the connection string names `authSource=admin`, and
  the database is on an internal network with no published port.
- **Three credentials are Docker Secrets**, exported by
  `config/entrypoint.sh` because Checkmate reads everything from the
  environment and has no `_FILE` variant. The connection string carries the
  password inline, so the whole URL is the secret rather than the password
  alone.
- **Session tokens last a week, not 99 days.** Upstream's `TOKEN_TTL` default
  is `99d` and there is no refresh flow, so that default is a bearer token with
  three months of life. `APP_TOKEN_TTL` is the one line to change if weekly
  sign-ins are the wrong trade for you.
- **Port 52346 is not routed.** It answers `/livez` without authentication and
  belongs to the health check, not to the internet.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** —
  verified against v3.12.0. The container writes nothing outside `/tmp`.

## What leaves the host

Since v3.13.0 Checkmate has anonymous telemetry, on by default: a daily
heartbeat, with a count of monitors by type since v3.13.1. This stack sets
`TELEMETRY_ENABLED: "false"`, so it is off. Three features do send data outward
**when you choose them**:

| Feature | Goes to | What |
|---|---|---|
| Global uptime checks | `api.globalping.io` | the URL or host you are checking, to a third-party probe network |
| PageSpeed monitor | `pagespeedonline.googleapis.com` | the URL you are measuring, to Google |
| The world map view | `basemaps.cartocdn.com` | your browser fetches map tiles from CARTO when that view is open |

Notification channels reach their own vendors, which is what they are for. A
monitor that checks an internal host from this container alone sends nothing
anywhere.

## Known limits

- **`limit-standard` is not measured against this dashboard**, a React
  application that pulls its assets in one burst. If the first load is
  rate-limited, the counter is the thing to look at — `limit-extra-large`
  exists for a first load that exceeds the burst of 500, behind a closed
  access policy.
- **No notification channel has been exercised.** Twelve are supported; none
  was configured or delivered here.
- **Hardware monitoring needs an agent** (Capture) on each machine, which this
  stack does not deploy.
- **The status-page routers are written, not run.** See above.
- **Nothing here has run behind this repository's Traefik yet.**

## Backup

| | |
|---|---|
| **Everything** | `./volumes/mongodb` — monitors, history, incidents, users and status pages. Dump it rather than copying the files: `docker compose exec checkmate-db sh -c 'mongodump -u checkmate -p "$(cat /run/secrets/DB_ROOT_PWD)" --authenticationDatabase admin --archive' > checkmate.archive` |
| **The keys** | `.secrets/jwt_secret.txt` signs sessions; changing it signs everyone out, and costs nothing else. `.secrets/encryption_key.txt` decrypts stored Docker TLS client keys; without it those monitors have to be set up again |
| **Credentials** | `.secrets/db_root_pwd.txt` and `.secrets/db_connection_string.txt` hold the same password twice — restore both together |
| **Reproducible** | nothing on the application container; it keeps no state |
| **Quiescing** | `mongodump` is consistent enough for this data. Copying `volumes/mongodb` from a running container is not |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/checkmate/volumes/mongodb
```

Restore: put the volume back, restore the secrets, start the database, load the
dump if you took one, then start the application. The history comes back with
it; a gap in the checks is the outage you did not record, not data loss.

## Open findings

<!-- findings:start — generated by scripts/ci/lifecycle-report.py from upstream-status.json; edit the text around it -->

**Findings in the upstream images** at the pin `v3.13.1` — the newest upstream release. Scanned 2026-11-09; counted are findings with a published fix, as CRITICAL · HIGH. They come with the images as upstream publishes them.

| Image | Base system | Libraries | Programs |
|---|---|---|---|
| `ghcr.io/bluewave-labs/checkmate:v3.13.1` | 0 · 1 | 4 · 21 | 1 · 25 |
| `mongo:8.0.32` | 0 · 2 | 0 · 3 | 1 · 26 |

<!-- findings:end -->

The image, `ghcr.io/bluewave-labs/checkmate:v3.13.1`, carries 5 CRITICAL findings in bundled libraries: DOMPurify, handlebars (2), `proxy-addr` and the Go runtime of the esbuild build tool. It is the newest release.

**Risk:** each needs a specific use (user-supplied templates, a mis-written proxy subnet, a particular sanitizer mode, or a build step) that Checkmate is not known to make; this has not been checked in its code. Move to the next release.

The MongoDB image, `mongo`, carries one CRITICAL finding, CVE-2025-68121, in the Go runtime of `gosu`, the helper that drops root privileges at start. Every current image of this line ships the same gosu build, and its maintainer has not rebuilt it with a fixed Go.

**Risk:** the flaw is in TLS session resumption, and gosu opens no network connection, so it is not reached. The finding clears when upstream ships a rebuilt gosu.
