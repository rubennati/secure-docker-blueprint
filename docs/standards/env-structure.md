# Env Structure

Rules and rationale for `.env.example` files.

For naming patterns (variable prefixes, scopes), see [Naming Conventions](naming-conventions.md).

---

## Section Order

```env
# =============================================
# {App Name} – Environment
# =============================================
# Copy this file to .env and adjust all values.
# NEVER commit the .env file.
# =============================================

COMPOSE_PROJECT_NAME=appname

# --- Domain & Traefik ---
# --- Images ---
# --- Containers ---
# --- Network ---              (only if app-specific)
# --- Database ---             (only if app has a database)
# --- App Configuration ---
# --- SMTP ---                 (only if app sends mail)
# --- Timezone ---
# --- Secrets ---
```

## Section Rules

**COMPOSE_PROJECT_NAME** — always first, no section header:
```env
COMPOSE_PROJECT_NAME=wordpress
```
This is the single source for container names, network names, and Traefik router names.

**Domain & Traefik** — how the app is exposed:
```env
# --- Domain & Traefik ---
APP_TRAEFIK_HOST=app.example.com
APP_TRAEFIK_CERT_RESOLVER=cloudflare-dns
APP_TRAEFIK_TLS_OPTION=tls-basic
APP_TRAEFIK_ACCESS=acc-tailscale
APP_TRAEFIK_SECURITY=sec-3
TRAEFIK_NETWORK=proxy-public
```
This section is second because it's what you change most often per deployment.

**Images** — one tag variable per image, with image name + Docker Hub link as comment:
```env
# --- Images ---
# wordpress (https://hub.docker.com/_/wordpress)
APP_TAG=6.7-php8.3-fpm-alpine
# mariadb (https://hub.docker.com/_/mariadb)
DB_TAG=11.4
# redis (https://hub.docker.com/_/redis)
REDIS_TAG=7.4-alpine
```

**Tag pinning rules — two tiers:**

| Image type | Pin to | Example | Rationale |
|---|---|---|---|
| **App images** | `major.minor.patch` | `32.0.6-fpm-alpine` | Patch upgrades can include DB migrations or config changes |
| **Infra images** | `major.minor` | `7.4-alpine`, `10.11`, `1.29-alpine` | Patch = security/bug fixes only; auto-update is safe |

App images: Nextcloud, Ghost, Paperless-ngx, Authentik, n8n, NocoDB, Seafile, etc.

Infra images: Redis, MariaDB, PostgreSQL, Nginx (reverse-proxy role), ClamAV, Gotenberg, Tika.

Never `:latest`. Never major-only (e.g. `8`, `v2`, `32`).

**Containers** — derived from COMPOSE_PROJECT_NAME:
```env
# --- Containers ---
CONTAINER_NAME_APP=${COMPOSE_PROJECT_NAME}-app
CONTAINER_NAME_DB=${COMPOSE_PROJECT_NAME}-db
```

**Network** — internal network name, derived from COMPOSE_PROJECT_NAME:
```env
# --- Network ---
NETWORK_INTERNAL=${COMPOSE_PROJECT_NAME}-internal
```

**Database** — non-sensitive database config:
```env
# --- Database ---
DB_NAME=wordpress
DB_USER=wp_user
```
Passwords are never here — they go in `.secrets/`.

**App Configuration** — app-specific settings:
```env
# --- App Configuration ---
VW_SIGNUPS_ALLOWED=false
VW_LOG_LEVEL=warn
```

**SMTP** — mail relay configuration:
```env
# --- SMTP ---
VW_SMTP_HOST=smtp.example.com
VW_SMTP_FROM=vaultwarden@example.com
VW_SMTP_PORT=587
VW_SMTP_SECURITY=starttls
VW_SMTP_USERNAME=
```
SMTP passwords go in `.secrets/`, not here.

**Timezone** — near the end, rarely changes:
```env
# --- Timezone ---
# Examples: UTC, Europe/Berlin, Europe/Vienna, America/New_York
TZ=UTC
```

**Secrets** — generation instructions as comments:
```env
# --- Secrets ---
# Create the secrets directory and files:
#   mkdir -p .secrets
#   openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
#   openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt
```
This section has no actual variables — only comments that document which secrets to create.

## Rules

- **Use example.com** for all domain placeholders.
- **Use real defaults** where sensible (port numbers, log levels, timezones).
- **Group related vars** within their section — database vars together, SMTP vars together.
- **Comment non-obvious values** — explain what a setting does if the name isn't self-explanatory.
- **No secrets in .env.example** — not even example values for passwords.
- **Secrets section documents `openssl` generation commands** — so the user knows exactly what to create.
- **Always strip newlines** in secret generation: `| tr -d '\n'`

## Checklist

- [ ] Header with app name, copy instruction, and "NEVER commit" warning
- [ ] `COMPOSE_PROJECT_NAME` at the top, before all sections
- [ ] Section order matches the standard above
- [ ] App images pinned to `major.minor.patch` (never `:latest`, never major-only)
- [ ] Infra images (redis, mariadb, postgres, nginx, clamav) pinned to `major.minor`
- [ ] Image name + Docker Hub link as comment above each tag variable
- [ ] Container names derived from `${COMPOSE_PROJECT_NAME}`
- [ ] `TRAEFIK_NETWORK=proxy-public` in Domain & Traefik section
- [ ] Domain placeholders use `example.com`
- [ ] `TZ=UTC` (not `TIMEZONE=`)
- [ ] No passwords or tokens — only in `.secrets/`
- [ ] Secrets section lists all required secret files with generation commands including `| tr -d '\n'`
