#!/bin/sh
set -e

# Windmill reads its entire connection as one DATABASE_URL string — no native
# _FILE support for a discrete password field. Read the secret here and build
# the URL before handing off to the image's own command.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use an
# intermediate variable so set -e correctly aborts if the secret file is
# missing.
_pwd="$(cat /run/secrets/DB_PWD)"
export DATABASE_URL="postgres://${DB_USER}:${_pwd}@db/${DB_NAME}?sslmode=disable"
unset _pwd

exec "$@"
