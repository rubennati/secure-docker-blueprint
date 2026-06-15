# Seafile CE — Thumbnail 403 Forbidden — 2026-06-15

## Bug: `/thumbnail/...` returns 403 Forbidden

**Symptom:** Browser (and Seahub) gets HTTP 403 when requesting any `/thumbnail/…`
URL. Image and video previews are broken. All other Seafile features work normally.

**Affected blueprint:** `apps/seafile/` (Community Edition)

---

## Root cause 1: Missing `JWT_PRIVATE_KEY` in thumbnail container

The production thumbnail container showed:

```
THUMB JWT direct bytes: 0
THUMB JWT_FILE: /run/secrets/JWT_KEY

APP JWT direct bytes: 65
APP JWT_FILE:
```

The thumbnail-server image does not use the shared `config/entrypoint.sh` wrapper.
Every other Seafile service in this blueprint (main `seafile`, `seadoc`,
`notification-server`, `seafile-md-server`) mounts `entrypoint.sh` and starts it
as the container entrypoint — that wrapper reads `/run/secrets/*` and exports the
real values as environment variables before `exec`-ing the original command.

The `thumbnail-server` container skips this wrapper entirely and starts its own init
process directly. `JWT_PRIVATE_KEY_FILE` and `SEAFILE_MYSQL_DB_PASSWORD_FILE` are
set in the container environment, but neither the thumbnail server's init system nor
the image's startup scripts reads `_FILE` suffixes. The actual values never reach the
process, so JWT validation always fails → 403.

**Why the Pro blueprint doesn't have this problem:** `apps/seafile-pro/` passes
`JWT_PRIVATE_KEY=${JWT_PRIVATE_KEY}` and `SEAFILE_MYSQL_DB_PASSWORD=…` as direct
environment variables, with no Docker Secrets at all (see
`docs/bugfixes/seafile-pro-2026-04-13.md`, Bug #3).

---

## Root cause 2: Traefik router priority missing

When multiple Traefik routers share the same `Host(…)` rule, Traefik picks the
one with the highest priority. Without explicit priorities, routers are ranked by
rule length. A bare `Host(files.example.com)` rule on the main `seafile` router
can match first and forward the request to the main container instead of the
thumbnail-server, resulting in a 403 from Seahub (which doesn't serve thumbnails
directly).

The fix is the same pattern already used in `apps/seafile-pro/`:
- main router → `priority=1` (lowest, catch-all)
- all PathPrefix sub-service routers → `priority=100` (higher)

---

## Fix applied

### `thumbnail-server.yml`

Added direct environment variables:

```yaml
SEAFILE_MYSQL_DB_PASSWORD: ${SEAFILE_MYSQL_DB_PASSWORD}
JWT_PRIVATE_KEY: ${JWT_PRIVATE_KEY}
```

Both `_FILE` variants are kept in the environment block (as documentation of what
secret file backs each value) but have no functional effect at runtime.

Added `priority=100` to the Traefik router label.

### `seafile-server.yml`

Added `priority=1` to the main Traefik router label.

### `notification-server.yml` and `seadoc.yml`

Added `priority=100` to all PathPrefix sub-service routers. These routers weren't
intercepted in practice before (rule length was longer than the bare `Host` rule),
but the explicit priority makes the intent unambiguous and future-proof.

### `.env.example`

Added `JWT_PRIVATE_KEY=` and `SEAFILE_MYSQL_DB_PASSWORD=` as explicit placeholders
at the bottom. These must be filled in from the corresponding secret files:

```bash
JWT_PRIVATE_KEY=$(cat .secrets/jwt_key.txt)
SEAFILE_MYSQL_DB_PASSWORD=$(cat .secrets/seafile_db_pwd.txt)
```

---

## Why this differs from upstream Seafile docs

The official Seafile multi-container documentation assumes nginx or Caddy as the
reverse proxy. Nginx `location` blocks have implicit path specificity — more specific
locations match first without any priority configuration. When we replace nginx with
Traefik, Traefik requires explicit `priority` labels to replicate this behaviour.

The official compose also passes all credentials as direct environment variables
(no `_FILE`, no Docker Secrets). This blueprint uses Docker Secrets for most
services to avoid plaintext credentials in `.env`. The thumbnail-server is the
exception because it cannot benefit from the entrypoint wrapper.

---

## Production rollout

**Minimal recreate — only `seafile` and `thumbnail-server` need to be restarted.**
`notification-server` and `seadoc` router priority changes take effect when those
containers are next recreated; they don't require an immediate restart.

```bash
# 1. Back up
cp .env .env.bak
cp apps/seafile/seafile-server.yml apps/seafile/seafile-server.yml.bak
cp apps/seafile/thumbnail-server.yml apps/seafile/thumbnail-server.yml.bak

# 2. Add the direct credential vars to .env
#    (values must exactly match the content of the secret files)
printf '\nJWT_PRIVATE_KEY=%s\n' "$(cat .secrets/jwt_key.txt)" >> .env
printf 'SEAFILE_MYSQL_DB_PASSWORD=%s\n' "$(cat .secrets/seafile_db_pwd.txt)" >> .env

# 3. Validate merged config
docker compose config --quiet

# 4. Recreate only affected containers
docker compose up -d --force-recreate seafile thumbnail-server

# 5. Verify JWT is now present (non-zero byte count, secret not printed)
docker compose exec thumbnail-server sh -lc 'printenv JWT_PRIVATE_KEY | wc -c'
docker compose exec thumbnail-server sh -lc 'printenv SEAFILE_MYSQL_DB_PASSWORD | wc -c'

# 6. Verify Traefik priorities
docker inspect seafile-app \
  --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
  | grep -E "traefik.http.routers.*(rule|priority)"

docker inspect seafile-thumbnail \
  --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
  | grep -E "traefik.http.routers.*(rule|priority)"

# 7. Test thumbnail generation in the browser or via curl
#    (requires a valid session cookie)
```

---

## Verification commands (safe — no secrets printed)

```bash
# JWT byte count in each container
docker compose exec seafile sh -lc 'printenv JWT_PRIVATE_KEY | wc -c'
docker compose exec thumbnail-server sh -lc 'printenv JWT_PRIVATE_KEY | wc -c'
docker compose exec thumbnail-server sh -lc 'printenv SEAFILE_MYSQL_DB_PASSWORD | wc -c'

# Router priorities (labels on running containers)
docker inspect seafile-app \
  --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
  | grep -E "traefik.http.routers.*(rule|priority)"

docker inspect seafile-thumbnail \
  --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' \
  | grep -E "traefik.http.routers.*(rule|priority)"
```

---

## Lesson

Phusion `my_init` and image-bundled init systems do not propagate environment
variables set in Docker Compose `environment:` blocks through to sub-processes the
same way a simple shell process does. When a service uses its own init daemon (rather
than the shared `entrypoint.sh` wrapper), any `_FILE` convention must either be
supported natively by that service's code or bypassed with direct env vars.

Always verify with `printenv VAR | wc -c` (byte count, not value) after adding a
new service to confirm the expected variables are actually present at runtime.
