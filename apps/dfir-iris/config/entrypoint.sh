#!/bin/bash
set -e

# IRIS has no _FILE support for any of these (verified: no such pattern in
# upstream's .env.model, docker-compose.base.yml, or entrypoint script) —
# both app and worker read them as plain env vars. This wrapper injects
# them from Docker Secrets, then hands off to the image's own entrypoint,
# which itself takes the same "app" vs "iris-worker" argument this stack's
# compose command already passes.
_pwd="$(cat /run/secrets/postgres_password)"
export POSTGRES_PASSWORD="$_pwd"
unset _pwd

_pwd="$(cat /run/secrets/postgres_admin_password)"
export POSTGRES_ADMIN_PASSWORD="$_pwd"
unset _pwd

_key="$(cat /run/secrets/iris_secret_key)"
export IRIS_SECRET_KEY="$_key"
unset _key

_salt="$(cat /run/secrets/iris_security_password_salt)"
export IRIS_SECURITY_PASSWORD_SALT="$_salt"
unset _salt

exec "$@"
