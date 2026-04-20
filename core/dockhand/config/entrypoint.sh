#!/bin/sh
# =========================================================
# Build DATABASE_URL from env vars + secret at runtime.
# Dockhand does not support _FILE env vars natively.
# =========================================================
set -e

DB_PWD="$(cat /run/secrets/DB_PWD)"
export DATABASE_URL="postgres://${DB_USER}:${DB_PWD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
export ENCRYPTION_KEY="$(cat /run/secrets/ENCRYPTION_KEY)"

exec "$@"
