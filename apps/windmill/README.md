# Windmill

Code-first automation: scripts (Python, TypeScript, Go, Bash, SQL and more),
flows, APIs, scheduled jobs and internal apps, with Postgres as the entire
state including the job queue. Aimed at developers and data teams; a
different shape from [n8n](../n8n/)'s node-based editor.

## Architecture

```text
Internet → Traefik (TLS, port 443) → windmill-server :8000
                                       │
                          app-internal (internal: true)
                                       │
            db (Postgres 18) ← worker, worker-native ──→ app-egress → internet
```

Four containers. The server serves the API and UI; workers pull jobs from the
Postgres queue and never talk to the server. `worker` runs general jobs
(Python, TypeScript, Go, Bash, …); `worker-native` runs the lightweight
in-process kinds. Traefik replaces the Caddy service in upstream's compose
file.

## Setup

```bash
cp .env.example .env
mkdir -p .secrets volumes/postgres volumes/worker_cache
sudo chown 1000:1000 volumes/worker_cache        # the workers run as uid 1000
openssl rand -hex 32 > .secrets/db_pwd.txt
docker compose up -d
./ops/bootstrap-admin.sh you@example.com
```

Set `APP_TRAEFIK_HOST` in `.env`. The database password is hex on purpose — it
is embedded in a connection URL, where base64's `+ / =` break parsing.

### Replace the default administrator first

A fresh Windmill contains the superadmin `admin@windmill.dev` with the
password `changeme`. That is upstream's documented starting point, and it is
valid from the moment the server first starts. This stack therefore ships with
`APP_TRAEFIK_ACCESS=acc-deny`: nothing can reach the UI until you have run

```bash
./ops/bootstrap-admin.sh you@example.com
```

The script talks to the server container directly, needs no Traefik route,
and:

- creates `you@example.com` as superadmin with a generated password, saved to
  `.secrets/windmill_admin_pwd.txt` (mode 600);
- deletes `admin@windmill.dev`;
- checks that the built-in login now fails, and exits non-zero if it does not.

Running it again is safe — it reports "already bootstrapped" and changes
nothing. Then set `APP_TRAEFIK_ACCESS` in `.env` to the audience you want
(`acc-private` for LAN plus VPN) and run `docker compose up -d`. Keep the
password file with the other secrets and back it up with them.

## Job isolation

Scripts run inside the worker container with no further sandboxing. Upstream's
own default worker is `privileged: true` for PID-namespace isolation, which
this repository does not grant; NSJAIL, upstream's unprivileged alternative,
failed in testing. The worker is non-root, has all capabilities dropped, a
read-only root filesystem and `no-new-privileges`, and that is the whole
boundary. The evidence is in
[`UPSTREAM.md`](UPSTREAM.md#nsjail-was-tried-and-did-not-work) — read it
before letting anyone you do not trust write scripts here.

## Network exception — why the workers reach the internet

Every stack here isolates its internal network. The two workers additionally
join `app-egress`, a network private to this stack with outbound access,
because jobs need it: a Python job downloads its interpreter and
dependencies on first use, and job code calls external APIs. Without it the
first Python job fails with `dns error … failed to lookup address
information`.

The database stays on `app-internal` alone and has no route out. Any script an
operator writes can therefore reach the internet, and can reach the database
too — the workers hold the connection string. Restrict who can create
scripts accordingly. The same exception exists in
[Nextcloud](../nextcloud/) and [Invoice Ninja](../../business/invoiceninja/).

## Status

`scaffolded`. 2026-09-18 (1.814.0): the local and the production compose files
were booted with the hardened settings, all services reached `healthy`, the
default administrator was replaced and its login stopped working, and real
jobs ran through the API on both workers — Python on `worker`, TypeScript on
`worker-native`, each on a read-only root filesystem. Traefik routing and TLS
have not been run against a real host yet. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-18).

## Try it locally

```bash
cp .env.local.example .env.local      # set DB_PASSWORD: openssl rand -hex 32
mkdir -p volumes/local/postgres volumes/local/worker_cache
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl http://localhost:8000/api/health/status
DC="docker compose -f docker-compose.local.yml --env-file .env.local" \
  ./ops/bootstrap-admin.sh you@example.com
docker compose -f docker-compose.local.yml --env-file .env.local down
```

Until the bootstrap script has run, `admin@windmill.dev` / `changeme` works on
`http://localhost:8000`. The first Python job installs an interpreter through
`uv` and can take several minutes on a slow connection; later jobs reuse the
cache.

## Backup

| | |
|---|---|
| **Database** | PostgreSQL 18 · container `${COMPOSE_PROJECT_NAME}-db` · database `windmill` · user `postgres` |
| **Password** | `.secrets/db_pwd.txt` |
| **State** | `./volumes/postgres` — scripts, flows, schedules, resources, users, job history and the queue |
| **Reproducible** | `./volumes/worker_cache` — language runtimes and dependencies, safe to exclude |
| **Quiescing** | Not needed. The dump is consistent on its own. |

```yaml
postgresql_databases:
    - name: windmill
      container: windmill-db
      username: postgres
      password: "{credential file /srv/docker/apps/windmill/.secrets/db_pwd.txt}"
```

**Restore order:** database first, then server, then workers. The operator
account lives in the database, so a restored instance keeps it;
`.secrets/windmill_admin_pwd.txt` is its password and belongs in the same
backup as `db_pwd.txt`. Windmill also keeps `datatable`, DuckLake and fork
databases beside `windmill` in the same cluster; a single-database dump does
not carry them, so dump the whole cluster if you use those features. Full
architecture: [`backup/README.md`](../../backup/README.md).
