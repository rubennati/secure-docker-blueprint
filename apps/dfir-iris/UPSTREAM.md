# Upstream Reference

## Source

- **Image:** https://github.com/dfir-iris/iris-web/pkgs/container/iriswebapp_app
- **GitHub:** https://github.com/dfir-iris/iris-web
- **Docs:** https://docs.dfir-iris.org
- **License:** LGPL-3.0
- **Origin:** France · Airbus CyberSecurity (SAS), confirmed via copyright headers in upstream's own source files (`docker/webApp/iris-entrypoint.sh`, the nginx entrypoint) · EU
- **Domain:** Security operations
- **Role:** Collaborative incident-response case management: cases, indicators, evidence and timelines
- **Based on version:** `v2.4.29`
- **Verification snapshot:** 2026-09-19 — full 4-service local Compose
  stack booted end to end (rabbitmq, db, app, worker all healthy or
  correctly running), real Docker Secrets exercised throughout, initial
  admin credential generation confirmed; not yet run behind a real Traefik
  host

## What we use

- `ghcr.io/dfir-iris/iriswebapp_app:v2.4.29` (used for both `app` and
  `worker` — same image, different command, matching upstream's own shape)
- `ghcr.io/dfir-iris/iriswebapp_db:v2.4.29` — a Postgres image with IRIS's
  own init scripts layered on top (not vanilla `postgres`)
- `rabbitmq:3-management-alpine` — the official image, matching upstream's
  own compose file exactly

## nginx is not included — verified, not assumed

Read `docker/webApp/iris-entrypoint.sh`, the nginx image's own
`/entrypoint.sh`, and its actual runtime `nginx.conf` template directly
from a live container (not the vestigial `conf.d/default.conf` the base
nginx image also ships, which the entrypoint never touches). Confirmed:
nginx's entrypoint runs exactly one `envsubst` substitution
(`INTERFACE_HTTPS_PORT`, `IRIS_UPSTREAM_SERVER`, `IRIS_UPSTREAM_PORT`,
`SERVER_NAME`, `KEY_FILENAME`, `CERT_FILENAME`) and the resulting config
does TLS termination, a set of security headers, and a reverse proxy to
`app:8000` — including a WebSocket-upgrade block for `/socket.io` and two
upload paths with extended timeouts and unbuffered request bodies for
large evidence files. None of this is IRIS-specific business logic; all of
it is standard reverse-proxy behavior Traefik already provides. See
README.md#architecture for what was not carried over 1:1 and why.

`IRIS_FRONTEND_SERVER`/`IRIS_FRONTEND_PORT`/`IRIS_SVELTEKIT_FRONTEND_DIR`
appear in upstream's `.env.model` but are **not** referenced by the actual
nginx entrypoint's `envsubst` call in `v2.4.29` — these are forward-looking
scaffolding for a not-yet-released SvelteKit frontend rearchitecture, not
part of the current stable release's real request path — confirmed by
reading the entrypoint script itself, not the env file.

## What we changed vs. upstream

| Change | Reason |
|--------|--------|
| nginx dropped, Traefik fronts `app` directly | See above |
| Custom entrypoint wrapper on `db`, `app` and `worker` for secret injection | Verified: no `_FILE` support anywhere — not on IRIS's own `POSTGRES_ADMIN_PASSWORD` (a custom var an IRIS-specific init script reads as plain text, confirmed by reading `10-create_user.sh` directly), and not on `IRIS_SECRET_KEY`/`IRIS_SECURITY_PASSWORD_SALT`. The base `postgres` image's own `POSTGRES_PASSWORD_FILE` mechanism exists but is bypassed here too, for a single consistent pattern across all three services rather than a mixed one |
| `cap_drop: ALL` on `app`/`worker`/`db`/`rabbitmq`, with `cap_add` restoring what `db`/`rabbitmq` need to start as root and drop | Verified against live containers: neither `app` nor `worker` has any non-root user to drop to at all (confirmed empty `/etc/passwd` beyond system accounts) — a real upstream limitation, not a choice this stack made |
| No `read_only` on `app`/`worker` | Not verified narrow enough — see README.md's Security model |
| `command: ["postgres"]` added explicitly to `db` | **A real, non-obvious finding**: overriding a service's `entrypoint:` in Compose does not forward the image's own default `CMD` as arguments. Without this, the wrapper's final `exec docker-entrypoint.sh` ran with zero arguments, matched none of the postgres entrypoint's own argument checks, and exited 0 immediately — a silent restart loop with no log output at all across 8+ restart attempts, confirmed only by re-running the wrapper manually with `bash -x` inside the container |

## What was actually verified, and how

- Booted `rabbitmq` and `db` first: both reported healthy.
- `db` initially crash-looped silently (exit 0, zero log lines, `Restarting`
  within ~200ms every cycle). Diagnosed with `bash -x` tracing inside a
  `sleep`-overridden version of the same container — traced to the missing
  `command:` documented above, not to the secret-injection logic itself
  (which traced correctly, printing the real decrypted values under `-x`
  before the final `exec`).
- Booted `dfir-iris-app`: real database migrations (30+ named Alembic
  revisions) ran to completion, followed by module registration
  (`iris_misp_module`, `iris_check_module`, `iris_webhooks_module`,
  `iris_intelowl_module`) and post-init (initial customer, initial case,
  asset icon symlinks), ending in upstream's own `IRIS IS READY` banner and
  a freshly generated admin password printed once.
- The healthcheck initially used `curl -fsSk .../ | grep -qi iris`, which
  failed: the root path is a 302 redirect to `/login` with no "iris" text
  of its own, and `curl -f` treats a redirect as success regardless, so the
  check never actually confirmed the app was serving real content. Fixed
  to `curl -fsSkL` (follow the redirect) — confirmed `/login` does contain
  "IRIS" text.
- Booted `dfir-iris-worker`: connected to RabbitMQ, registered its task
  queues, and started its Celery Beat scheduler — confirmed via logs
  showing the real task list (`pipeline_dispatcher`, `task_hook_wrapper`,
  the updater tasks) rather than just "container is up".
- **Not verified:** a large evidence-file upload through Traefik (the
  timeout behavior nginx specially handled — see above), OIDC/LDAP
  sign-in, TLS/Traefik behind a real domain, and a restore rehearsal.

## Upgrade checklist

1. Watch [DFIR-IRIS releases](https://github.com/dfir-iris/iris-web/releases)
2. Read the changelog for migration or module-interface-version changes
3. Back up the database, all four volumes and the four secrets together
   before upgrading — see README.md#backup
4. Bump `APP_TAG` in `.env` (the `app`/`worker` and `db` images should move
   together — they are versioned as one release)
5. `docker compose pull && docker compose up -d`
6. Watch `docker compose logs -f dfir-iris-app` for migrations to complete
   before assuming the new version is ready

## Known limitations

- **No non-root user exists in the `app`/`worker` image** — see README.md's
  Security model.
- **No `read_only` on `app`/`worker`** — not yet safely verified.
- **Large evidence-file upload timeout behavior through Traefik is
  unverified** — nginx specially handled this upstream; Traefik's defaults
  have not been tested against a comparably large upload.
- **OIDC/LDAP not configured or exercised.**
- **No restore rehearsal has been performed.**
