# ERPNext

ERP for small and mid-sized businesses on the Frappe framework: accounting,
invoicing, stock, buying, selling, manufacturing, projects and HR. Upstream:
[ERPNext](https://github.com/frappe/erpnext), deployed the way
[frappe_docker](https://github.com/frappe/frappe_docker) deploys it.

## Architecture

```text
Internet → Traefik (TLS) → erpnext-frontend :8080 (nginx)
                                  │
                     app-internal (internal: true)
                                  │
   erpnext-backend :8000 (Gunicorn) · erpnext-websocket :9000 (Socket.IO)
   erpnext-queue-short · erpnext-queue-long · erpnext-scheduler
   erpnext-configurator (runs once) · db (MariaDB 11.8)
   redis-cache · redis-queue

app-egress: erpnext-backend and both queue workers
```

One image runs every Frappe role.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # secrets and the mounted paths
sudo chown -R 1000:1000 volumes/sites volumes/logs
sudo chown -R 999:999 volumes/redis-queue
docker compose up -d
ops/create-site.sh              # about five minutes
```

`ops/create-site.sh` creates the Frappe site `SITE_NAME` — the host name — and
installs ERPNext into it. It runs upstream's `new-site` against the database and
user MariaDB created from the Docker Secrets, so Frappe never receives the MariaDB
root password. The passwords are read inside the container. A second run reports
that the site exists and changes nothing.

Log in as `Administrator` with the password in `.secrets/admin_pwd.txt`. The first
login opens the setup wizard — company, country, currency, time zone, fiscal year.

## Scheduled jobs start hours after setup

Frappe creates a new site in its default time zone, Asia/Kolkata, and records when
each scheduled job type was created in that zone. When the setup wizard switches
the site to another zone, those times lie ahead of the site's clock, and no
scheduled job runs until the clock passes them — the email queue included. The
wait is the difference between the two zones: 3 hours 30 minutes for Central
European Summer Time. Upstream behaviour; it resolves itself.

## What is mounted

| Path | Holds |
|---|---|
| `volumes/sites` → `sites/` | Site and common configuration, uploaded files, backups made by `bench` |
| `volumes/logs` → `logs/` | Frappe's logs |
| `volumes/mysql` | The database |
| `volumes/redis-queue` | The job queue |

The static assets come from the image: every container relinks `sites/assets` to
them at start, so a new image brings its own.

## Security notes

- **MariaDB root password.** Used by MariaDB alone. The site gets the database and
  user the MariaDB entrypoint creates.
- **Passwords Frappe keeps in files.** `sites/<site>/site_config.json` holds the
  site's database password, `sites/common_site_config.json` the Redis password —
  Frappe reads both from there. The Administrator password is stored only as a
  hash.
- **`bench` logs its command lines.** Every `bench` invocation is written to
  `logs/bench.log`, arguments included. The configurator and `ops/create-site.sh`
  call Frappe's command runner directly, so no password reaches the log. A `bench`
  command typed by hand with a password argument does.
- **Encryption key.** Frappe adds `encryption_key` to `site_config.json` the first
  time it encrypts a value. Encrypted values are unreadable without it.
- **Sign-up is off.** Self-registration is refused until it is switched on in
  Website Settings.
- **Hardening.** Every Frappe role runs as uid 1000 with `read_only`,
  `cap_drop: ALL`, `no-new-privileges` and no capability added back; Redis runs as
  uid 999, read-only, with a password. No port is published.
- **Network.** The database, both Redis instances, Socket.IO and the scheduler
  have no route out. The backend and the queue workers reach outward for email,
  webhooks and integrations.
- **Client addresses.** nginx takes the client address from `X-Forwarded-For`
  sent by any address on its networks, which are reachable only by Traefik and the
  stack's own containers.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
sudo chown -R 1000:1000 volumes/sites volumes/logs
sudo chown -R 999:999 volumes/redis-queue
docker compose -f docker-compose.local.yml --env-file .env.local up -d
COMPOSE_FILE=docker-compose.local.yml ENV_FILE=.env.local ops/create-site.sh
# http://localhost:8080 — Administrator, password in .secrets/admin_pwd.txt
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time. The database is the
exception: a named volume, because Frappe needs case-sensitive table names and a
bind mount from a case-insensitive filesystem does not give them.

## Backup

Back up the database, `volumes/sites` and `.secrets/`:

```bash
docker exec erpnext-db sh -c 'mariadb-dump -u"$MYSQL_USER" -p"$(cat /run/secrets/DB_PWD)" "$MYSQL_DATABASE"' > erpnext.sql
sudo tar -czf erpnext-files.tar.gz volumes/sites .secrets
```

Restore into an empty database with `mariadb`, unpack the archive, restore the
`1000:1000` ownership on `volumes/sites`, and run `docker compose up -d`. Without
the original `site_config.json` the encrypted values in the database cannot be
read. Restore is not exercised here.
