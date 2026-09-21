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

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

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
