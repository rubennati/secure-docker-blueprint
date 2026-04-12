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

# --- Images ---
# --- Container ---
# --- General ---
# --- Network ---          (only if app-specific networks)
# --- Database ---         (only if app has a database)
# --- App Configuration ---
# --- SMTP ---             (only if app sends mail)
# --- Traefik Routing ---
# --- Secrets ---
```

## Section Rules

**Images** — one variable per image used in the compose file:
```env
APP_IMAGE=ghost:5.96.2-alpine
DB_IMAGE=mysql:8.4
```
Always pin to a specific stable version. Never `:latest`.

**Container** — one `CONTAINER_NAME_` per service:
```env
CONTAINER_NAME_APP=ghost-app
CONTAINER_NAME_DB=ghost-db
```
Pattern: `{app}-{role}`. Keep it short and clear.

**General** — shared settings:
```env
TIMEZONE=Europe/Vienna
COMPOSE_PROJECT_NAME=ghost
```
`COMPOSE_PROJECT_NAME` must match the app name. It's used for Traefik router names and the internal network name.

**Database** — non-sensitive database config:
```env
DB_MYSQL_DATABASE=ghost
DB_MYSQL_USER=ghost_user
```
Passwords are never here — they go in `./secrets/`.

**App Configuration** — app-specific settings:
```env
VW_SIGNUPS_ALLOWED=false
VW_LOG_LEVEL=warn
```
Prefix with a short app identifier when the app has many settings.

**SMTP** — mail relay configuration:
```env
VW_SMTP_HOST=smtp-relay.brevo.com
VW_SMTP_FROM=vaultwarden@example.com
VW_SMTP_PORT=587
VW_SMTP_SECURITY=starttls
VW_SMTP_USERNAME=
```
SMTP passwords go in `./secrets/`, not here.

**Traefik Routing** — always the same set of variables:
```env
APP_TRAEFIK_HOST=app.example.com
APP_TRAEFIK_CERT_RESOLVER=cloudflare-dns
APP_TRAEFIK_TLS_OPTION=tls-basic
APP_TRAEFIK_ACCESS=acc-public
APP_TRAEFIK_SECURITY=sec-2
APP_INTERNAL_PORT=80
```
See [Traefik Labels](traefik-labels.md) for valid values.

**Secrets** — generation instructions as comments:
```env
# Create the secrets directory and files:
#   mkdir -p secrets
#   openssl rand -base64 32 > secrets/db_pwd.txt
#   openssl rand -base64 32 > secrets/db_root_pwd.txt
```
This section has no actual variables — only comments that document which secrets to create.

## Rules

- **Use example.com** for all domain placeholders.
- **Use real defaults** where sensible (port numbers, log levels, timezones).
- **Group related vars** within their section — database vars together, SMTP vars together.
- **Comment non-obvious values** — explain what a setting does if the name isn't self-explanatory.
- **No secrets in .env.example** — not even example values for passwords.
- **Secrets section documents `openssl` generation commands** — so the user knows exactly what to create.

## Checklist

- [ ] Header with app name, copy instruction, and "NEVER commit" warning
- [ ] Section order matches the standard above
- [ ] All images pinned to specific version (never `:latest`)
- [ ] Container names follow `{app}-{role}` pattern
- [ ] `COMPOSE_PROJECT_NAME` matches the app name
- [ ] Domain placeholders use `example.com`
- [ ] No passwords or tokens — only in `./secrets/`
- [ ] Secrets section lists all required secret files with generation commands
