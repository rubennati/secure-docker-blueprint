# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/defectdojo/defectdojo-django
- **GitHub:** https://github.com/DefectDojo/django-DefectDojo
- **Docs:** https://docs.defectdojo.com
- **License:** BSD 3-Clause
- **Origin:** DefectDojo Inc · no country stated in the sources checked · no country
- **Domain:** Security operations
- **Role:** Vulnerability management: import scanner and pentest findings, deduplicate them and track them to closure
- **Based on version:** `3.3.100`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

The licence names DefectDojo, Inc.; no jurisdiction was found in the pages checked.

## What we use

- `defectdojo/defectdojo-django:3.3.100` for uWSGI, the Celery worker, Celery beat
  and the initializer, and `defectdojo/defectdojo-nginx:3.3.100`. Upstream's compose
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

**Not yet exercised:** Traefik routing and TLS; the browser interface; other scanner
formats; notifications and ticketing integrations; Celery beat's scheduled jobs
firing; backup and restore; an upgrade across versions.

## Upgrade checklist

1. Read the release notes: https://github.com/DefectDojo/django-DefectDojo/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database, `volumes/media` and `.secrets/`
4. Bump `APP_TAG` in `.env.example` — the django and nginx images move together
5. `docker compose pull && docker compose up -d`; the initializer migrates first
6. Log in and open a product's findings
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
