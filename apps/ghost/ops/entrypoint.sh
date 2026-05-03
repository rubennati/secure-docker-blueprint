#!/bin/sh
# Ghost does not support _FILE env vars — read Docker Secrets manually
# and export them as the plain env vars Ghost expects.
set -e

if [ -f /run/secrets/DB_PWD ]; then
  export database__connection__password
  database__connection__password="$(cat /run/secrets/DB_PWD)"
fi

if [ -f /run/secrets/GHOST_MAIL_PWD ]; then
  export mail__options__auth__pass
  mail__options__auth__pass="$(cat /run/secrets/GHOST_MAIL_PWD)"
fi

exec docker-entrypoint.sh node current/index.js
