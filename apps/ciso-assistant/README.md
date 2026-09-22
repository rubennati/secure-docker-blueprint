# CISO Assistant

Governance, risk and compliance: frameworks such as ISO/IEC 27001, NIS2 and NIST
CSF mapped to controls, with risk registers, compliance assessments, evidence and
remediation plans. Backend, task worker and frontend, with PostgreSQL — upstream's
own PostgreSQL + Traefik template. Upstream:
[CISO Assistant](https://github.com/intuitem/ciso-assistant-community).

## Architecture

```text
Internet → Traefik (TLS) ─┬→ ciso-assistant-frontend :3000   everything else
                          └→ ciso-assistant-backend  :8000   /api
                                     │
                        app-internal (internal: true)
                                     │
                   ciso-assistant-huey · PostgreSQL 16
```

The backend migrates the database and loads the framework library at start; Huey
runs scheduled tasks.

## Setup

```bash
cp .env.example .env            # host name, ADMIN_EMAIL
ops/init.sh                     # three secrets, data directories
sudo chown 1001:1001 volumes/data
docker compose up -d
```

**The first start takes about ten minutes**: every migration runs and the
framework library — 326 libraries, from ISO/IEC 27001 to NIS2 — is loaded into the
database. Later starts take seconds. The administrator is created on that first
start from `ADMIN_EMAIL` and the password in `.secrets/admin_pwd.txt`; there is no
setup page and no open window.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator | `ADMIN_EMAIL` + `.secrets/admin_pwd.txt` | Created once on the first start; changing the secret later does not change the account |
| Further users | Invited by the administrator | PostgreSQL. Public sign-up is refused (403) |
| API clients | Personal access tokens | Created in the user settings |
| Sessions and tokens | Signed with `DJANGO_SECRET_KEY` | Docker Secret |

## Security notes

- **Secrets.** None of the variables has a `_FILE` form. `config/entrypoint.sh`
  exports them from the Docker Secrets; they are absent from `docker inspect`.
  Without `DJANGO_SECRET_KEY` the image would generate one and store it in the data
  directory — with the secret set, no such file appears. The image does write
  `idp_oidc_private_key.pem` there on the first start: the signing key of its
  built-in OIDC provider, which the backup below includes.
- **Hardening.** Upstream's own compose already runs read-only with all
  capabilities dropped; this stack keeps that. Backend and Huey run as uid 1001,
  the frontend as 1000 with no shell in its image. No port is published.
- **Network.** Huey and PostgreSQL are on `app-internal` and have no route out.
- **Exposure.** A register of an organisation's risks and control gaps is a map of
  where it is weak. `.env.example` ships `acc-tailscale`.
- **Rate limit.** The interface's first load requests about 80 script chunks and
  assets. Under `sec-2` fourteen of them were answered with `429` and the page did
  not load, so `.env.example` ships `sec-2-spa`.

## What is not included

Upstream's default compose also runs Qdrant (used by the AI features) and an MCP
server (as an optional profile); its PostgreSQL + Traefik template includes
neither. This stack follows the template.

## Status

Run behind Traefik with TLS on 2026-09-22 (v4.0.5): the interface and the `/api`
split, ISO/IEC 27001:2022 imported into a compliance assessment, Huey's scheduled
tasks, a restart, and the restore below. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — about ten minutes on the first start
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Only the frontend is published, on `127.0.0.1`; Traefik and the Docker Secrets
mechanism are not used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/data` and `.secrets/django_secret_key.txt`.
`volumes/data` holds Huey's queue, a SQLite file, and the OIDC signing key; it
belongs to uid 1001 with mode `700`, hence `sudo`, and Huey is stopped while the
archive is written:

```bash
docker exec ciso-assistant-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > ciso-assistant.sql
docker compose stop ciso-assistant-huey
sudo tar -czf ciso-assistant-files.tar.gz volumes/data .secrets/django_secret_key.txt
docker compose start ciso-assistant-huey
```

Restore into an empty database:

```bash
docker compose down
# move volumes/postgres and volumes/data aside, then:
(umask 077; mkdir -p volumes/postgres volumes/data)
docker compose up -d db
docker exec -i ciso-assistant-db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < ciso-assistant.sql
sudo tar -xzf ciso-assistant-files.tar.gz
sudo chown -R 1001:1001 volumes/data
docker compose up -d
```

The backend's start tries to create the administrator again and logs `That email
is already taken`; the restored account is kept.
