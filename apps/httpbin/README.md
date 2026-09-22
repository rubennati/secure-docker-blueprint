# httpbin

An HTTP request and response service for testing HTTP clients: it echoes headers,
query arguments and bodies, and returns chosen status codes, redirects, delays and
payloads. This stack runs the [Python Software Foundation's
fork](https://github.com/psf/httpbin) of httpbin, which publishes versioned images.

## Architecture

```text
Internet → Traefik (TLS) → httpbin-app :8080 (Gunicorn)
```

One container, no state and no secrets.

## Setup

```bash
cp .env.example .env            # host name
docker compose up -d
```

The host name's root lists every endpoint.

## Security notes

- **No login, and an open redirect.** Every endpoint answers whoever reaches it,
  and `/redirect-to` sends a visitor on to any URL it is given. `.env.example`
  ships `APP_TRAEFIK_ACCESS=acc-tailscale`, the VPN only.
- **It echoes what it receives.** `/get` and `/headers` return the request's
  headers and put the client's address in `origin`; the proxy headers
  `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Port` and `X-Real-Ip`
  appear only with `?show_env=1`.
- **The root page loads fonts from Google.** Its API explorer requests
  `fonts.googleapis.com` in the visitor's browser.
- **Bounded per request.** `/delay` stops at 10 seconds and `/bytes` at 102,400
  bytes.
- **Replaced start command.** The image's own command fails in this version; the
  stack runs the same server with another worker class — see UPSTREAM.md.
- **Hardening.** `read_only`, `cap_drop: ALL`, `no-new-privileges`, the image's
  uid 999, no published port.

## Status

Run behind Traefik with TLS on 2026-09-22 (0.10.4): the endpoints through the
route, `/redirect-to` refused outside the access policy, the per-request bounds,
and a restart. Full log in
[`UPSTREAM.md`](UPSTREAM.md#verification-performed-2026-09-22).

## Try it locally

```bash
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml --env-file .env.local up -d
# http://localhost:8080
docker compose -f docker-compose.local.yml --env-file .env.local down
```

The port binds to `127.0.0.1`; Traefik is not used.

## Backup

Nothing to back up: the service keeps no state. `.env` is the only file to keep.
