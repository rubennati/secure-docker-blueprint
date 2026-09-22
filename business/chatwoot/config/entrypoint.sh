#!/bin/sh
set -e

# Replaces upstream's rails entrypoint, which runs `bundle install` on every
# start — a development convenience that writes into the image. What remains of
# it is the wait for the database. The secrets have no _FILE variants and are
# read from the Docker Secrets here.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use intermediate
# variables so set -e aborts if a secret file is missing.
_db="$(cat /run/secrets/DB_PWD)"
_rd="$(cat /run/secrets/REDIS_PWD)"
_sk="$(cat /run/secrets/SECRET_KEY_BASE)"
export POSTGRES_PASSWORD="$_db"
export REDIS_PASSWORD="$_rd"
export SECRET_KEY_BASE="$_sk"
unset _db _rd _sk

until pg_isready -q -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USERNAME"; do
  sleep 2
done

exec "$@"
