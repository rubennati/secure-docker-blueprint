# Upstream Reference

## Source

- **Image:** https://github.com/intuitem/ciso-assistant-community/pkgs/container/ciso-assistant-community%2Fbackend
- **GitHub:** https://github.com/intuitem/ciso-assistant-community
- **Docs:** https://intuitem.gitbook.io/ciso-assistant
- **License:** AGPL-3.0
- **Origin:** France · intuitem · EU
- **Domain:** Security operations
- **Role:** Governance, risk and compliance: frameworks such as ISO 27001 and NIS2 mapped to controls, risks and evidence
- **Decision facts checked:** 2026-09-21
- **Use restrictions:** none — the community images this stack pins are released under AGPLv3, and the commercially licensed code in `enterprise/` ships only in separate enterprise binaries — https://github.com/intuitem/ciso-assistant-community/blob/main/LICENSE.md · checked 2026-09-21
- **Edition gating:** SSO/SAML, the API, multiple frameworks and self-hosting are in the community edition; the Pro edition adds, among others, SCIM group provisioning, fine-grained per-object permissions, a multi-level domain hierarchy and custom fields — https://intuitem.com/compare · checked 2026-09-21
- **Commercial model:** paid self-hosted edition — https://intuitem.com/compare · checked 2026-09-21
- **Based on version:** `v4.0.5`

No `Last verified` line yet — see [Verification performed](#verification-performed-2026-09-21)
below. The field asserts Traefik/TLS routing was confirmed on a real host, which
has not happened; this stack stays `scaffolded` until it does.

The origin comes from intuitem's legal notice (RCS Versailles, France).

## What we use

- `ghcr.io/intuitem/ciso-assistant-community/backend:v4.0.5` for backend and Huey,
  and `…/frontend:v4.0.5`. Upstream's compose pins `:latest` with `pull_policy:
  always`; not used here. Per upstream's licence file, the community binaries are
  AGPLv3; the commercially licensed code ships only in separate enterprise images.
- `postgres:16.14` — upstream's template runs `postgres:16`.
- The shape of upstream's `config/templates/docker-compose-postgresql-traefik.yml.j2`:
  backend, Huey, frontend and PostgreSQL, with `/api` routed to the backend.

## What we changed and why

| Change | Reason |
|--------|--------|
| `config/entrypoint.sh` exports `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` and `DJANGO_SUPERUSER_PASSWORD` | No `_FILE` variants; upstream's template writes the database password into the compose file |
| `DJANGO_SECRET_KEY` from a Docker Secret | Left unset, the image generates the key into the data directory, next to the data — with it set, no such file is written (verified) |
| First administrator from `DJANGO_SUPERUSER_EMAIL` and the secret | The image's `startup.sh` creates it unattended when the email is set; upstream's templates leave the variable out |
| Healthcheck against `localhost`, not `127.0.0.1` | Django answers 400 to a Host outside `ALLOWED_HOSTS`, measured |
| `start_period: 900s` on the backend | The first start took about ten minutes on the test machine: every migration plus 326 framework libraries. Later starts took about a minute |
| Frontend healthcheck in Node | The image has no shell |
| No Qdrant, no MCP server | Both are absent from upstream's PostgreSQL + Traefik template; Qdrant serves the AI features, MCP is an optional profile |

Upstream's own hardening — `read_only`, `cap_drop: ALL`, `no-new-privileges`, uid
1001 — is kept as it is.

## Verification performed (2026-09-21)

Against the production `docker-compose.yml` (Docker Secrets, wrapper,
`app-internal`) on a throwaway `proxy-public` network without Traefik:

- All four services started; the first start ran the migrations and loaded the
  framework library, and the administrator was created from the environment
  (`is_superuser` true in the database)
- Login through `POST /api/_allauth/app/v1/auth/login` returned an access token; a
  wrong password returned 400
- Public sign-up through the same API returned 403
- With `Authorization: Token …`, a domain was created and listed next to the
  built-in "Global"; without a token the API returned 401
- 326 stored libraries were available, among them ISO/IEC 27001:2013 and 2022
- The frontend redirected to its login page
- After `docker compose down` and `up`, the domain was still there
- Hardening from `docker inspect`: backend and Huey uid 1001, frontend 1000:1000,
  all three read-only with all capabilities dropped; no published port; the secret
  values absent from the configured environment; no `django_secret_key` file in the
  data directory; Huey and PostgreSQL without a route out

**Not yet exercised:** Traefik routing and TLS, including the `/api` split in
practice; the browser interface; Huey actually running a task (it started and
loaded its configuration against PostgreSQL); email; SSO; importing a framework
into an assessment; backup and restore.

## Upgrade checklist

1. Read the release notes: https://github.com/intuitem/ciso-assistant-community/releases
2. Check the GitHub Security tab for advisories against the current version
3. Back up the database, `volumes/data` and `django_secret_key.txt`
4. Bump `APP_TAG` in `.env.example` — backend, Huey and frontend move together
5. `docker compose pull && docker compose up -d`; the backend migrates at start
6. Log in and open an assessment
7. Update **Based on version** above — and add **Last verified** only if the
   upgrade was exercised on a real install
