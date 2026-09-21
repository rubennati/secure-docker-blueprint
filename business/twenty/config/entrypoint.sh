#!/bin/sh
set -e

# Twenty reads its database and Redis connections as URLs and its encryption key
# as a plain variable; none has a _FILE variant. Build both from the Docker
# Secrets here, then hand off to the image's own entrypoint.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use intermediate
# variables so set -e aborts if a secret file is missing.
_db="$(cat /run/secrets/DB_PWD)"
_ek="$(cat /run/secrets/ENCRYPTION_KEY)"
_rd="$(cat /run/secrets/REDIS_PWD)"
export PG_DATABASE_URL="postgres://${DB_USER}:${_db}@db:5432/${DB_NAME}"
export ENCRYPTION_KEY="$_ek"
export REDIS_URL="redis://:${_rd}@redis:6379"
unset _db _ek _rd

exec "$@"
