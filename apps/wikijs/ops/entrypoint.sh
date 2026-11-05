#!/bin/sh
# Wiki.js 3 creates its root administrator at the first start from ADMIN_EMAIL
# and ADMIN_PASS and has no _FILE variant for the password. Read the Docker
# Secret here and export it, then start the image's own command. Without the
# secret Wiki.js would fall back to a published default password, so a missing
# or empty file stops the container instead.
set -e

if [ ! -s /run/secrets/ADMIN_PWD ]; then
  echo "entrypoint: /run/secrets/ADMIN_PWD is missing or empty" >&2
  exit 1
fi
export ADMIN_PASS
ADMIN_PASS="$(cat /run/secrets/ADMIN_PWD)"

exec tini -s -- node --no-experimental-webstorage backend
