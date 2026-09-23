# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/frappe/erpnext
- **Deployment:** https://github.com/frappe/frappe_docker
- **GitHub:** https://github.com/frappe/erpnext
- **Docs:** https://docs.frappe.io/erpnext
- **License:** GPL-3.0
- **Origin:** India · Frappe Technologies Pvt. Ltd. · non-EU
- **Edition gating:** none — upstream states that ERPNext is 100% open source with no features behind paywalls — https://frappe.io/erpnext/pricing · checked 2026-09-21
- **Commercial model:** no paid edition — https://frappe.io/erpnext/pricing · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Domain:** Business operations
- **Role:** ERP on the Frappe framework: accounting, invoicing, stock, buying, selling, manufacturing, projects and HR
- **Based on version:** `v16.35.0`

No `Last verified` line yet: the realtime service's session check is fixed and
proven inside the stack (below), and the desk it serves has not been opened in a
browser since.

The origin comes from Frappe's cloud and enterprise terms, which name Frappe
Technologies Pvt. Ltd. and place arbitration in Mumbai. The licence is the
repository's licence file; the pricing page describes the self-hosted edition as
AGPL-3.0. The Frappe framework underneath is MIT.

## What we use

- `frappe/erpnext:v16.35.0` — one image for every role, published for amd64 and
  arm64. Upstream's compose pins `platform: linux/amd64`; this stack does not.
- `mariadb:11.8` and `redis:8.6-alpine` — the versions upstream's compose pins.
- frappe_docker's `compose.yaml` with `overrides/compose.mariadb.yaml` and
  `overrides/compose.redis.yaml`: the same ten services.

## What we changed and why

| Change | Reason |
|--------|--------|
| Bind mounts, and the configurator creates `common_site_config.json` when missing | The image seeds an empty file only into a named volume. A bind mount starts empty, and `bench set-config` fails without the file — measured |
| MariaDB creates the site's database and user; the site is created with `--no-setup-db` | Upstream creates the site with the MariaDB root password on the command line. Here Frappe uses the site's own user and never receives the root password |
| Redis with a password | Upstream's two instances have none. The password sits in a config file on tmpfs rather than in the process list; Frappe's Redis URLs in `common_site_config.json` carry it |
| Frappe's command runner instead of `bench` for commands with passwords | `bench` writes every command line to `logs/bench.log` — measured: the Redis password, the database password and the Administrator password were in it after the upstream-style commands. `python -m frappe.utils.bench_helper frappe …` from `sites/` is what `bench` itself runs |
| `read_only` on every Frappe role; tmpfs on `config/` and `config/pids` | Frappe takes file locks in `config/`, which fails on a read-only root — measured. `bench` treats the directory as a bench only while `config/pids` exists — measured: "No such command" without it |
| tmpfs on nginx's `conf.d`, `/var/lib/nginx` and `/run`, mode 1777 | `nginx-entrypoint.sh` writes the site configuration at start; nginx needs its temp paths and PID file |
| `FRAPPE_SITE_NAME_HEADER` set to the site name | One site, answered whatever Host header arrives |
| `UPSTREAM_REAL_IP_ADDRESS: 0.0.0.0/0` | The client address comes from Traefik's `X-Forwarded-For` |
| Egress only for the backend and the queue workers | Nothing else calls out |
| Healthchecks: TCP for nginx, Gunicorn and Socket.IO; the process for workers and scheduler | The image ships no `healthcheck.sh`, although upstream's operations page refers to one |
| No backup-cron override | Upstream's runs Ofelia with the Docker socket |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | A company's books in one place |
| `config/nginx-socketio.conf`: a second listener on 8081 for `/socket.io`, with `Origin http://$host:8080`, and the site name as a network alias of the frontend on `app-internal` | The realtime service authenticates a socket by fetching `<Origin>/api/method/frappe.realtime.get_user_info`. The image's nginx puts the public URL in `Origin`, which a container on `app-internal` cannot reach — every socket was refused with `Unauthorized: TypeError: fetch failed`. Upstream's own compose leaves that container on a network with a way out; this keeps the isolation and gives it an address that exists |

## The realtime service's session check (2026-09-23)

Frappe's realtime server (`realtime/middlewares/authenticate.js`) authenticates a
socket by fetching `<Origin>/api/method/frappe.realtime.get_user_info` with the
session cookie. The image's nginx template sets `Origin` to
`$proxy_x_forwarded_proto://${FRAPPE_SITE_NAME_HEADER}` — the public URL — and
the websocket container sits on `app-internal` only, where that address does not
resolve and could not be reached if it did.

`config/nginx-socketio.conf` serves `/socket.io` from a second listener on 8081
and sends `Origin http://$host:8080` instead. The frontend carries the site name
as a network alias on `app-internal`, so that address exists there; `Host` still
carries the site name, so the backend resolves the site as it does for any other
request, and `X-Frappe-Site-Name` keeps the namespace check happy. Traefik routes
`/socket.io` to 8081 and everything else to 8080.

Measured from inside the websocket container, with a session opened through the
same internal address, the same handshake against both listeners:

```text
port 8080 (the image's own block): 44 … {"message":"Unauthorized: TypeError: fetch failed"}
port 8081 (this listener):         40 … {"sid":"…"}     — the namespace connected
```

`GET /api/method/frappe.realtime.get_user_info` through the internal address
answered `200` where the same call had failed to connect at all.

**Not yet exercised:** the desk in a browser with the fix in place — pushed
notifications, list refreshes and progress bars.

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- All services `healthy` about two minutes after the first `up`; the configurator
  exited `0`
- `ops/create-site.sh` created the site in 137 s; a second run changed nothing;
  `logs/bench.log` contained no password
- A client outside the access policy's ranges got `403`, over IPv4 and IPv6
- Login as Administrator, then the setup wizard in the browser: language,
  country, time zone and currency; a user; the persona questions; company and
  chart of accounts — "Complete Setup" took 42 s and opened the desk (67
  requests, no `429` under `sec-2`)
- The site had been created with the scheduler off (`*** Scheduler is disabled
  ***`); after the wizard `enable_scheduler` was `1`
- The scheduler delay as the README describes: with the site switched to a zone
  30 minutes behind Asia/Kolkata, the 82 scheduled job types carried creation
  times ahead of the site's clock, and no scheduled job ran for the 22 minutes
  observed after the wizard. The first run after the delay was not waited for
- A customer created with the desk's own client API and listed at `/app/customer`
- The realtime socket did not connect (`Unauthorized: TypeError: fetch failed`,
  see above); polling and the websocket upgrade themselves answered through the
  route
- Company and customer unchanged after `docker compose down` and `up`
- Backup as the README describes (737 tables); restore into an empty database in
  12 s, the archive unpacked, ownership restored — site, company and customer back

**Not yet exercised:** a scheduled job's first run after the delay; email;
reports and printing; the queues under load.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, `app-internal`) on a
throwaway `proxy-public` network without Traefik. `volumes/sites`, `volumes/logs`,
`volumes/mysql` and `volumes/redis-queue` were Docker volumes owned as
`ops/init.sh` and the `chown` lines leave them:

- The nine long-running services came up healthy on read-only roots; the
  configurator exited 0 after writing the database host and both Redis URLs
- `ops/create-site.sh` created the site in 4 minutes 25 seconds with the
  database user MariaDB created; a second run reported "already created"
- Neither the Administrator password nor the MariaDB root password was in any file
  under `sites/` or `logs/`, or in a database dump. The database password was only
  in `site_config.json`, the Redis password only in `common_site_config.json`
- Without a session, `/app` redirected to the login and the REST API answered 403.
  A wrong password returned 401; the right one logged in. Sign-up was refused:
  "Sign Up is disabled"
- Once the desk was loaded, a POST without the CSRF token was refused
  (`CSRFTokenError`, 400); with the token it created the record
- The setup wizard completed through its own endpoint (company, country, currency,
  time zone); a customer created through the REST API was in the database;
  Socket.IO answered through nginx
- The queue workers ran the jobs the wizard queued. After the wizard set
  Europe/Vienna, the next scheduled runs lay 3 hours 17 minutes ahead of the
  site's clock, because the job types were created in Asia/Kolkata; with one job
  made due by setting its last run back, the scheduler container queued it on its
  next tick and a worker ran it
- After `docker compose down` and `up`: all services healthy, the customer still
  there, login working
- Hardening from `docker inspect`: the Frappe roles as uid 1000, read-only,
  `cap_drop: ALL`, no capability added; Redis as uid 999, read-only; no published
  port; no secret value in the configured environment; `app-internal` internal;
  egress only for the backend and the queue workers
- `docker-compose.local.yml` created its site; login answered 200, a wrong
  password 401
- Seen once, on a first start: two Frappe containers relinking `sites/assets` at
  the same moment — the second failed on the read-only root and started cleanly on
  its automatic restart

**Not yet exercised:** Traefik routing and TLS; the desk in a browser; accounting
documents, stock and reports; email; PDF printing; an image upgrade with
`bench migrate`; backup and restore; more than one site.

## Upgrade checklist

1. Read the release notes: https://github.com/frappe/erpnext/releases
2. Back up the database, `volumes/sites` and `.secrets/`
3. Bump `APP_TAG` in `.env.example`, and `DB_TAG` / `REDIS_TAG` if frappe_docker's
   compose moved
4. `docker compose pull && docker compose up -d`
5. Apply the new release's migrations, upstream's step (not exercised here):
   `docker compose exec erpnext-backend bench --site "$SITE_NAME" migrate`
6. Log in and open the desk
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
