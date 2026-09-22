# calrs

Scheduling on your own server: bookable meeting types, a public page guests pick
a slot on, and availability read from a CalDAV calendar you already run. One
container with SQLite — upstream ships no database service and needs none.
Upstream: [calrs](https://github.com/olivierlambert/calrs).

## Architecture

```text
Guests and the administrator → Traefik (TLS) → app :3000
                                                 │
                                    volumes/data (SQLite)
                                                 │
                                    CalDAV server · SMTP relay (outbound)
```

One host name serves both the booking pages and the administrator's own pages.
There is no second service and no separate database.

## Setup

```bash
cp .env.example .env            # host name
ops/init.sh                     # the encryption key
mkdir -p volumes/data && sudo chown 999:999 volumes/data
docker compose up -d
ops/bootstrap-admin.sh you@example.com "Your Name"
```

`ops/bootstrap-admin.sh` creates the first administrator and closes registration.
It asks for the password once and cannot be piped — the prompt comes from the
application and needs a terminal. Run it a second time and it reports that a user
exists and changes nothing.

Then connect a calendar in the dashboard under *Sources*: a CalDAV URL with its
own credentials, which are encrypted with the key from `ops/init.sh`. Set up the
SMTP relay before the booking page is shared: without one, a booking still tells
the guest that a confirmation email has been sent.

## The command line

Run the `calrs` command line through the entrypoint, as `ops/bootstrap-admin.sh`
does:

```bash
docker compose exec calrs-app /bin/sh /entrypoint.sh calrs user list
```

`docker compose exec` bypasses the entrypoint. A bare `calrs` starts without
`CALRS_SECRET_KEY`, generates its own `secret.key` in `volumes/data` and encrypts
with that — while the server keeps using the Docker Secret, so CalDAV and SMTP
passwords set from the command line that way cannot be read by it.

## The open window, and why the router starts closed

Before the bootstrap has run, whoever reaches the instance first can register and
becomes the administrator. There is no setup password to protect that window, so
`.env.example` ships `APP_TRAEFIK_ACCESS=acc-tailscale`: the VPN only.

That is also the tension in this stack. Guests cannot book through a closed
router, so a real booking page eventually needs a wider policy — and the
administrator's pages sit on the same host name, behind the same policy. Opening
it is a deliberate edit after the bootstrap, not the default, and what it exposes
is the login form rather than an open registration form.

## Credentials

| Who | Credential | Where it lives |
|---|---|---|
| Administrator and further users | Email + password | SQLite in `volumes/data`; accounts are created with `calrs user create`, through the entrypoint |
| Stored CalDAV and SMTP passwords | Encrypted with `CALRS_SECRET_KEY` | Docker Secret. Do not change it once calendars are connected |
| Browser sessions | Cookie, with a separate cross-site request forgery token | Set by the application |

## Security notes

- **Secrets.** `CALRS_SECRET_KEY` has no `_FILE` variant, so `config/entrypoint.sh`
  exports the Docker Secret before starting the binary. The key is absent from
  `docker inspect`. Given the environment variable, the application does not write
  its own `secret.key` into the data directory — as long as command-line calls go
  through the entrypoint too, see above.
- **Hardening.** The image already runs as uid 999. `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, no published port; `/tmp` is the only writable path besides
  the data volume.
- **Cross-site request forgery.** The token is delivered in a `__Host-` cookie and
  must be posted back as `_csrf`. A POST without it is refused. Because the cookie
  is `Secure`, the login flow only works over HTTPS — which is how it is served.
- **Egress.** The container sits on `proxy-public` and reaches its CalDAV server
  and SMTP relay from there.
- **Google Calendar.** Not supported upstream: Google requires OAuth2 for CalDAV.
  Bridge it through a CalDAV server that subscribes to the calendar.

## Status

Run behind Traefik with TLS on 2026-09-22 (1.17.1): the bootstrap, the
administrator's login, an event type booked by a guest, a restart, and the restore
below. Full log in [`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
ops/init.sh
mkdir -p volumes/data
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:3000 — register; the first account is the administrator
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik and the Docker Secrets mechanism are not
used. It mounts the same `volumes/data` as the production file, so run one at a
time.

## Backup

Back up `volumes/data` and `.secrets/calrs_secret_key.txt`. The directory holds
the SQLite database — users, event types, bookings and the connected calendars.
Stop the container first for a consistent copy:

```bash
docker compose stop calrs-app
tar -czf calrs-data.tar.gz volumes/data .secrets/calrs_secret_key.txt
docker compose start calrs-app
```

Restore by unpacking both back into place, restoring the `999:999` ownership on
`volumes/data`, and running `docker compose up -d`. Without the original key the
stored CalDAV and SMTP passwords cannot be decrypted, and each calendar has to be
reconnected.
