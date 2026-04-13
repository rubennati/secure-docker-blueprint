#!/bin/sh
set -e

# =============================================
# Shared entrypoint for all Seafile services.
# Reads Docker Secrets and exports them as
# plain environment variables, then exec's
# the original service command.
#
# Why: Seafile reads passwords via os.environ
# only — no _FILE support. This wrapper bridges
# Docker Secrets to env vars.
# =============================================

# --- Secrets → env vars ---
[ -f /run/secrets/DB_ROOT_PWD ] && \
  export INIT_SEAFILE_MYSQL_ROOT_PASSWORD="$(cat /run/secrets/DB_ROOT_PWD)"

[ -f /run/secrets/SEAFILE_DB_PWD ] && \
  export SEAFILE_MYSQL_DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)" && \
  export DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)"

[ -f /run/secrets/SEAFILE_ADMIN_PWD ] && \
  export INIT_SEAFILE_ADMIN_PASSWORD="$(cat /run/secrets/SEAFILE_ADMIN_PWD)" && \
  export SS_FIRST_ADMIN_PASSWORD="$(cat /run/secrets/SEAFILE_ADMIN_PWD)" && \
  export INIT_SS_ADMIN_PASSWORD="$(cat /run/secrets/SEAFILE_ADMIN_PWD)"

[ -f /run/secrets/JWT_KEY ] && \
  export JWT_PRIVATE_KEY="$(cat /run/secrets/JWT_KEY)" && \
  export SEAFILE_AI_SECRET_KEY="$(cat /run/secrets/JWT_KEY)"

[ -f /run/secrets/REDIS_PWD ] && \
  export REDIS_PASSWORD="$(cat /run/secrets/REDIS_PWD)"

[ -f /run/secrets/ONLYOFFICE_JWT_SECRET ] && \
  export ONLYOFFICE_JWT_SECRET="$(cat /run/secrets/ONLYOFFICE_JWT_SECRET)"

# --- Persist env vars for my_init ---
# Phusion's my_init re-imports env vars from /etc/container_environment/
# after each startup script, clearing the process environment.
# Writing secrets here ensures they survive the re-import cycle.
# Only runs in containers with my_init (app, seadoc) — others skip this.
if [ -d /etc/container_environment ]; then
  [ -n "${INIT_SEAFILE_MYSQL_ROOT_PASSWORD:-}" ] && \
    printf '%s' "$INIT_SEAFILE_MYSQL_ROOT_PASSWORD" > /etc/container_environment/INIT_SEAFILE_MYSQL_ROOT_PASSWORD
  [ -n "${SEAFILE_MYSQL_DB_PASSWORD:-}" ] && \
    printf '%s' "$SEAFILE_MYSQL_DB_PASSWORD" > /etc/container_environment/SEAFILE_MYSQL_DB_PASSWORD
  [ -n "${DB_PASSWORD:-}" ] && \
    printf '%s' "$DB_PASSWORD" > /etc/container_environment/DB_PASSWORD
  [ -n "${INIT_SEAFILE_ADMIN_PASSWORD:-}" ] && \
    printf '%s' "$INIT_SEAFILE_ADMIN_PASSWORD" > /etc/container_environment/INIT_SEAFILE_ADMIN_PASSWORD
  [ -n "${SS_FIRST_ADMIN_PASSWORD:-}" ] && \
    printf '%s' "$SS_FIRST_ADMIN_PASSWORD" > /etc/container_environment/SS_FIRST_ADMIN_PASSWORD
  [ -n "${INIT_SS_ADMIN_PASSWORD:-}" ] && \
    printf '%s' "$INIT_SS_ADMIN_PASSWORD" > /etc/container_environment/INIT_SS_ADMIN_PASSWORD
  [ -n "${JWT_PRIVATE_KEY:-}" ] && \
    printf '%s' "$JWT_PRIVATE_KEY" > /etc/container_environment/JWT_PRIVATE_KEY
  [ -n "${SEAFILE_AI_SECRET_KEY:-}" ] && \
    printf '%s' "$SEAFILE_AI_SECRET_KEY" > /etc/container_environment/SEAFILE_AI_SECRET_KEY
  [ -n "${REDIS_PASSWORD:-}" ] && \
    printf '%s' "$REDIS_PASSWORD" > /etc/container_environment/REDIS_PASSWORD
  [ -n "${ONLYOFFICE_JWT_SECRET:-}" ] && \
    printf '%s' "$ONLYOFFICE_JWT_SECRET" > /etc/container_environment/ONLYOFFICE_JWT_SECRET
fi

# --- Append custom seahub settings (once) ---
SEAHUB_CONF="/shared/seafile/conf/seahub_settings.py"
CUSTOM_CONF="/config/seahub_custom.py"
MARKER="# --- Blueprint custom settings ---"

if [ -f "$SEAHUB_CONF" ] && [ -f "$CUSTOM_CONF" ]; then
  if ! grep -q "$MARKER" "$SEAHUB_CONF" 2>/dev/null; then
    printf '\n%s\n' "$MARKER" >> "$SEAHUB_CONF"
    cat "$CUSTOM_CONF" >> "$SEAHUB_CONF"
  fi
fi

exec "$@"
