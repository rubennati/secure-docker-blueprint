#!/bin/sh
set -e

# Inject secrets into environment before starting OpenProject.
# DATABASE_URL and SECRET_KEY_BASE embed credentials and cannot use _FILE variants.
#
# The DB password is URL-encoded before embedding in DATABASE_URL.
# Base64 passwords contain +, /, and = which are URL-special characters
# and break the postgres:// URL parser if left unencoded.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status (export is a
# special builtin). Use intermediate variables so `set -e` correctly aborts
# the container if a secret file is missing or unreadable.
_key="$(cat /run/secrets/secret_key_base)"
export SECRET_KEY_BASE="$_key"
unset _key

_pwd="$(cat /run/secrets/db_pwd)"
_enc="$(printf '%s' "${_pwd}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
export DATABASE_URL="postgres://${OP_DB_USER:-openproject}:${_enc}@db/${OP_DB_NAME:-openproject}?pool=20&encoding=unicode&reconnect=true"
unset _pwd _enc

exec "$@"
