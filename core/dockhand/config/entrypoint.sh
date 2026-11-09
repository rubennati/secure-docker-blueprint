#!/bin/sh
# =========================================================
# Build DATABASE_URL from env vars + secret at runtime.
# Dockhand does not support _FILE env vars natively.
# =========================================================
set -e

DB_PWD="$(cat /run/secrets/DB_PWD)"
# The README generates the password with base64, whose / + = are not valid in
# the userinfo of a URL; Dockhand refuses such a DATABASE_URL ("Invalid URL
# format"). Percent-encode them, % first.
DB_PWD_ENC="$(printf '%s' "${DB_PWD}" | sed 's/%/%25/g; s/+/%2B/g; s|/|%2F|g; s/=/%3D/g')"
export DATABASE_URL="postgres://${DB_USER}:${DB_PWD_ENC}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
unset DB_PWD DB_PWD_ENC
export ENCRYPTION_KEY="$(cat /run/secrets/ENCRYPTION_KEY)"

exec "$@"
