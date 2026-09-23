# Gotify

A notification receiver you host yourself: applications post a message with
their own token, and the clients that hold a connection open receive it. One
container with SQLite, no external service in the path.
Upstream: [gotify/server](https://github.com/gotify/server).

It is the second receiver in this category beside [ntfy](../ntfy/); which one
fits depends on where the receiver runs, which
[monitoring/README.md](../README.md#where-the-receiver-runs) covers.

## Architecture

```text
Publishers (scripts, monitors) ──POST /message──┐
                                                ├─→ Traefik (TLS) → app :80
Clients (browser, Android app) ──stream/WS──────┘                      │
                                                            volumes/data (SQLite)
```

One host name serves the web interface, the publishing API and the client
stream. There is no second service and no database container.

## Try it locally

Runs on `http://localhost:8080` without Traefik, DNS or a certificate.

```bash
cp .env.local.example .env.local
mkdir -p .secrets volumes/data
openssl rand -base64 24 | tr -d '\n' > .secrets/gotify_admin_pass.txt
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080 — sign in as admin with that password
docker compose -f docker-compose.local.yml --env-file .env.local down
```

## Setup

```bash
cp .env.example .env                      # host name, admin user name
mkdir -p .secrets volumes/data
openssl rand -base64 24 | tr -d '\n' > .secrets/gotify_admin_pass.txt
sudo chown -R 1000:1000 volumes/data      # APP_UID:APP_GID from .env
docker compose up -d
docker compose logs gotify-app --follow   # watch for: Listen address=[::]:80
```

**The password file is read on the first start only.** Once the administrator
exists in the database, editing it changes nothing — the password is changed in
the web interface. Starting without the file creates `admin`/`admin`, which is
upstream's published default, so create the file first.

Then sign in and create an application per publisher. Each gets its own token,
and deleting that application revokes it.

## Sending a message

```bash
curl -X POST "https://gotify.example.com/message" \
  -H "X-Gotify-Key: <application-token>" \
  -F "title=Backup" -F "message=Run finished" -F "priority=5"
```

Gotify also accepts the token as `?token=<application-token>`. The header is the
better habit: a query string is written to Traefik's access log, so the token
would sit in a file that is kept and rotated on a different schedule than the
token itself.

The clients that receive it are the browser interface and the Android app, which
keeps its own connection open — upstream's README lists no iOS client. Every
client needs a path to this host; with the shipped `acc-tailscale` that means
the VPN.

## Security model

- **The administrator password is set before the first start**, from a Docker
  Secret. Self-registration is off (`GOTIFY_REGISTRATION=false`), so accounts are
  created by the administrator.
- **`read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root** — the
  server runs as `APP_UID:APP_GID`, writes only `/tmp` and the data volume, and
  binds port 80 without any capability. Verified on 2026-09-23 against 3.1.1.
- **No plugin is loaded.** `GOTIFY_PLUGINSDIR` is empty, so no plugin directory
  is created in the data volume. A Gotify plugin is compiled code that runs
  inside the server.
- **The session cookie carries `Secure`** (`GOTIFY_SERVER_SECURECOOKIE=true`),
  which holds because Traefik terminates TLS in front of it.
- **`acc-tailscale` by default.** Everything except `/health` and `/version`
  needs a token or a session, but the access policy is what keeps the interface
  off the open internet.
- **Tokens are bearer credentials.** An application token may post messages; a
  client token may read them. Neither expires on its own — revoke by deleting
  the application or client.
- **OIDC is available and off.** With it enabled, upstream's default registers
  every user of the identity provider; restrict by group before pointing it at a
  shared one.

## Known limits

- **The rate limit is not measured.** The chain ships `sec-2`. The interface is a
  single bundle and a client's stream is one long-lived request, so neither is
  expected to burst, but no first-load count has been taken behind Traefik.
- **The base image is Debian `sid`**, upstream's choice for the published image.
- **Nothing here has run behind Traefik yet.** The stack is `scaffolded`: the
  hardening above was verified on the image, the route was not.

## Backup

| | |
|---|---|
| **Database** | SQLite · `./volumes/data/gotify.db` — users, applications, clients, tokens, and messages not yet delivered |
| **State** | `./volumes/data/images` — the icons uploaded per application |
| **Reproducible** | Nothing. Everything the server holds is in the data volume |
| **Quiescing** | Stop the container, or copy the database with `sqlite3 .backup` — SQLite is written live and a file copy of a busy database can be torn |

```yaml
# /etc/borgmatic/config.yaml
source_directories:
  - /srv/secure-docker-blueprint/monitoring/gotify/volumes/data

sqlite_databases:
  - name: gotify
    path: /srv/secure-docker-blueprint/monitoring/gotify/volumes/data/gotify.db
```

Restore: stop the container, put the data directory back, make sure it still
belongs to `APP_UID:APP_GID`, start it. Tokens keep working, because they live in
that database — which is also why it is worth encrypting the archive.
