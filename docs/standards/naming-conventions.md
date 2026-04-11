# Naming Conventions

## Container Names

Pattern: `{app}-{role}`

| Example | Role |
|---------|------|
| `wordpress-app` | Application |
| `wordpress-db` | Database |
| `paperless-redis` | Cache/Queue |
| `dockhand-socket-proxy` | Docker Socket Proxy |

## Environment Variables

Pattern: `{SCOPE}_{PROPERTY}`

| Scope | Examples |
|-------|----------|
| `APP_` | `APP_IMAGE`, `APP_TRAEFIK_HOST`, `APP_INTERNAL_PORT` |
| `DB_` | `DB_IMAGE`, `DB_USER`, `DB_NAME` |
| `CONTAINER_NAME_` | `CONTAINER_NAME_APP`, `CONTAINER_NAME_DB` |
| `COMPOSE_` | `COMPOSE_PROJECT_NAME`, `COMPOSE_FILE` |

## Networks

| Name | Type | Created by |
|------|------|-----------|
| `proxy-public` | `external: true` | core/traefik |
| `{app}-internal` | `internal: true` | Each app |

## Volumes

Always bind mounts, never named volumes.

| Path | Content |
|------|---------|
| `./volumes/data/` | App data |
| `./volumes/mysql/` | MySQL/MariaDB |
| `./volumes/postgres/` | PostgreSQL |
| `./volumes/redis/` | Redis |
| `./config/` | Config files (committed) |

## Secrets

| Path | Content |
|------|---------|
| `./secrets/db_pwd.txt` | Database password |
| `./secrets/db_root_pwd.txt` | DB root password |
| `./secrets/jwt_key.txt` | JWT signing key |

Generate with: `openssl rand -base64 32 > secrets/name.txt`

## .env.example Structure

Fixed section order:

```
# --- Images ---
# --- Container ---
# --- General ---
# --- Database ---
# --- App Configuration ---
# --- Traefik Routing ---
# --- Secrets ---
```

Header always:

```
# =============================================
# {App Name} – Environment
# =============================================
# Copy this file to .env and adjust all values.
# NEVER commit the .env file.
# =============================================
```

## docker-compose.yml Structure

Fixed block order per service:

```
# --- Identity ---       image, container_name, restart, depends_on
# --- Security ---       security_opt, read_only, tmpfs, cap_drop, user
# --- Configuration ---  environment, secrets
# --- Storage ---        volumes
# --- Networking ---     networks, ports
# --- Traefik ---        labels
# --- Health ---         healthcheck
```
