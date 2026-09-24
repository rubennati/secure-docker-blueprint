# Upstream Reference

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
- **Based on version:** `v1.4.2`

## Project maturity

59 820 stars, pushed 2026-09-24, v1.4.2 on 2026-08-23. **Six critical
advisories were published on 2026-08-03 and fixed in 1.4.0** — nothing older
than that belongs on a network.

## What we use

Thirteen services from six application images, plus PostgreSQL, Valkey,
RabbitMQ and MinIO. Upstream's own shape, with the pins changed:

| | Upstream's Community Edition compose | Here |
|---|---|---|
| MinIO | `minio/minio:latest` | `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` |
| PostgreSQL | `postgres:15.7-alpine` (2024) | `postgres:15.19-alpine` |
| Valkey | `valkey/valkey:7.2.11-alpine` | `valkey/valkey:7.2.14-alpine` |
| RabbitMQ | `rabbitmq:3.13.6-management-alpine` (2024) | `rabbitmq:3.13.7-management-alpine` |

**`minio/minio` no longer exists on Docker Hub** — the API answers 404 for the
repository. Upstream's published Community Edition compose therefore names an
image that cannot be pulled. `quay.io/minio/minio` is the same image
`monitoring/langfuse` already pins.

## What we changed and why

| Change | Reason |
|--------|--------|
| Eight Docker Secrets through `config/entrypoint.sh` | Plane reads every setting from the environment and has no `_FILE` variant. Upstream's defaults are `plane`/`plane` for PostgreSQL and RabbitMQ and `access-key`/`secret-key` for MinIO |
| A second wrapper for RabbitMQ | 3.13 rejects `RABBITMQ_DEFAULT_PASS_FILE` as deprecated and exits. Its suggested alternative is a configuration file, which would put the password on the host |
| No published ports | Upstream's proxy publishes 80 and 443. Traefik fronts the bundled proxy instead, which keeps MinIO and the four interfaces off `proxy-public` |
| Network aliases on the internal network | Measured below |
| `user:` on the backend, live, Valkey and MinIO | Every Plane image declares root |
| `cap_add` per service rather than none | Measured below — three different images need three different sets |
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
- **The web and admin images are nginx** and their entrypoint chowns
  `/var/cache/nginx` before dropping to uid 101 — `chown(...) failed
  (Operation not permitted)` without `CHOWN`, `DAC_OVERRIDE`, `SETGID`,
  `SETUID`.
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
curl -sL https://github.com/makeplane/plane/releases/download/v1.4.2/docker-compose.yml

# The proxy's Caddyfile, with upstream's service names in it
docker run --rm --entrypoint sh makeplane/plane-proxy:v1.4.2 -c 'cat /etc/caddy/Caddyfile'
```
