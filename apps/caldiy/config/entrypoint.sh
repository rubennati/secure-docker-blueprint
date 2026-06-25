#!/bin/sh
set -e

# Cal.diy has no native _FILE support for any of its secrets.
# Read Docker Secret files and export as environment variables
# before handing off to the original start.sh.

# read_secret_required NAME FILE — prints the (newline-stripped) secret on stdout,
# or aborts the container. Required because `export VAR="$(...)"` masks the exit
# status of the command substitution: export is a special builtin whose own status
# (always 0) is what `set -e` sees, so a missing/unreadable secret file would NOT
# abort and the app could start with an empty secret. Assigning the result of this
# helper to a plain variable first lets `set -e` see the real failure and exit.
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

# Read + validate DB_PWD (fail fast on missing/unreadable/empty), then percent-encode
# chars unsafe in a postgresql:// URL. base64 passwords can contain + / = — all break
# URL host-field parsing in node-postgres. read_secret_required strips the newline.
_raw_pwd="$(read_secret_required DB_PWD /run/secrets/DB_PWD)"
_enc_pwd="$(printf '%s' "${_raw_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
unset _raw_pwd

export DATABASE_URL="postgresql://${DB_USER}:${_enc_pwd}@db:5432/${DB_NAME}"
export DATABASE_DIRECT_URL="${DATABASE_URL}"
unset _enc_pwd
# Required secrets — fail fast (via read_secret_required) if any is missing,
# unreadable, or empty, rather than starting Cal.diy with a broken secret.
_nextauth_secret="$(read_secret_required NEXTAUTH_SECRET /run/secrets/NEXTAUTH_SECRET)"
export NEXTAUTH_SECRET="$_nextauth_secret"
unset _nextauth_secret

_encryption_key="$(read_secret_required ENCRYPTION_KEY /run/secrets/ENCRYPTION_KEY)"
export CALENDSO_ENCRYPTION_KEY="$_encryption_key"
unset _encryption_key

_cron_api_key="$(read_secret_required CRON_API_KEY /run/secrets/CRON_API_KEY)"
export CRON_API_KEY="$_cron_api_key"
unset _cron_api_key

_vapid_private_key="$(read_secret_required VAPID_PRIVATE_KEY /run/secrets/VAPID_PRIVATE_KEY)"
export VAPID_PRIVATE_KEY="$_vapid_private_key"
unset _vapid_private_key

# SMTP password is optional — only inject if the file is non-empty
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export EMAIL_SERVER_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
