#!/bin/sh
set -e
# =============================================================================
# Secret-injection entrypoint for Keycloak
# =============================================================================
# Keycloak reads every option from KC_* variables and has no working _FILE
# variant: KC_DB_PASSWORD_FILE is accepted into the configuration without a
# warning and never reaches the JDBC driver ("no password was provided"),
# and KC_BOOTSTRAP_ADMIN_PASSWORD_FILE leaves the bootstrap admin unset.
# Verified against 26.7.3 on 2026-09-07. This wrapper exports both from
# /run/secrets/ and hands over to kc.sh. It runs as the image's user (1000).
#
# Wiring in docker-compose.yml:
#   entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
#   command:    ["/opt/keycloak/bin/kc.sh", "start"]
# =============================================================================

read_secret_required() {
  _name="$1"
  _file="$2"
  if [ ! -r "$_file" ] || [ ! -s "$_file" ]; then
    echo "FATAL: required Docker Secret '${_name}' is missing, unreadable, or empty" >&2
    exit 1
  fi
  _val="$(tr -d '\n' < "$_file")"
  if [ -z "$_val" ]; then
    echo "FATAL: required Docker Secret '${_name}' is empty after newline strip" >&2
    exit 1
  fi
  printf '%s' "$_val"
}

_val="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
export KC_DB_PASSWORD="$_val"

# Used only when the master realm is created, on the first start. Afterwards
# the temporary account should be replaced by a permanent administrator.
_val="$(read_secret_required BOOTSTRAP_ADMIN_PWD /run/secrets/BOOTSTRAP_ADMIN_PWD)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$_val"
unset _val

exec "$@"
