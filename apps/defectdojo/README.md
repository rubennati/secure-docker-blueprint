# DefectDojo

Vulnerability management: import the output of scanners and penetration tests
into products and engagements, deduplicate the findings, and track each one to
closure, with metrics and reports. Django under uWSGI behind nginx, a Celery
worker and scheduler, a one-shot initializer, PostgreSQL and Valkey — the seven
services of upstream's compose. Upstream:
[DefectDojo](https://github.com/DefectDojo/django-DefectDojo).

## Architecture

```text
Internet, scanners → Traefik (TLS) → defectdojo-nginx :8080
                                            │
                              app-internal (internal: true)
                                            │
   defectdojo-uwsgi · celeryworker · celerybeat · PostgreSQL 18 · Valkey
         (initializer: runs, migrates, exits)     │
                                     celeryworker → app-egress (notifications)
```

## Setup

```bash
cp .env.example .env            # host name, ADMIN_USER, ADMIN_EMAIL
ops/init.sh                     # every secret, including the connection URLs
sudo chown 1001:1001 volumes/media
sudo chown 999:1000 volumes/valkey
docker compose up -d            # the first start migrates for about five minutes
```

The initializer runs on every `docker compose up`: on an empty database it
migrates, loads the scanner definitions and creates the administrator from
`ADMIN_USER` and `.secrets/dd_admin_password.txt`; afterwards it finds nothing to
do and exits. The application starts only once it has exited successfully. There
is no setup page and no open window.

Import a report through the interface or the API — for example
`POST /api/v2/import-scan/` with a token from `POST /api/v2/api-token-auth/`.

## Upstream's default keys

Upstream's compose file carries public default values for `DD_SECRET_KEY` and
`DD_CREDENTIAL_AES_256_KEY`. The second encrypts the credentials DefectDojo stores
for tool integrations. An installation that keeps the defaults encrypts them with
a key anyone can read. This stack replaces both with secrets from `ops/init.sh`.

Upstream also prints a generated administrator password to the initializer's log
when none is set. Here it is set, so nothing is printed.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator | `ADMIN_USER` + `.secrets/dd_admin_password.txt` | Created once by the initializer |
| Further users | Created by the administrator | PostgreSQL |
| API clients and scanners | API tokens (`/api/v2/api-token-auth/`, or per user in the interface) | PostgreSQL |
| Stored integration credentials | Encrypted with `DD_CREDENTIAL_AES_256_KEY` | Docker Secret — keep it |
| Sessions | Signed with `DD_SECRET_KEY` | Docker Secret |
| Service-to-service | PostgreSQL and Valkey passwords, inside three connection URLs | Docker Secrets |

## Security notes

- **Secrets.** DefectDojo reads any `DD_*_FILE` variable into its value itself
  (`/secret-file-loader.sh`). Every secret uses that, including the database,
  broker and cache URLs, which carry passwords. No wrapper is involved. The values
  appear neither in `docker inspect` nor in any log — checked.
- **Hardening.** Every DefectDojo container runs as uid 1001 with a read-only root
  filesystem and all capabilities dropped. nginx and Celery beat get a tmpfs at
  `/run/defectdojo` for the files they write at start; Valkey runs as 999, read-only,
  with its password in a tmpfs config file. No port is published.
- **Network.** Only the Celery worker has a route out, for notifications and
  ticketing integrations; uWSGI, PostgreSQL and Valkey have none.
- **Exposure.** A database of unfixed vulnerabilities is a list of ways in.
  `.env.example` ships `acc-tailscale`; scanners that push results over the API must
  be able to reach it.

## Status

Run behind Traefik with TLS on 2026-09-22 (3.3.100): the first start, the API
with a token, two scan imports, the interface, a restart, and the restore below.
Full log in [`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
cp .env.local.example .env      # ops/init.sh reads DB_NAME and DB_USER from .env
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — about five minutes on the first start
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Only nginx is published, on `127.0.0.1`; Traefik and the Docker Secrets mechanism
are not used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/media` and `.secrets/`:

```bash
docker exec defectdojo-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > defectdojo.sql
sudo tar -czf defectdojo-files.tar.gz volumes/media .secrets
```

`volumes/media` belongs to uid 1001 with mode `700`, hence `sudo`.

Valkey holds the task queue and a cache. Restore into an empty database with
`psql`, unpack the archive, restore the `1001:1001` ownership on `volumes/media`,
and run `docker compose up -d`; the initializer finds the schema in place. Without
the original `dd_credential_aes_256_key.txt`, stored integration credentials cannot
be decrypted.
