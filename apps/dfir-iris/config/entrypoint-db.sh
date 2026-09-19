#!/bin/bash
set -e

# The base postgres image supports POSTGRES_PASSWORD_FILE natively, but
# IRIS's own layered init script (10-create_user.sh) reads
# POSTGRES_ADMIN_PASSWORD as a plain env var with no _FILE equivalent —
# verified by reading that script directly. This wrapper injects both from
# Docker Secrets the same way, then hands off to the image's own entrypoint.
_pwd="$(cat /run/secrets/postgres_password)"
export POSTGRES_PASSWORD="$_pwd"
unset _pwd

_pwd="$(cat /run/secrets/postgres_admin_password)"
export POSTGRES_ADMIN_PASSWORD="$_pwd"
unset _pwd

exec docker-entrypoint.sh "$@"
