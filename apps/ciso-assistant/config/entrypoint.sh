#!/bin/sh
set -e

# CISO Assistant reads its database password, Django secret key and the first
# administrator's password from plain environment variables. Read them from the
# Docker Secrets here, then hand off to the image's own start command.
# Without DJANGO_SECRET_KEY the image would generate one and store it in the
# data directory, next to the data it protects.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use intermediate
# variables so set -e aborts if a secret file is missing.
_db="$(cat /run/secrets/DB_PWD)"
_sk="$(cat /run/secrets/DJANGO_SECRET_KEY)"
export POSTGRES_PASSWORD="$_db"
export DJANGO_SECRET_KEY="$_sk"
if [ -f /run/secrets/ADMIN_PWD ]; then
  _ap="$(cat /run/secrets/ADMIN_PWD)"
  export DJANGO_SUPERUSER_PASSWORD="$_ap"
fi
unset _db _sk _ap

exec "$@"
