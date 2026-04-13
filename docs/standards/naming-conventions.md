# Naming Conventions

## Service Names

Use short, generic names in `docker-compose.yml`:

| Role | Name |
|------|------|
| Application | `app` |
| Database | `db` |
| Cache / Queue | `redis` |
| Web server | `nginx` |
| Docker socket proxy | `socket-proxy` |

## Container Names

Derived from `COMPOSE_PROJECT_NAME` via variables:

```env
CONTAINER_NAME_APP=${COMPOSE_PROJECT_NAME}-app
CONTAINER_NAME_DB=${COMPOSE_PROJECT_NAME}-db
CONTAINER_NAME_REDIS=${COMPOSE_PROJECT_NAME}-redis
```

| Example | Value |
|---------|-------|
| `CONTAINER_NAME_APP` | `wordpress-app` |
| `CONTAINER_NAME_DB` | `wordpress-db` |
| `CONTAINER_NAME_REDIS` | `paperless-redis` |

## Environment Variables

Pattern: `{SCOPE}_{PROPERTY}`

| Scope | Examples |
|-------|----------|
| `APP_` | `APP_TAG`, `APP_TRAEFIK_HOST` |
| `DB_` | `DB_TAG`, `DB_USER`, `DB_NAME` |
| `CONTAINER_NAME_` | `CONTAINER_NAME_APP`, `CONTAINER_NAME_DB` |
| `COMPOSE_` | `COMPOSE_PROJECT_NAME` |
| `TRAEFIK_` | `TRAEFIK_NETWORK` |

## Image References

Image name hardcoded in compose, only the tag as variable. Image name + Docker Hub link as comment in `.env.example`:

```yaml
# docker-compose.yml
image: wordpress:${APP_TAG}
```
```env
# .env.example
# wordpress (https://hub.docker.com/_/wordpress)
APP_TAG=6.7-php8.3-fpm-alpine
```

## Networks

| Name | Type | Created by |
|------|------|-----------|
| `proxy-public` | `external: true` | core/traefik |
| `{app}-internal` | `name: ${COMPOSE_PROJECT_NAME}-internal` | Each app |

## Secrets

Stored in `.secrets/` (hidden dotfolder, gitignored):

| Path | Content |
|------|---------|
| `.secrets/db_pwd.txt` | Database password |
| `.secrets/db_root_pwd.txt` | DB root password |
| `.secrets/jwt_key.txt` | JWT signing key |

Generate with: `openssl rand -base64 32 | tr -d '\n' > .secrets/name.txt`

## .env.example Structure

Fixed section order:

```
COMPOSE_PROJECT_NAME=...

# --- Domain & Traefik ---
# --- Images ---
# --- Containers ---
# --- Network ---
# --- Database ---
# --- App Configuration ---
# --- SMTP ---
# --- Timezone ---
# --- Secrets ---
```

For detailed rules and rationale, see [Env Structure](env-structure.md).

## docker-compose.yml Structure

Fixed block order per service:

```
# --- Identity ---       image, container_name, restart, depends_on
# --- Security ---       security_opt, read_only, tmpfs, cap_drop, user
# --- Configuration ---  entrypoint, environment, secrets
# --- Storage ---        volumes
# --- Networking ---     networks, ports
# --- Traefik ---        labels
# --- Health ---         healthcheck
```

For detailed rules, common patterns, and checklist, see [Compose Structure](compose-structure.md).
