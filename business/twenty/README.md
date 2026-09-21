# Twenty

CRM: companies, people, opportunities, notes and tasks, with a data model you
can extend and a GraphQL and REST API for all of it. Server and worker from one
image, with PostgreSQL and Redis — the four services upstream's own compose runs.
Upstream: [Twenty](https://github.com/twentyhq/twenty).

## Architecture

```text
Internet → Traefik (TLS) → twenty-server :3000 (web interface and API)
                                  │
                     app-internal (internal: true)
                                  │
            twenty-worker · PostgreSQL 16 · Redis (job queues)
```

The server migrates the database on start and registers the scheduled jobs; the
worker runs the queued jobs.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # three secrets, data directories
sudo chown 1000:1000 volumes/storage
sudo chown 999:999 volumes/redis
docker compose up -d            # the first start migrates the database
```

Then open the site over the VPN and sign up. **The first account creates the
workspace and becomes the server administrator.** A new workspace also comes with
a handful of sample companies and people; delete them when you no longer need
them.

## The open window, and why the router starts closed

Until the first workspace exists, whoever reaches the sign-up page creates it and
becomes the administrator. `.env.example` therefore ships
`APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only.

After that, upstream's default closes the door: a second person who signs up
without an invitation is refused with "New workspace setup is disabled" —
verified. Further users join through invitations from inside the workspace.

## Mail and calendar sync need outbound access

The worker is on `app-internal` only, with no route out. That is enough for the
CRM itself, but syncing a mailbox or a calendar from Google or Microsoft runs in
the worker and needs to reach those providers. To use it, add the worker to a
network with outbound access, the same way `apps/windmill` does for its workers.
Not configured here, and not exercised.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator and members | Email + password | PostgreSQL; members join by invitation |
| API clients | API keys created in the workspace settings | PostgreSQL |
| Stored connection credentials | Encrypted with `ENCRYPTION_KEY` | Docker Secret. Upstream documents a rotation procedure with `FALLBACK_ENCRYPTION_KEY`; do not simply replace it |
| Service-to-service | Database and Redis passwords | Docker Secrets |

## Security notes

- **Secrets.** None of the variables has a `_FILE` form. `config/entrypoint.sh`
  builds the database and Redis URLs and the encryption key from the Docker Secrets
  before the image's own entrypoint runs; the values are absent from `docker inspect`.
- **Hardening.** The image already runs as uid 1000. Server and worker are
  `read_only` with `cap_drop: ALL` and `no-new-privileges`; Redis runs as uid 999,
  read-only, with its password in a tmpfs config file. No port is published.
- **Network.** Worker, PostgreSQL and Redis are on `app-internal` and have no route
  out.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-21).

## Local deployment validation

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — sign up; the first account creates the workspace
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/storage` and `.secrets/encryption_key.txt`:

```bash
docker exec twenty-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > twenty.sql
tar -czf twenty-files.tar.gz volumes/storage .secrets/encryption_key.txt
```

Redis holds only queues and caches. Restore into an empty database with `psql`,
unpack the archive, restore the `1000:1000` ownership on `volumes/storage`, and run
`docker compose up -d`. Without the original encryption key, stored connection
credentials cannot be decrypted. Restore is not exercised here.
