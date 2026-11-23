# Upstream Reference

- **Last verified:** 2026-11-08 (v1.4.3) — over IPv4, with Silo as the object store: /god-mode claimed, a workspace, project and work item created, an image attachment uploaded through the pre-signed URL into Silo and read back byte-identical, all still there after down/up

## Source

- **Image:** https://hub.docker.com/u/makeplane
- **GitHub:** https://github.com/makeplane/plane
- **Docs:** https://developers.plane.so/self-hosting
- **License:** AGPL-3.0
- **Use restrictions:** none for the Community Edition — https://github.com/makeplane/plane/blob/master/LICENSE.txt · checked 2026-09-24
- **Edition gating:** OIDC and SAML single sign-on are in the paid editions, which are a separate codebase rather than a flag in this one — https://plane.so/pricing · checked 2026-09-24
- **Commercial model:** paid self-hosted edition — https://plane.so/pricing · checked 2026-09-24
- **Decision facts checked:** 2026-09-24
- **Origin:** US · Plane Software, Inc. · non-EU
- **Domain:** Business operations
- **Role:** Project management — issues, cycles, modules and pages, with a collaborative editor and public project pages

## Project maturity

59 820 stars, pushed 2026-09-24, v1.4.2 on 2026-08-23. **Six critical
advisories were published on 2026-08-03 and fixed in 1.4.0** — nothing older
than that belongs on a network.

## What we use

Thirteen services from six application images, plus PostgreSQL, Valkey,
RabbitMQ and Silo (a MinIO fork). Upstream's own shape, with the pins changed:

| | Upstream's Community Edition compose | Here |
|---|---|---|
| Object store | `pgsty/silo:RELEASE.2026-09-16T00-00-00Z` | `pgsty/silo:RELEASE.2026-11-12T00-00-00Z` |
| PostgreSQL | `postgres:15.7-alpine` (2024) | `postgres:15.20-alpine` |
| Valkey | `valkey/valkey:7.2.11-alpine` | `valkey/valkey:7.2.16-alpine` |
| RabbitMQ | `rabbitmq:3.13.6-management-alpine` (2024) | `rabbitmq:3.13.7-management-alpine` |

Upstream's compose names `pgsty/silo` for the object store since v1.4.3; this
file pins the newest Silo release, the same tag `monitoring/langfuse` uses. See
"Object store: Silo instead of MinIO" below.

## What we changed and why

| Change | Reason |
|--------|--------|
| Eight Docker Secrets through `config/entrypoint.sh` | Plane reads every setting from the environment and has no `_FILE` variant. Upstream's defaults are `plane`/`plane` for PostgreSQL and RabbitMQ and `access-key`/`secret-key` for MinIO |
| A second wrapper for RabbitMQ | 3.13 rejects `RABBITMQ_DEFAULT_PASS_FILE` as deprecated and exits. Its suggested alternative is a configuration file, which would put the password on the host |
| No published ports | Upstream's proxy publishes 80 and 443. Traefik fronts the bundled proxy instead, which keeps the object store and the four interfaces off `proxy-public` |
| Network aliases on the internal network | Measured below |
| `user:` on the backend, live, Valkey and the object store | Every Plane image declares root |
| `cap_add` only on the proxy | Measured below — its Caddy binary carries a file capability. From v1.5.0 web and admin are Caddy and space is Node, and none of the three needs a capability (measured 2026-11-23) |
| `CORS_ALLOWED_ORIGINS` set to the host | Upstream leaves it empty |
| `CERT_*` deliberately unset | Measured below |

## Verified on the images (2026-09-24)

A throwaway network, no Traefik router. All twelve long-running services came
up; the migrator ran the schema and exited.

- **Routing through the bundled proxy works**: `/` 200 (web), `/god-mode/` 200
  (admin), `/spaces/` 200 (space), `/api/instances/` 200 (API).
- **`enable_signup` is `true`** in the instance API on a fresh install, which
  is what the README's first instruction is about.
- **The proxy's Caddyfile hardcodes upstream's service names** — `web:3000`,
  `api:8000`, `space:3000`, `admin:3000`, `live:3000`, `plane-minio:9000`. This
  repository gives every service a unique name, so the four interfaces and the
  API carry **network aliases** on the internal network instead. Aliases there
  collide with nothing: the network is private to this stack.
- **`CERT_ACME_CA=""` breaks the proxy.** The Caddyfile writes
  `acme_ca {$CERT_ACME_CA:https://acme-v02.api.letsencrypt.org/directory}`;
  setting the variable to an empty string overrides that default and leaves the
  directive with no argument — `Error: adapting config using caddyfile:
  parsing caddyfile tokens for 'acme_ca': wrong argument count`. Leaving the
  variables unset is what keeps the defaults.
- **The proxy binary carries `cap_net_bind_service=ep`.** With `cap_drop: ALL`
  the kernel refuses the exec itself: `exec /usr/bin/caddy: operation not
  permitted`, naming neither the file's capability nor the reason. `cap_add:
  NET_BIND_SERVICE` is what makes it start.
- **The web and admin images were nginx up to v1.4.3** and their entrypoint
  chowned `/var/cache/nginx` before dropping to uid 101 — `chown(...) failed
  (Operation not permitted)` without `CHOWN`, `DAC_OVERRIDE`, `SETGID`,
  `SETUID`. From v1.5.0 both are Caddy and need none of them; see Version notes.
- **The backend runs as root and `/code` is world-writable** (`drwxrwxrwx`),
  which is how it gets away with it. Running it as uid 1000 works and is what
  this stack does; running it as root with `cap_drop: ALL` does **not**,
  because the log directory bind mount then needs `DAC_OVERRIDE`.
- **The live image's command is `node apps/live`**, through its own
  `docker-entrypoint.sh`. There is no `live/dist/server.js`.
- **The backend image has no curl and no wget**, so the health check uses the
  Python interpreter that is certainly there.
- Idle, nothing in the queue: worker 638 MiB anonymous, beat-worker 138, API
  136, live 126, space 89, RabbitMQ 88, MinIO 80, proxy 12, Valkey 7,
  PostgreSQL 5, web 3, admin 3. About 1.4 GiB for the stack at rest.

What a host run still has to establish: the route through `core/traefik`,
claiming `/god-mode`, a workspace with real content, an upload through MinIO,
the live editor with two browsers, and a restore from the volumes.

## What reaches the network on its own

**Telemetry every six hours**, carrying the instance domain and every workspace
slug, to `telemetry.plane.so`. There is **no environment variable for it**: the
task checks `instance.is_telemetry_enabled`, a field on the instance record, so
it is switched off in `/god-mode` after setup rather than in this compose file.
The README says so in its setup steps.

## Object store: Silo instead of MinIO

MinIO withdrew its public container images on 2026-09-24: `quay.io/minio/minio`
answers `401 Unauthorized`, the Docker Hub repository is gone, and
[`minio/minio`](https://github.com/minio/minio) was archived on GitHub with its last
push on 2026-04-24. The tag pinned here before, `RELEASE.2025-09-07T16-13-09Z`,
could not be pulled from anywhere public, so the stack did not start.

The store is now [`pgsty/silo`](https://github.com/pgsty/silo) (AGPL-3.0), a
maintained MinIO fork with release tags on Docker Hub. Upstream's own Community Edition compose names it since v1.4.3. It reads
MinIO's variables (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD_FILE`) and serves the S3
API on port 9000, so the service keeps the name `plane-minio` and its clients are
unchanged. The image has no `mc`; the healthcheck is Silo's own
`silo healthcheck ready`. It runs as uid 1000 with `cap_drop: ALL` and no
capability added.

Not tested: a data directory written by the old MinIO image. Every run of this
stack since the withdrawal started empty.

## Version notes

- Moved to `v1.5.0` (2026-11-16) on 2026-11-23, all six images together. 19
  advisories fixed in 1.5.0 (https://github.com/makeplane/plane/security/advisories),
  5 high: GHSA-9xw4-p247-rjgx (`PUT` on projects, work items and modules fell through
  to a handler that only checked sign-in, so any account could rewrite them and move
  a project into its own workspace), GHSA-26x6-rcfm-vmf9 (a workspace member could
  make a secret project public and join it), GHSA-hvx3-58mp-5fpx (read and comment
  on work items in other workspaces), GHSA-h4w5-vhxc-265g (read, change and delete
  other workspaces' published boards), GHSA-82hp-5m7w-qqqm (download, copy and
  restore files of other projects); 14 medium: GHSA-9382-fr89-xp7w,
  GHSA-4ww6-7fp7-m5q8, GHSA-w7fx-v6rg-mrgr, GHSA-6xvg-x5h6-69p8,
  GHSA-9m3q-w2rr-h96c, GHSA-vhwc-995m-8fhx, GHSA-hfwx-f8q3-r2xf,
  GHSA-3m9w-xfj8-69g3, GHSA-wq96-4xjj-j4qg, GHSA-vfqm-7rh7-84hq,
  GHSA-r68c-48rr-m67f, GHSA-h4p4-mwfg-qh82, GHSA-xvc5-m5jf-gvpj,
  GHSA-4jpp-964m-27cr. All need a signed-in account or API token, so they reach
  every instance with more than one user or workspace. The release also requires a
  matching OAuth `state`, refuses `next_path` redirects to other hosts, marks the
  session and CSRF cookies `Secure` when `WEB_URL` is https, rate-limits sign-in by
  client IP and checks page access on every live-collaboration connection.
  Breaking changes and what they mean here: the admin and web images serve with Caddy
  on port 3000 instead of nginx, and space was already Node, so the `cap_add` that
  the nginx entrypoint needed (`CHOWN`, `DAC_OVERRIDE`, `SETGID`, `SETUID`) is gone
  from all three — measured: all three healthy with `cap_drop: ALL` and no
  `cap_add`. Browser writes with a session cookie are refused unless their `Origin`
  is the instance host, `WEB_URL` or a CORS or CSRF trusted origin; this stack sets
  `WEB_URL` and `CORS_ALLOWED_ORIGINS` to the host name (measured: same origin `200`,
  `Origin: http://evil.example` `403 CSRF Failed: origin not allowed`); API-key
  clients send no `Origin` and are not affected. The live server checks page access
  through the API on every connection, so live and API run from the same tag, which
  `APP_TAG` already ensures. PostHog is removed (`POSTHOG_*` are no longer read).
  The external API ignores `created_by` and `created_at` in request bodies and answers
  `404` for sub-resources of a missing work item. `rediss://` now verifies the
  certificate (this stack uses plain `redis://` on the internal network). New
  optional `NUM_PROXIES` for the API's rate-limit client IP is left unset: DRF then
  keys on the whole `X-Forwarded-For`, which Traefik writes and the bundled proxy
  extends. Three migrations (`db.0123` to `db.0125`) run in the migrator. Upgrade
  tested on the local file: `v1.4.3` with a workspace, project and work item, then
  `v1.5.0`: the three migrations applied, the work item read back through the API,
  `/`, `/god-mode/`, `/spaces/` and `/api/instances/` answered `200`, password sign-in
  through `/auth/sign-in/` worked. Sources:
  https://github.com/makeplane/plane/releases/tag/v1.5.0,
  https://github.com/makeplane/plane/security/advisories
- Moved to `v1.4.3` on 2026-10-31 (released 2026-10-28), all six images together. No breaking change, variable, migration or image order is
  labelled; the REST API now answers a validation error for assignees or labels
  outside the project instead of dropping them. The release fixes access-control
  issues (project publish, published boards, sub-work-items, invitations, sign-in
  rate limiting) and raises sanitize-html, djangorestframework, sharp, js-yaml,
  fast-uri, qs, morgan and postcss-selector-parser; npm is removed from the
  runtime images. Upstream's bundled object store is now `pgsty/silo` pinned to a
  release tag, the image this stack runs (see "Object store: Silo instead of
  MinIO").

## Upgrade checklist

1. Read the release notes — https://github.com/makeplane/plane/releases
2. Raise `APP_TAG` in `.env` and in `.env.local.example`; all six application
   images share it
3. `docker compose pull && docker compose up -d` — the migrator runs first and
   the rest wait for it
4. `docker compose logs plane-migrator` — migrations applied without error
5. Open a project and check that the live editor still connects
6. Record the result in `Last verified` once it ran behind `core/traefik`

## Diff against upstream

```bash
# Upstream's Community Edition compose — the one setup.sh downloads
curl -sL https://github.com/makeplane/plane/releases/download/v1.5.0/docker-compose.yml

# The proxy's Caddyfile, with upstream's service names in it
docker run --rm --entrypoint sh makeplane/plane-proxy:v1.5.0 -c 'cat /etc/caddy/Caddyfile'
```
