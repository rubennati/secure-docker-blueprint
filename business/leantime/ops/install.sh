#!/usr/bin/env bash
# Creates the database schema and the first administrator from the command
# line, so the web installer is never the thing that does it.
#
# Run this with the database up and the application still down:
#   docker compose up -d leantime-db
#   ops/install.sh
#   docker compose up -d
#
# Two details make this longer than a plain `docker compose exec`:
#
#   * /start.sh ignores its arguments — it always execs supervisord — so the
#     LEAN_*_FILE variables have to be resolved here instead. Same trap as
#     apps/calrs and backup/kopia, in a different shape.
#   * `traefik.enable=false` keeps this one-off container from registering a
#     second router for the same host name while it runs.
#
# The command is `db:migrate`, not the `db:install` the source declares as an
# alias: Laravel registers it under its name only, and `db:install` is answered
# with "Command not defined". It creates the schema and the administrator on an
# empty database and applies pending migrations on a populated one.
#
# It prompts for the administrator's email, password, name and company. Nothing
# is passed as an argument, so the password stays out of the process list and
# out of your shell history.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose run --rm --no-deps \
    --label traefik.enable=false \
    --entrypoint /bin/sh \
    leantime-app -c '
        [ -n "${LEAN_DB_PASSWORD_FILE:-}" ] && \
            LEAN_DB_PASSWORD="$(cat "$LEAN_DB_PASSWORD_FILE")" && \
            export LEAN_DB_PASSWORD
        [ -n "${LEAN_SESSION_PASSWORD_FILE:-}" ] && \
            LEAN_SESSION_PASSWORD="$(cat "$LEAN_SESSION_PASSWORD_FILE")" && \
            export LEAN_SESSION_PASSWORD
        exec php bin/leantime db:migrate
    '

echo
echo "Schema created. Start the application:"
echo "  docker compose up -d"
