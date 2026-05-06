#!/bin/sh
set -e

# Inject secrets into environment before starting OpenProject.
# DATABASE_URL and SECRET_KEY_BASE embed credentials and cannot use _FILE variants.
#
# The DB password is URL-encoded before embedding in DATABASE_URL.
# Base64 passwords contain +, /, and = which are URL-special characters
# and break the postgres:// URL parser if left unencoded.
export SECRET_KEY_BASE="$(cat /run/secrets/OP_SECRET_KEY_BASE)"

_pwd="$(cat /run/secrets/OP_DB_PWD)"
_enc="$(printf '%s' "${_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
export DATABASE_URL="postgres://${OP_DB_USER:-openproject}:${_enc}@db/${OP_DB_NAME:-openproject}?pool=20&encoding=unicode&reconnect=true"
unset _pwd _enc

exec "$@"
