#!/bin/sh
set -e

# --- Secrets → env vars ---
# Invoice Ninja (Laravel) does not support _FILE env vars.
[ -f /run/secrets/DB_PWD ]     && export DB_PASSWORD="$(cat /run/secrets/DB_PWD)"
[ -f /run/secrets/IN_USER_PWD ] && export IN_PASSWORD="$(cat /run/secrets/IN_USER_PWD)"

exec "$@"
