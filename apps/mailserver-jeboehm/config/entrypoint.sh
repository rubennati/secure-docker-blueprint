#!/bin/sh
# Exports the credentials from /run/secrets and hands over to the image's own
# entrypoint. A service gets only the secrets its compose block mounts.
set -e

load() {
  [ -f "/run/secrets/$2" ] || return 0
  _v="$(cat "/run/secrets/$2")"
  export "$1=$_v"
  unset _v
}

load DB_PASSWORD DB_PWD
load REDIS_PASSWORD REDIS_PWD
load CONTROLLER_PASSWORD CONTROLLER_PWD
load DOVEADM_API_KEY DOVEADM_API_KEY

exec /entrypoint.sh "$@"
