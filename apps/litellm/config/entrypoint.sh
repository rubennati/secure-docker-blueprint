#!/bin/sh
set -e

# LiteLLM reads its master key, salt key and database URL from the environment
# and has no _FILE variant for any of them. Build them from the Docker Secrets
# here and hand off to the image's own entrypoint.
# Intermediate variables so set -e aborts if a secret file is missing.
_db="$(cat /run/secrets/DB_PWD)"
_mk="$(cat /run/secrets/LITELLM_MASTER_KEY)"
_sk="$(cat /run/secrets/LITELLM_SALT_KEY)"
export DATABASE_URL="postgresql://${DB_USER}:${_db}@db:5432/${DB_NAME}"
export LITELLM_MASTER_KEY="$_mk"
export LITELLM_SALT_KEY="$_sk"
unset _db _mk _sk

exec "$@"
