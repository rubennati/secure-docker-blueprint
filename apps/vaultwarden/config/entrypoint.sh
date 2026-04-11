#!/bin/sh
# Build DATABASE_URL from env vars + secret file at runtime.
# This avoids putting the DB password in .env or docker-compose.yml.

DB_PWD="$(cat /run/secrets/DB_PWD)"
export DATABASE_URL="mysql://${DB_USER}:${DB_PWD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

exec /start.sh "$@"
