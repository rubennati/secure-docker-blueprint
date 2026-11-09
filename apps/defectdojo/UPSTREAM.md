# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/defectdojo/defectdojo-django
- **GitHub:** https://github.com/DefectDojo/django-DefectDojo
- **Docs:** https://docs.defectdojo.com
- **License:** BSD 3-Clause
- **Origin:** DefectDojo Inc · no country stated in the sources checked · no country
- **Decision facts checked:** not yet
- **Domain:** Security operations
- **Role:** Vulnerability management: import scanner and pentest findings, deduplicate them and track them to closure
- **Last verified:** 2026-11-08 (3.5.0) — over IPv4: the initializer migrated, loaded 393 scanner definitions and created the administrator from `ADMIN_USER` and the secret file, an API token for it, a product type created and present after `down`/`up`, celery worker and beat running, the refused client answered `403` (docs/labs/stack-refresh/2026-11-08-results.md)

The licence names DefectDojo, Inc.; no jurisdiction was found in the pages checked.

## What we use

- `defectdojo/defectdojo-django:3.5.0` for uWSGI, the Celery worker, Celery beat
  and the initializer, and `defectdojo/defectdojo-nginx:3.5.0`. Upstream's compose
  defaults to `:latest`; not used here.
- `postgres:18.6-alpine` and `valkey/valkey:9.1.2-alpine` — the versions upstream's
  compose pins (it also pins their digests).
- The seven services of upstream's `docker-compose.yml`, unchanged in shape.

## What we changed and why

| Change | Reason |
|--------|--------|
| Every secret through `DD_*_FILE` | Upstream's image reads them natively; its compose sets them as plain variables |
| Own values for `DD_SECRET_KEY` and `DD_CREDENTIAL_AES_256_KEY` | Upstream's compose has public default values for both; the second encrypts stored integration credentials |
| `DD_ADMIN_PASSWORD_FILE` on the initializer | Without it the initializer generates a password and prints it to its log — verified that nothing is printed with it set |
| Valkey with a password, via a tmpfs config file | Upstream runs it without one |
| `read_only: true` on all five DefectDojo containers | Verified from an empty database: migrations, admin, imports, jobs, restart. nginx and beat each needed one tmpfs, below |
| tmpfs at `/run/defectdojo` for nginx and beat, `mode: 1023` | nginx's entrypoint writes its upstream definition there (`can't create /run/defectdojo/uwsgi_pass: Read-only file system`); beat keeps its pid file and schedule there. A plain tmpfs mounts `755 root`; 1023 is octal 1777 |
| uWSGI healthcheck against `localhost:8081` | Django answers 400 to a Host outside `DD_ALLOWED_HOSTS` |
| nginx healthcheck against `127.0.0.1` with `Host: localhost` | In that container `localhost` resolves to `::1` while nginx listens on IPv4 only, and the Host header must still be allowed |
| Celery worker on `app-egress` | It sends notifications and talks to ticketing integrations; nothing else gets a route out |
| `DD_GITHUB_STAR_PROMPT_ENABLED: "False"` | From 3.4.300 the interface shows users of seven days or more a card asking them to star the project on GitHub; upstream's default is on |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- First start about four and a half minutes; the initializer migrated, created the
  administrator and exited `0`, then the application started
- A client outside the access policy's ranges got `403` on `/` and `/api/v2/`,
  over IPv4 and IPv6
- `POST /api/v2/api-token-auth/` returned a token; a wrong password `400`; the API
  `403` without a token, `200` with it
- `POST /api/v2/import-scan/` with a two-finding report (Generic Findings Import)
  and `auto_create_context`: product type, product, engagement and test created,
  both findings active. A second import of the same report added a second test
  with the same two findings, not marked as duplicates — deduplication is a
  system setting, off by default
- The Celery worker ran the tasks the imports queued (search index, notifications,
  finding post-processing)
- In the browser: login page 37 requests, dashboard 42, the findings list 41 with
  the imported findings
- After `docker compose down` and `up` (54 s, the initializer exited `0` again):
  token, product and the four findings unchanged
- Backup as the README describes; the archive of `volumes/media` needs `sudo`
  (uid 1001, mode `700`). Restore into an empty database without errors, the
  archive unpacked, ownership restored — token, product and findings back
- Each recreated database container leaves an empty anonymous volume: the
  PostgreSQL 18 image declares `VOLUME /var/lib/postgresql`, while `PGDATA` points
  into the bind mount, where the data stays
- Peaks: uWSGI 552 MiB, initializer 324 MiB, Celery worker 182 MiB, Celery beat
  178 MiB, PostgreSQL 93 MiB, nginx 14 MiB, Valkey 13 MiB

**Outside this verification:** notifications and ticketing integrations; deduplication
switched on; scanners pushing results; large imports.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, `app-internal`,
`app-egress`) on a throwaway `proxy-public` network without Traefik, starting from
an empty database with every DefectDojo container read-only, through nginx from a
peer container:

- The initializer migrated the empty database, created the administrator and exited
  0 in about five minutes; the application started after it
- `POST /api/v2/api-token-auth/` returned a token; a wrong password returned 400;
  the API without a token returned 403
- A product type and a product were created, and a Generic Findings Import report
  with two findings was imported through `POST /api/v2/import-scan/`; both findings
  were listed with the right severities
- Re-importing the same report created nothing and left both findings untouched —
  deduplication working
- The Celery worker received and completed the post-import tasks (11 succeeded)
- After `docker compose down` and `up`, both findings were still there
- Hardening from `docker inspect`: all DefectDojo containers uid 1001, read-only, all
  capabilities dropped; Valkey 999:1000, read-only; no published port; secret values
  absent from the configured environment and from every log; the administrator
  password not printed; uWSGI and PostgreSQL without a route out

**Outside this verification:** Traefik routing and TLS; the browser interface; other scanner
formats; notifications and ticketing integrations; Celery beat's scheduled jobs
firing; backup and restore; an upgrade across versions.

## Version notes

- Valkey moved to `9.1.3-alpine` on 2026-10-31 (released 2026-10-26); the stack's state is anchored on the application pin, which did not
  move. Upstream marks the release
  SECURITY: GHSA-f4q9-j22m-xqq9, a heap buffer overflow in cluster Pub/Sub
  message construction that an authenticated client could turn into code
  execution. No breaking change; expired hash fields no longer propagate on
  HDEL and related commands, and `hide-user-data-from-log` also redacts error
  text.
- Moved to `3.5.0` on 2026-11-05 (released 2026-11-02), django and nginx
  together. Upstream's upgrade notes for 3.4.x
  and 3.5.x name no manual step; database migrations run in the initializer.
  API changes: from 3.5.0 `/api/v2/findings/` applies the `engagement`,
  `product` and `prod_type` filters it used to ignore and rejects a
  non-numeric value with 400; from 3.4.300 the `endpoint` field of
  `/api/v2/endpoint_status/` carries the Endpoint's ID when Locations is
  enabled. New settings: `DD_GITHUB_STAR_PROMPT_ENABLED` (3.4.300, set to
  `False` here), `DD_SECRET_KEY_FALLBACKS` (3.5.0). The deprecated Tool Type,
  Tool Configuration and API Scan Configuration endpoints are still present in
  3.5.0. Upstream's own compose now pulls through `registry.defectdojo.com`,
  which logs each pull; this stack keeps the Docker Hub names. Advisories fixed
  after 3.3.100: GHSA-66vh-fm67-46vw, GHSA-52xm-5vrx-cqmm, GHSA-j635-qvw5-qv7j,
  GHSA-g3w5-c3g8-5gfp, GHSA-p7f6-2fhg-x25w, GHSA-68cw-fx5m-7mq8,
  GHSA-fhpm-fp42-h465, GHSA-vcgh-2275-cccm,
  GHSA-hm9q-36mr-hg94, GHSA-qj59-6r69-xmgv, GHSA-x667-22jr-wvmw,
  GHSA-p43f-52f3-6v3v, GHSA-9pmx-7vc8-r7xw, GHSA-r83j-v49f-m87m,
  GHSA-r68c-qm7x-4926, GHSA-4chj-hx9x-6m59, GHSA-hprf-883v-c8h8 and
  GHSA-xr4w-vf88-w48v (medium and low).

## Upgrade checklist

1. Read the release notes: https://github.com/DefectDojo/django-DefectDojo/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database, `volumes/media` and `.secrets/`
4. Bump `APP_TAG` in `.env.example` — the django and nginx images move together
5. `docker compose pull && docker compose up -d`; the initializer migrates first
6. Log in and open a product's findings
7. Add **Last verified** only if the
   upgrade was exercised on a real install
