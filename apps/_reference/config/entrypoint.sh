#!/bin/sh
set -e
# =============================================================================
# Secret-injection entrypoint — the canonical pattern
# =============================================================================
# Only needed when an image CANNOT read secrets from files itself. If it
# supports the _FILE convention (postgres, mariadb, paperless — see the `db`
# service), use that instead and delete this file.
#
# Wiring in docker-compose.yml:
#   entrypoint: ["/bin/sh", "/config/entrypoint.sh", "<image's original entrypoint>"]
#   command:    ["<image's original command>"]
# Read both from the image before wiring:
#   docker inspect --format='{{json .Config.Entrypoint}} {{json .Config.Cmd}}' <image>
#
# This script exports secrets, then `exec "$@"` hands control to the original
# entrypoint — the app starts normally and never knows the difference.
# =============================================================================

# read_secret_required NAME FILE — prints the secret (newline stripped), or aborts.
#
# Why a helper instead of `export VAR="$(cat ...)"`: export is a special builtin
# whose own exit status (always 0) is what `set -e` sees, so a missing file would
# NOT abort — the app would start with an empty secret. Assigning to a plain
# variable first lets `set -e` catch the real failure. Fail fast beats a service
# running with a blank password.
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

# --- Required secrets ---
# Build connection URLs here, so the password never appears in `environment:`
# (where `docker inspect` would show it). DB_USER/DB_NAME come from .env — only
# the password is secret.
_db_pwd="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
export DATABASE_URL="postgres://${DB_USER}:${_db_pwd}@db:5432/${DB_NAME}"
unset _db_pwd

_app_key="$(read_secret_required APP_KEY /run/secrets/APP_KEY)"
export APP_KEY="$_app_key"
unset _app_key

# --- Optional secrets ---
# Only inject when the file has content, so an unused feature (mail here) does
# not block startup.
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export SMTP_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
