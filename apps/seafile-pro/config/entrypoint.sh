#!/bin/sh
set -e

# =============================================
# Entrypoint wrapper for Seafile Pro app container.
#
# Handles three post-install config injections:
# 1. seahub_settings.py — OnlyOffice + Metadata + Thumbnail
# 2. seafevents.conf    — SeaSearch config (replaces Elasticsearch)
# 3. seafile.conf       — ClamAV virus scanning
#
# Each injection only runs once (marker-based).
# Configs don't exist on first boot — the wrapper
# catches them on the second start (after restart).
# =============================================

SEAFILE_CONF_DIR="/shared/seafile/conf"

# --- 1. Append custom seahub settings (once) ---
SEAHUB_CONF="$SEAFILE_CONF_DIR/seahub_settings.py"
CUSTOM_CONF="/config/seahub_custom.py"
MARKER_SEAHUB="# --- Blueprint custom settings ---"

if [ -f "$SEAHUB_CONF" ] && [ -f "$CUSTOM_CONF" ]; then
  if ! grep -q "$MARKER_SEAHUB" "$SEAHUB_CONF" 2>/dev/null; then
    printf '\n%s\n' "$MARKER_SEAHUB" >> "$SEAHUB_CONF"
    cat "$CUSTOM_CONF" >> "$SEAHUB_CONF"
  fi
fi

# --- 2. Configure SeaSearch in seafevents.conf (once) ---
SEAFEVENTS_CONF="$SEAFILE_CONF_DIR/seafevents.conf"
MARKER_SEASEARCH="# --- Blueprint SeaSearch ---"

if [ -f "$SEAFEVENTS_CONF" ]; then
  if ! grep -q "$MARKER_SEASEARCH" "$SEAFEVENTS_CONF" 2>/dev/null; then
    # Generate base64 auth token from admin credentials
    SS_TOKEN=""
    if [ -n "${INIT_SEAFILE_ADMIN_EMAIL:-}" ] && [ -n "${INIT_SEAFILE_ADMIN_PASSWORD:-}" ]; then
      SS_TOKEN=$(printf '%s:%s' "$INIT_SEAFILE_ADMIN_EMAIL" "$INIT_SEAFILE_ADMIN_PASSWORD" | base64 | tr -d '\n')
    fi

    if [ -n "$SS_TOKEN" ]; then
      # Disable old Elasticsearch config
      sed -i '/^\[INDEX FILES\]/,/^$/{s/^enabled = true/enabled = false/}' "$SEAFEVENTS_CONF"

      # Add SeaSearch config
      printf '\n%s\n' "$MARKER_SEASEARCH" >> "$SEAFEVENTS_CONF"
      cat >> "$SEAFEVENTS_CONF" << EOF
[SEASEARCH]
enabled = true
seasearch_url = http://seasearch:4080
seasearch_token = ${SS_TOKEN}
interval = 10m
index_office_pdf = true
EOF
    fi
  fi
fi

# --- 3. Configure ClamAV in seafile.conf (once) ---
SEAFILE_CONF="$SEAFILE_CONF_DIR/seafile.conf"
MARKER_CLAMAV="# --- Blueprint ClamAV ---"

if [ -f "$SEAFILE_CONF" ]; then
  if ! grep -q "$MARKER_CLAMAV" "$SEAFILE_CONF" 2>/dev/null; then
    printf '\n%s\n' "$MARKER_CLAMAV" >> "$SEAFILE_CONF"
    cat >> "$SEAFILE_CONF" << 'EOF'
[virus_scan]
scan_command = clamdscan
virus_code = 1
nonvirus_code = 0
scan_interval = 5
scan_size_limit = 20
threads = 2
EOF
  fi
fi

exec "$@"
