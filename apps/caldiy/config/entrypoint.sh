#!/bin/sh
set -e

# Cal.diy has no native _FILE support for any of its secrets.
# Read Docker Secret files and export as environment variables
# before handing off to the original start.sh.

# Strip trailing newline, then percent-encode chars unsafe in a postgresql:// URL.
# base64 passwords can contain + / = — all break URL host-field parsing in node-postgres.
_raw_pwd="$(tr -d '\n' < /run/secrets/DB_PWD)"
_enc_pwd="$(printf '%s' "${_raw_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"

export DATABASE_URL="postgresql://${DB_USER}:${_enc_pwd}@db:5432/${DB_NAME}"
export DATABASE_DIRECT_URL="${DATABASE_URL}"
export NEXTAUTH_SECRET="$(tr -d '\n' < /run/secrets/NEXTAUTH_SECRET)"
export CALENDSO_ENCRYPTION_KEY="$(tr -d '\n' < /run/secrets/ENCRYPTION_KEY)"
export CRON_API_KEY="$(tr -d '\n' < /run/secrets/CRON_API_KEY)"

# SMTP password is optional — only inject if the file is non-empty
if [ -s /run/secrets/SMTP_PASSWORD ]; then
  export EMAIL_SERVER_PASSWORD="$(tr -d '\n' < /run/secrets/SMTP_PASSWORD)"
fi

exec "$@"
