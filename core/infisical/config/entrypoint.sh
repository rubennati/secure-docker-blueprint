#!/bin/sh
set -e

# Infisical has no _FILE support for its secrets. Read Docker Secret files and
# export them as env vars, then hand off to the image's standalone-entrypoint.sh.

# read_secret_required NAME FILE — prints the (newline-stripped) secret on stdout,
# or aborts. Assign to a plain variable first so `set -e` sees a missing/unreadable
# secret (export is a special builtin whose own status, always 0, would mask it).
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

# DB password is hex (URL-safe) — no percent-encoding needed for the postgres URI.
_db_pwd="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
export DB_CONNECTION_URI="postgres://${DB_USER}:${_db_pwd}@db:5432/${DB_NAME}"
unset _db_pwd

_enc="$(read_secret_required ENCRYPTION_KEY /run/secrets/ENCRYPTION_KEY)"
export ENCRYPTION_KEY="$_enc"
unset _enc

_auth="$(read_secret_required AUTH_SECRET /run/secrets/AUTH_SECRET)"
export AUTH_SECRET="$_auth"
unset _auth

# SMTP password is optional — only inject if the file is non-empty.
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export SMTP_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
