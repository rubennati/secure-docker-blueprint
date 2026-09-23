# Upstream Reference

## Source

- **Image:** https://github.com/bluewave-labs/Checkmate/pkgs/container/checkmate
- **GitHub:** https://github.com/bluewave-labs/Checkmate
- **Project:** https://checkmate.so
- **License:** AGPL-3.0
- **Use restrictions:** none — https://github.com/bluewave-labs/Checkmate/blob/develop/LICENSE · checked 2026-09-23
- **Edition gating:** none — upstream states every feature ships in the open-source build, with no monitor limit and no paid support tier — https://checkmate.so · checked 2026-09-23
- **Commercial model:** no paid edition — https://checkmate.so · checked 2026-09-23
- **Decision facts checked:** 2026-09-23
- **Origin:** Canada · BlueWave Labs · non-EU
- **Domain:** Monitoring
- **Role:** Uptime, certificate, hardware and container monitoring with incidents, maintenance windows and status pages
- **Based on version:** `v3.12.0`

## Project maturity

10 878 stars, pushed 2026-09-22, release v3.12.0 on 2026-09-13, 167
contributors. Formerly BlueWave Uptime; the rename is why older references and
the `bluewave-labs` organisation name do not match the product name.

## What we use

- `ghcr.io/bluewave-labs/checkmate:v3.12.0`, one container carrying the API,
  the built dashboard and the worker that runs the checks. Two ports: 52345
  serves everything, 52346 answers `/livez` for the worker.
- `mongo:8.0.32`.

## What we changed and why

| Change | Reason |
|--------|--------|
| MongoDB with authentication | Upstream's compose runs `mongod --bind_ip_all` with no credentials at all. `MONGO_INITDB_ROOT_*` plus `authSource=admin` in the connection string |
| `config/entrypoint.sh` exports three credentials from Docker Secrets | Checkmate reads everything from the environment and has no `_FILE` variant. The connection string carries the password inline, so the whole URL is the secret |
| `APP_TAG=v3.12.0` | Upstream's compose uses `:latest` with `pull_policy: always` |
| `NODE_ENV=production`, `LOG_LEVEL=info` | The schema in `config/envValidation.js` defaults them to `development` and `debug` |
| `TOKEN_TTL=7d` | Upstream's default is `99d` and no refresh flow exists, so a stolen token is usable for three months |
| `read_only: true`, `cap_drop: ALL`, `no-new-privileges` | Upstream's compose sets none of them. The image runs as uid 1000 and the container keeps no state — there is no data volume at all |
| No `ports:` | Upstream publishes 52345 to the host |
| MongoDB on `internal: true` | Upstream puts both services on one bridge network |
| Port 52346 is not routed | The worker health port answers `/livez` without authentication |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | A fresh instance hands ownership to whoever registers first, and the dashboard lists every host this installation watches |

`stop_grace_period: 60s` is upstream's, kept: the worker finishes the checks in
flight rather than leaving a gap on every restart.

## Verified on the images (2026-09-23)

Not a host verification: this ran the stack's own files with a throwaway
network and no Traefik router.

- `ops/init.sh` → `docker compose up -d`: migrations ran, MongoDB connected
  **with authentication**, and the application came up healthy as uid 1000
  under `read_only`, `cap_drop: ALL` and `no-new-privileges`. No read-only or
  permission errors in the log, before or after a restart.
- **The registration window is real and it closes.**
  `POST /api/v1/auth/register` is unauthenticated and took the first account
  with `role: ["superadmin"]` and no invite token. A second attempt was
  refused with `404 Invite not found`.
- **`GET /api/v1/auth/users/superadmin` is unauthenticated and says whether
  the window is open** — it answered `data: false` before the first account and
  `data: true` after. The client uses it to decide which screen to show; it
  also tells anyone who can reach the port that an instance is unclaimed.
- The register endpoint takes `{"user": {...}}`, not a flat body: the
  controller reads `req.body.user` and `req.body.token`. A flat JSON or
  multipart body is answered with a 500 whose message is
  `expected object, received undefined`.
- **A monitor ran.** An HTTP monitor created through the API recorded checks in
  `db.checks` with `status: true`, response times and `statusCode: 200`.
- `GET /api/v1/monitors` without a token answers `401 No token provided`.
- **No Google Fonts in the dashboard.** `statusPageDocumentCsp.js` allows
  `fonts.googleapis.com` and `fonts.gstatic.com` and its comment mentions "the
  app's Google Fonts", but the served `index.html`, the main stylesheet and the
  main bundle reference none — fonts are bundled. The CSP entry is permissive
  rather than load-bearing.
- **The world map loads tiles from a third party.** The main bundle carries
  `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`, so
  opening that view has the browser fetch map style and tiles from CARTO.
- Idle: application 135 MiB anonymous plus 55 MiB page cache with one monitor;
  MongoDB 111 MiB plus 212 MiB.

What a host run still has to establish: the route through `core/traefik`, the
`sec-2` chain against the dashboard, a notification channel actually
delivering, a public status page on its own router, and a restore from the
volume.

## Where upstream's "nothing leaves" needs a footnote

checkmate.so states: *"Does any data leave my infrastructure? No. …No
phone-home, no telemetry pipeline."* That is true of telemetry — nothing in the
image reports on the installation. Three features send data outward **when you
choose them**, which is different from a beacon but is not nothing:

| Feature | Endpoint | What goes out |
|---|---|---|
| Global uptime checks | `api.globalping.io/v1` | the URL or host being checked, to a third-party probe network |
| PageSpeed monitor | `pagespeedonline.googleapis.com` | the URL being measured, to Google |
| The world map view | `basemaps.cartocdn.com` | the viewer's browser fetches map tiles from CARTO |

Notification channels — Pushover, Telegram, Twilio, PagerDuty, SignalGrid and
the rest — also reach their vendors, which is what a notification channel is.

## Upgrade checklist

1. Read the release notes — https://github.com/bluewave-labs/Checkmate/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`
3. `docker compose pull && docker compose up -d` — migrations run on start
4. `docker compose logs checkmate-app` — `Migrations completed`, then
   `Server started on port:52345`
5. Confirm a monitor is still recording checks
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's own compose — :latest, published port, no read_only, no DB auth
curl -s https://raw.githubusercontent.com/bluewave-labs/Checkmate/develop/docker/docker-compose.yaml

# Every setting the server reads, with its defaults and validation
docker run --rm --entrypoint sh ghcr.io/bluewave-labs/checkmate:v3.12.0 \
    -c 'cat /app/server/dist/config/envValidation.js; cat /app/server/.env.example'
```
