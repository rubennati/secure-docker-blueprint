#!/bin/sh
set -e

# Inject secrets into environment before starting OpenProject.
# DATABASE_URL and SECRET_KEY_BASE embed credentials and cannot use _FILE variants.
export SECRET_KEY_BASE="$(cat /run/secrets/OP_SECRET_KEY_BASE)"
export DATABASE_URL="postgres://${OP_DB_USER:-openproject}:$(cat /run/secrets/OP_DB_PWD)@db/${OP_DB_NAME:-openproject}?pool=20&encoding=unicode&reconnect=true"

exec "$@"
