# Naming Conventions

## Container-Namen

Pattern: `{app}-{role}`

| Beispiel | Rolle |
|----------|-------|
| `wordpress-app` | Application |
| `wordpress-db` | Database |
| `paperless-redis` | Cache/Queue |
| `dockhand-socket-proxy` | Docker Socket Proxy |

## Env-Variablen

Pattern: `{SCOPE}_{PROPERTY}`

| Scope | Beispiele |
|-------|-----------|
| `APP_` | `APP_IMAGE`, `APP_TRAEFIK_HOST`, `APP_INTERNAL_PORT` |
| `DB_` | `DB_IMAGE`, `DB_USER`, `DB_NAME` |
| `CONTAINER_NAME_` | `CONTAINER_NAME_APP`, `CONTAINER_NAME_DB` |
| `COMPOSE_` | `COMPOSE_PROJECT_NAME`, `COMPOSE_FILE` |

## Netzwerke

| Name | Typ | Erstellt von |
|------|-----|-------------|
| `proxy-public` | `external: true` | core/traefik |
| `{app}-internal` | `internal: true` | Jede App selbst |

## Volumes

Immer Bind Mounts, keine Named Volumes.

| Pfad | Inhalt |
|------|--------|
| `./volumes/data/` | App-Daten |
| `./volumes/mysql/` | MySQL/MariaDB |
| `./volumes/postgres/` | PostgreSQL |
| `./volumes/redis/` | Redis |
| `./config/` | Konfig-Dateien (committed) |

## Secrets

| Pfad | Inhalt |
|------|--------|
| `./secrets/db_pwd.txt` | Datenbank-Passwort |
| `./secrets/db_root_pwd.txt` | DB Root-Passwort |
| `./secrets/jwt_key.txt` | JWT Signing Key |

Generieren mit: `openssl rand -base64 32 > secrets/name.txt`

## .env.example Aufbau

Feste Sektionen-Reihenfolge:

```
# --- Images ---
# --- Container ---
# --- General ---
# --- Database ---
# --- App Configuration ---
# --- Traefik Routing ---
# --- Secrets ---
```

Header immer:

```
# =============================================
# {App Name} – Environment
# =============================================
# Copy this file to .env and adjust all values.
# NEVER commit the .env file.
# =============================================
```

## docker-compose.yml Aufbau

Feste Block-Reihenfolge pro Service:

```
# --- Identity ---       image, container_name, restart, depends_on
# --- Security ---       security_opt, read_only, tmpfs, cap_drop, user
# --- Configuration ---  environment, secrets
# --- Storage ---        volumes
# --- Networking ---     networks, ports
# --- Traefik ---        labels
# --- Health ---         healthcheck
```
