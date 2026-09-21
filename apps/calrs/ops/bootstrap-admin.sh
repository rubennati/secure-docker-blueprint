#!/usr/bin/env bash
# Creates the first administrator and closes registration.
#
# Until this has run, whoever reaches the instance first can register and
# becomes the administrator. The shipped access policy keeps the router closed
# to everyone but the VPN for that reason.
#
# The password prompt comes from the application and needs a terminal, so this
# script is interactive by design — it cannot be piped.
set -euo pipefail
cd "$(dirname "$0")/.."

email="${1:-}"
name="${2:-Administrator}"
if [ -z "$email" ]; then
  echo "usage: ops/bootstrap-admin.sh <email> [name]" >&2
  exit 1
fi

if ! docker compose ps --status running --services | grep -qx calrs-app; then
  echo "the calrs-app service is not running — start it with 'docker compose up -d' first" >&2
  exit 1
fi

if docker compose exec -T calrs-app calrs user list 2>/dev/null | grep -q '@'; then
  echo "already bootstrapped — a user exists. Nothing changed."
  docker compose exec -T calrs-app calrs user list
  exit 0
fi

echo "Creating the administrator. The password is asked twice and is not echoed."
docker compose exec calrs-app calrs user create --email "$email" --name "$name" --admin

docker compose exec -T calrs-app calrs config auth --registration false

echo
docker compose exec -T calrs-app calrs user list
docker compose exec -T calrs-app calrs config show | grep -i registration

echo
echo "Done. Registration is closed; further accounts are created with"
echo "'docker compose exec calrs-app calrs user create'."
