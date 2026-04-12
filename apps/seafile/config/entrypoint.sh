#!/bin/sh
set -e

# =============================================
# Shared entrypoint for all Seafile services.
# Reads Docker Secrets and exports them as
# plain environment variables, then exec's
# the original service command.
# =============================================

# --- Secrets → env vars ---
[ -f /run/secrets/DB_ROOT_PWD ] && \
  export INIT_SEAFILE_MYSQL_ROOT_PASSWORD="$(cat /run/secrets/DB_ROOT_PWD)"

[ -f /run/secrets/SEAFILE_DB_PWD ] && \
  export SEAFILE_MYSQL_DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)" && \
  export DB_PASSWORD="$(cat /run/secrets/SEAFILE_DB_PWD)"

[ -f /run/secrets/SEAFILE_ADMIN_PWD ] && \
  export INIT_SEAFILE_ADMIN_PASSWORD="$(cat /run/secrets/SEAFILE_ADMIN_PWD)"

[ -f /run/secrets/JWT_KEY ] && \
  export JWT_PRIVATE_KEY="$(cat /run/secrets/JWT_KEY)"

[ -f /run/secrets/REDIS_PWD ] && \
  export REDIS_PASSWORD="$(cat /run/secrets/REDIS_PWD)"

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
