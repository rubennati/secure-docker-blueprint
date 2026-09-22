# Upstream Reference

## Source

- **Image:** https://github.com/psf/httpbin/pkgs/container/httpbin
- **GitHub:** https://github.com/psf/httpbin (fork of https://github.com/postmanlabs/httpbin)
- **Docs:** https://github.com/psf/httpbin — the running service lists its endpoints at `/`
- **License:** MIT or ISC (either, at the user's choice, per the repository's LICENSE)
- **Origin:** United States · Python Software Foundation · non-EU
- **Decision facts checked:** 2026-09-21
- **Domain:** Developer tools
- **Role:** HTTP request and response service for testing clients: echoes requests, returns chosen status codes, redirects, delays and payloads
- **Based on version:** `0.10.4`
- **Last verified:** 2026-09-22 (0.10.4) — behind Traefik with TLS: the endpoints through the route, `/redirect-to` refused outside the access policy, the per-request bounds, and a restart

The fork's README gives its reason: the original's maintainers could not be
reached, and the `httpbin` package on PyPI is released from the fork. It also
states that httpbin.org is served from the original repository, not from the
fork. The original publishes no versioned image — `kennethreitz/httpbin` carries
only `latest` and `test`, both from 2018.

## What we use

- `ghcr.io/psf/httpbin:0.10.4` — the fork's newest release (2026-06-16). The
  image runs Gunicorn as uid 999.

## What we changed and why

| Change | Reason |
|--------|--------|
| Gunicorn with the `gthread` worker instead of the image's start script | The script starts the `gevent` worker. In 0.10.3 and 0.10.4 that exits at start — Gunicorn 26.0.0 requires gevent 24.10.1, the image carries 24.2.1 — measured with a plain `docker run`, no hardening involved. Reported upstream in psf/httpbin#69, fix proposed in psf/httpbin#70. 0.10.2 starts, with Gunicorn 21.2.0 |
| `--no-control-socket` | Gunicorn 26 writes a control socket under `/opt/httpbin/.gunicorn`; on a read-only root that logs an error at start |
| `read_only`, `cap_drop: ALL` | The image already runs unprivileged |
| `APP_TRAEFIK_ACCESS=acc-tailscale` | No login on any endpoint, and `/redirect-to` redirects to any URL |

## Verification performed (2026-09-22)

Behind Traefik with TLS, with the shipped `acc-tailscale` and `sec-2`:

- A client outside the access policy's ranges got `403` on `/`, `/get`,
  `/status/200` and `/redirect-to?url=https://example.com/`, over IPv4 and IPv6 —
  the open redirect is closed to it
- Through the route: the root page `200` in six requests, plus one request to
  `fonts.googleapis.com` from the browser; `POST /post` echoed its JSON body;
  `/status/418` answered `418`; `/redirect-to` answered `302` with the given
  `Location`; a custom request header came back from `/headers`
- `/get` put the client's address in `origin`; `X-Forwarded-For`,
  `X-Forwarded-Proto`, `X-Forwarded-Port` and `X-Real-Ip` appeared only with
  `?show_env=1`, `X-Forwarded-Host` and `X-Forwarded-Server` always
- Bounds: `/delay/12` answered after 10.2 s; `/bytes/200000` returned 102,400 bytes
- The same answers after `docker compose down` and `up`
- Peak 41 MiB (limit 256 MiB)

**Not yet exercised:** the streaming endpoints; load.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` on a throwaway `proxy-public` network
without Traefik:

- With the replaced command the container came up healthy, with no error in its
  log
- `/get` answered 200; `/status/418` returned 418; `/anything` echoed a POST body;
  `/redirect-to?url=https://example.com/` answered 302 to that URL;
  `/basic-auth/u/p` returned 200 with the right credentials and 401 with wrong
  ones; `/delay/12` returned after 10 seconds; `/bytes/500000` returned 102,400
  bytes; `/` served the endpoint list
- Hardening from `docker inspect`: `read_only`, uid 999 for every process,
  `cap_drop: ALL`, no capability added, no published port
- `docker-compose.local.yml` started read-only and answered `/get`

**Not yet exercised:** Traefik routing and TLS; the streaming endpoints; load.

## Upgrade checklist

1. Read the releases: https://github.com/psf/httpbin/releases — once a release
   fixes psf/httpbin#69, the image's own command starts again and the replaced
   command can go
2. Bump `APP_TAG` in `.env.example`
3. `docker compose pull && docker compose up -d`
4. `GET /get` answers 200
5. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
