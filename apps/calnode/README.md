# Calnode

Scheduling on your own server: booking pages guests pick a slot on, an admin
interface, and a REST API with its own keys. One Go binary with SQLite in the
data volume — upstream needs no database service, no cache and no separate API
server. Upstream: [Calnode](https://github.com/Calnode/calnode).

## Architecture

```text
Guests, the admin interface and API clients → Traefik (TLS) → calnode-app :3000
                                                                  │
                                                     volumes/data (SQLite)
                                                                  │
                                              calendar providers · SMTP (outbound)
```

One host name serves all three. There is no second service.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # encryption key and recovery secret
mkdir -p volumes/data && sudo chown 1000:1000 volumes/data
docker compose up -d
ops/setup.sh you@example.com "Your Name" Europe/Vienna
```

`ops/setup.sh` calls the first-run route from inside the container and prints the
API key it returns. **Store that key — the application shows it once and cannot
read it back.** A second run answers `409 Conflict` and changes nothing.

## The open window, and why the router starts closed

`POST /v1/setup` is public and unauthenticated until it has run. Whoever calls it
first becomes the owner of the workspace. There is no setup password in front of
it, so `.env.example` ships `APP_TRAEFIK_ACCESS=acc-tailscale`: the VPN only.

That is also the tension in this stack. Guests cannot book through a closed
router, so a real booking page eventually needs a wider policy — and the admin
interface and the API sit on the same host name, behind the same policy. Opening
it is a deliberate edit after `ops/setup.sh`, by which time the setup route is
closed for good.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Owner and further users | Account in the admin interface | SQLite in `volumes/data` |
| API and agent clients | API key, `cno_…` | Created at setup and in the admin interface; stored hashed |
| Stored calendar and provider credentials | Encrypted with a key derived from `CALNODE_ENCRYPTION_KEY` | Docker Secret |
| Key recovery | `CALNODE_RECOVERY_SECRET` | Docker Secret |

The API key is accepted as `Authorization: Bearer …` and as `X-API-Key: …`.

## Security notes

- **Production mode is decided by the URL.** An `https://` `BASE_URL` marks cookies
  `Secure` and makes the encryption key mandatory — the application refuses to
  start without it, which was confirmed here. The local file uses `http://` and is
  therefore in development mode.
- **Secrets.** Neither variable has a `_FILE` form, so `config/entrypoint.sh`
  exports both Docker Secrets before the image's own entrypoint runs. They are
  absent from `docker inspect`.
- **Hardening.** The image runs as root by default; this stack pins it to
  `APP_UID:APP_GID` (1000 by default), with `read_only`, `cap_drop: ALL`,
  `no-new-privileges` and no published port. `/tmp` and the data volume are the
  only writable paths.
- **Egress.** The container sits on `proxy-public` and reaches calendar providers
  and an SMTP relay from there.
- **Litestream** is built into the image's entrypoint and streams the database to
  an object store when `LITESTREAM_REPLICA_URL` is set; if the volume comes up
  empty it restores from the replica first. Not configured here, and not exercised.

## Status

`scaffolded` — see [UPSTREAM.md](UPSTREAM.md#verification-performed-2026-09-21).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
mkdir -p volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
curl -s -X POST -H 'content-type: application/json' \
     -d '{"name":"Administrator","email":"admin@example.com","timezone":"UTC"}' \
     http://localhost:3000/v1/setup
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/data` as the production file, so run one at a
time.

## Backup

Back up `volumes/data` and both files in `.secrets/`. The directory holds the
SQLite database — users, event types, bookings and the connected calendars. Stop
the container first for a consistent copy:

```bash
docker compose stop calnode-app
tar -czf calnode-data.tar.gz volumes/data .secrets
docker compose start calnode-app
```

Restore by unpacking both back into place, restoring the `1000:1000` ownership on
`volumes/data`, and running `docker compose up -d`. Without the original
encryption key the stored calendar credentials cannot be decrypted. Litestream is
upstream's own continuous alternative to this; neither path is exercised here.
