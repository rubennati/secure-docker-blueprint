#!/bin/sh
# Ghost ActivityPub does not support _FILE env vars — read Docker Secret manually.
set -e

if [ -f /run/secrets/DB_PWD ]; then
  export MYSQL_PASSWORD
  MYSQL_PASSWORD="$(cat /run/secrets/DB_PWD)"
fi

exec docker-entrypoint.sh node dist/app.js
