#!/bin/sh
# The web image's own entrypoint, with the credentials and APP_SECRET read from
# /run/secrets.
set -e

load() {
  _v="$(cat "/run/secrets/$2")"
  export "$1=$_v"
  unset _v
}

load DB_PASSWORD DB_PWD
load REDIS_PASSWORD REDIS_PWD
load CONTROLLER_PASSWORD CONTROLLER_PWD
load DOVEADM_API_KEY DOVEADM_API_KEY
load APP_SECRET APP_SECRET

[ "$#" -gt 0 ] && exec "$@"

if [ "${SKIP_INIT}" != "true" ]; then
  /usr/local/lib/init.sh
fi

exec frankenphp run --config /etc/frankenphp/Caddyfile --adapter caddyfile
