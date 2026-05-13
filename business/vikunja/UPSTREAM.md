# Vikunja — Upstream

**Last verified: 2026-05-06 (v2.3.0)**

## Source

- **Repository:** https://github.com/go-vikunja/vikunja
- **Docker Hub:** https://hub.docker.com/r/vikunja/vikunja
- **Docs:** https://vikunja.io/docs/

## License

AGPL-3.0 — fully open source, self-hosting permitted without restrictions.

## Release notes

https://github.com/go-vikunja/vikunja/releases

## What we use

- `vikunja/vikunja` Docker Hub image as the base
- Upstream single-binary image (API + frontend combined)
- Upstream PostgreSQL recommendation for multi-user setups

## What we changed

| Deviation | Reason |
|---|---|
| Custom `Dockerfile` — multi-stage build from `busybox:musl` | Upstream image is `FROM scratch` with no shell, cat, or wget. We add `/bin/sh`, `/bin/cat`, `/bin/wget` for secrets injection and HTTP healthcheck. |
| `COPY --chown=1000:0 /files-init /app/vikunja/files` | Upstream leaves `/app/vikunja/files` root-owned; named volume inherits root ownership; Vikunja (uid=1000) cannot write. `USER` directive doesn't work in FROM scratch images. |
| Custom `config/entrypoint.sh` | Vikunja has no `_FILE` env var support. Entrypoint injects JWT key, DB password, OIDC secret, and SMTP password from Docker Secrets at startup. Uses intermediate variables to avoid POSIX `export VAR=$(cmd)` silent-failure bug. |
| HTTP healthcheck via `wget` instead of `vikunja healthcheck` | The built-in healthcheck subcommand spawns a fresh process without the entrypoint's env vars — it fails DB auth every time. |
| Authentik OIDC configured | Upstream docs show plain local login. We configure OIDC as the only login method. |
| Traefik `redirectregex` middleware for SSO auto-redirect | `/login` auto-redirects to Authentik — no manual button click required. |
| `VIKUNJA_SERVICE_IPEXTRACTIONMETHOD: xff` | Required for correct client IP behind Traefik. |
| Rate limiting enabled | `VIKUNJA_RATELIMIT_ENABLED: true` — not enabled by default upstream. |

## Upgrade checklist

1. Read the release notes for breaking changes or migration steps
2. Check if the database schema migration runs automatically (it does — Vikunja auto-migrates on startup)
3. Bump `APP_TAG` in `.env`
4. `docker compose build --pull && docker compose up -d`
5. Verify the UI loads and existing tasks are intact
6. Verify Authentik OIDC login still works
7. Update `Last verified` date and version in this file
