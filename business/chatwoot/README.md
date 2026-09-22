# Chatwoot

Customer support across channels: a live-chat widget for your website, email,
and messaging inboxes in one shared queue, with agents, teams, canned responses
and automation. Rails and Sidekiq from one image, with PostgreSQL (pgvector) and
Redis. Upstream: [Chatwoot](https://github.com/chatwoot/chatwoot).

## Architecture

```text
Agents, website widget → Traefik (TLS) → chatwoot-rails :3000
                                               │
                                  app-internal (internal: true)
                                               │
                   chatwoot-sidekiq · PostgreSQL 16 + pgvector · Redis
                          │
                     app-egress → mail server, webhooks
```

The web service prepares or migrates the database on every start
(`db:chatwoot_prepare` is idempotent); the worker delivers email, notifications
and webhooks.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # three secrets, data directories
sudo chown 1000:1000 volumes/storage
sudo chown 999:999 volumes/redis
docker compose up -d            # the first start creates the database
```

Then open the site over the VPN. **The first visit shows an onboarding form that
creates the administrator** and closes itself afterwards. Email delivery needs
SMTP settings (`SMTP_*` and `MAILER_SENDER_EMAIL`, see upstream's `.env.example`),
which are not part of this stack's defaults.

## The open window, and why the router starts closed

Until the onboarding form has been submitted, whoever reaches the site creates the
administrator. `.env.example` therefore ships `APP_TRAEFIK_ACCESS=acc-tailscale`.

Public sign-up is off (`ENABLE_ACCOUNT_SIGNUP=false`, upstream's default); agents
are invited by the administrator. That is also the tension in this stack: a
website live-chat widget talks to this same host, so a public website eventually
needs a wider access policy — and the agent dashboard sits behind the same one.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator and agents | Email + password | PostgreSQL; agents join by invitation |
| API clients | Per-user access tokens, and inbox API keys | PostgreSQL |
| Sessions and encrypted fields | Derived from `SECRET_KEY_BASE` | Docker Secret. Do not change it once in use |
| Service-to-service | Database and Redis passwords | Docker Secrets |

## Security notes

- **Secrets.** None of the variables has a `_FILE` form. `config/entrypoint.sh`
  exports them from the Docker Secrets; they are absent from `docker inspect`.
- **Replaced entrypoint.** Upstream's rails entrypoint runs `bundle install` on
  every start, which writes into the image. The replacement keeps only the wait for
  the database.
- **Hardening.** The image runs as root by default; web and worker run as
  `APP_UID:APP_GID` (1000), `read_only`, with `cap_drop: ALL` and
  `no-new-privileges`. `tmp/` and `log/` are tmpfs mounts with mode 1777 — a plain
  tmpfs mounts as `755 root` and Rails could not write its cache. Redis runs as
  uid 999, read-only, with its password in a tmpfs config file. No port is published.
- **Network.** PostgreSQL and Redis have no route out. The worker is on
  `app-egress` to deliver mail and call webhooks; the web service reaches the
  internet through `proxy-public`.

## Status

Run behind Traefik with TLS on 2026-09-22 (v4.18.0): the onboarding, the
dashboard with its websocket, the API with a personal access token, a website
widget, a restart, and the restore below. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — the first visit creates the administrator
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/`, so run one at a time.

## Backup

Back up the database, `volumes/storage` and `.secrets/secret_key_base.txt`:

```bash
docker exec chatwoot-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > chatwoot.sql
tar -czf chatwoot-files.tar.gz volumes/storage .secrets/secret_key_base.txt
```

Redis holds queues and caches. Restore into an empty database with `psql`, unpack
the archive, restore the `1000:1000` ownership on `volumes/storage`, and run
`docker compose up -d`.
