#!/bin/sh
set -e

# =============================================
# Entrypoint wrapper for Seafile services.
# Currently only handles seahub_custom.py injection.
#
# TODO: Add Docker Secrets support when my_init
# env var persistence is resolved.
# =============================================

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
