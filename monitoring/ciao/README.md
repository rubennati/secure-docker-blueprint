# ciao

HTTP checks with a small dashboard: a name, a URL and a cron expression per
check, a status history, and TLS expiry per target. One Rails container with
SQLite — no scheduler service, no database container.
Upstream: [brotandgames/ciao](https://github.com/brotandgames/ciao).

It sits beside [Uptime Kuma](../uptime-kuma/) and [Gatus](../gatus/) as the
smallest of the three: checks are created in the interface like Kuma's, while
the whole stack stays one container.

## Architecture

```text
Operator → Traefik (TLS) → app :3000 ──HTTP(S) checks──→ the URLs being watched
                              │
                    volumes/db (SQLite)
                              │
                    webhooks · SMTP relay (outbound)
```

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p .secrets volumes/db
openssl rand -hex 64 | tr -d '\n' > .secrets/ciao_secret_key_base.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/ciao_basic_auth_password.txt
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — sign in as the user in .env.local, with that password
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env                      # host name, basic-auth user
mkdir -p .secrets volumes/db
openssl rand -hex 64 | tr -d '\n' > .secrets/ciao_secret_key_base.txt
openssl rand -base64 24 | tr -d '\n' > .secrets/ciao_basic_auth_password.txt
touch .secrets/ciao_prometheus_password.txt .secrets/ciao_smtp_password.txt
sudo chown -R 1000:1000 volumes/db        # the image runs as uid 1000
docker compose up -d
docker compose logs ciao-app --follow     # watch for: Listening on http://0.0.0.0:3000
```

The first start migrates the database, which takes longer than the server itself
— the healthcheck allows 60 seconds for it.

The scheduler runs inside the web process, so there is no worker container to
deploy, and every active check is scheduled again when the container starts. The
interface also has a *recreate jobs* action for the case where one was lost.

Then add checks in the interface: a name, the URL, and a cron expression such as
`*/5 * * * *`. The same thing over the API:

```bash
curl -u "$CIAO_USER:$CIAO_PASS" -X POST https://ciao.example.com/checks \
  -H "Content-Type: application/json" \
  -d '{"check":{"name":"nextcloud","url":"https://cloud.example.com","cron":"*/5 * * * *","active":true}}'
```

## Notifications

Webhooks are configured through the environment, one pair of variables per
target — the endpoint and the JSON posted to it. They apply to every check, not
to one, and the list is read when the container starts, so a new target needs a
restart. `<NAME>` is any upper-case identifier:

```bash
CIAO_WEBHOOK_ENDPOINT_NTFY=https://ntfy.example.com/alerts
CIAO_WEBHOOK_PAYLOAD_NTFY={"topic":"alerts","message":"__name__ is __status_after__ (__url__)"}
CIAO_WEBHOOK_PAYLOAD_TLS_EXPIRES_NTFY={"topic":"alerts","message":"__name__ certificate expires in __tls_expires_in_days__ days"}
```

The placeholders the payload accepts are `__name__`, `__url__`,
`__check_url__`, `__status_before__`, `__status_after__`, `__tls_expires_at__`
and `__tls_expires_in_days__`; anything else stays literal. Both
[ntfy](../ntfy/) and [Gotify](../gotify/) take a webhook like this, which is how
ciao reaches a phone.

Mail is the second route and needs the `SMTP_*` settings in `.env` plus the
password secret; leave `SMTP_HOST` empty to keep it off.

## Security model

- **Basic auth is ciao's only authentication**, and it is off unless
  `CIAO_BASIC_AUTH_USER` is set: with an empty user name the interface and the
  REST API answer anyone who reaches the port. Verified against 1.10.1 — 401
  without credentials, 200 with them.
- **`acc-tailscale` by default.** The dashboard lists every URL being watched,
  which is a map of what runs where.
- **`/metrics` sits outside that basic auth.** It is off
  (`PROMETHEUS_ENABLED=false`, verified: 404). Switching it on without
  `CIAO_PROMETHEUS_USER` and the password secret leaves it unauthenticated.
- **`SECRET_KEY_BASE` comes from a Docker Secret.** Left unset, the image
  generates a new key on every start and every session from the previous start
  is void.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** — the
  image runs as uid 1000 and writes only the SQLite volume; Rails' pid, cache and
  logs go to tmpfs.
- **Outbound by design.** Checks reach the URLs they watch, and webhooks reach
  their endpoints. A check URL is a request this host makes on request of
  whoever may sign in.

## Known limits

- **The rate limit is not measured.** The chain ships `sec-2`; no first-load
  count has been taken behind Traefik.
- **One maintainer.** 263 of the commits are theirs, the next contributor has 7.
  Releases through 2026-07.
- **Images come from Docker Hub only**, and the repository publishes no image
  elsewhere.
- **Nothing here has run behind Traefik yet.** The stack is `scaffolded`: the
  hardening, the authentication and a check through the API were verified on the
  image, the route was not.

## Backup

| | |
|---|---|
| **Database** | SQLite · `./volumes/db/production.sqlite3` — the checks, their history and the TLS expiry dates |
| **State** | Nothing outside that database |
| **Reproducible** | The status history. Losing it costs graphs, not the checks |
| **Quiescing** | Stop the container, or use `sqlite3 .backup` — the database is written live and the `-wal` file belongs to it |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/ciao/volumes/db

sqlite_databases:
  - name: ciao
    path: /srv/secure-docker-blueprint/monitoring/ciao/volumes/db/production.sqlite3
```

Restore: stop the container, put `volumes/db` back, keep it owned by uid 1000,
start it. The signing key lives in `.secrets/`, not in the database — restore
both, or every session cookie issued before the restore stops working.
