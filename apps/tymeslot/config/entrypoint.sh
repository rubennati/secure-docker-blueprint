#!/bin/sh
set -e
# =============================================================================
# Secret-injection entrypoint for Tymeslot
# =============================================================================
# Tymeslot reads every secret from the environment and has no _FILE variant
# for any of them (config/runtime.exs, start-docker.sh). This wrapper exports
# them from /run/secrets/ and then hands over to the image's own start script,
# which validates SECRET_KEY_BASE, waits for the database, runs the migrations
# and starts the server as the unprivileged `app` user with `su -p` — the
# environment exported here survives that switch.
#
# Wiring in docker-compose.yml:
#   entrypoint: ["/bin/sh", "/config/entrypoint.sh"]
#   command:    ["/app/start-docker.sh"]
# =============================================================================

# read_secret_required NAME FILE — prints the secret (newline stripped), or aborts.
# `export VAR="$(cat ...)"` would hide a missing file: export always exits 0, so
# `set -e` never fires and the app would start with an empty secret.
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
# Session and cookie signing key; the app refuses to boot without it.
_val="$(read_secret_required SECRET_KEY_BASE /run/secrets/SECRET_KEY_BASE)"
export SECRET_KEY_BASE="$_val"

# Data-at-rest key for stored calendar credentials. Optional upstream, required
# here: without it the key derives from SECRET_KEY_BASE, and rotating that
# would make every stored credential undecryptable.
_val="$(read_secret_required DATA_ENCRYPTION_KEY /run/secrets/DATA_ENCRYPTION_KEY)"
export DATA_ENCRYPTION_KEY="$_val"

# Database password as the discrete variable; host, port, name and user come
# from `environment:`. The start script forwards all of them to the release.
_val="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
export POSTGRES_PASSWORD="$_val"
unset _val

# --- Optional secrets ---
# Only injected when the file has content. With EMAIL_ADAPTER=smtp the app
# requires a non-empty password and fails to boot otherwise.
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export SMTP_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
