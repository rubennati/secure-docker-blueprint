#!/bin/sh
set -e

# Documenso reads NEXT_PRIVATE_* from env (no _FILE). Read Docker Secret files,
# export them, then hand off to the image's CMD (sh start.sh — runs migrations).

# read_secret_required NAME FILE — prints the (newline-stripped) secret, or aborts.
# Assign to a plain variable first so `set -e` sees a missing/unreadable secret.
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

# DB password is hex (URL-safe) — no percent-encoding needed for the postgres URL.
_db_pwd="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
export NEXT_PRIVATE_DATABASE_URL="postgresql://${DB_USER}:${_db_pwd}@db:5432/${DB_NAME}"
export NEXT_PRIVATE_DIRECT_DATABASE_URL="$NEXT_PRIVATE_DATABASE_URL"
unset _db_pwd

_ns="$(read_secret_required NEXTAUTH_SECRET /run/secrets/NEXTAUTH_SECRET)"
export NEXTAUTH_SECRET="$_ns"; unset _ns

_ek="$(read_secret_required ENCRYPTION_KEY /run/secrets/ENCRYPTION_KEY)"
export NEXT_PRIVATE_ENCRYPTION_KEY="$_ek"; unset _ek

_ek2="$(read_secret_required ENCRYPTION_SECONDARY_KEY /run/secrets/ENCRYPTION_SECONDARY_KEY)"
export NEXT_PRIVATE_ENCRYPTION_SECONDARY_KEY="$_ek2"; unset _ek2

_sp="$(read_secret_required SIGNING_PASSPHRASE /run/secrets/SIGNING_PASSPHRASE)"
export NEXT_PRIVATE_SIGNING_PASSPHRASE="$_sp"; unset _sp

# SMTP password optional
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export NEXT_PRIVATE_SMTP_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
