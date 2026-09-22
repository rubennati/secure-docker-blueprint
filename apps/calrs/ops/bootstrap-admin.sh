#!/usr/bin/env bash
# Creates the first administrator and closes registration.
#
# Until this has run, whoever reaches the instance first can register and
# becomes the administrator. The shipped access policy keeps the router closed
# to everyone but the VPN for that reason.
#
# The password prompt comes from the application and needs a terminal, so this
# script is interactive by design — it cannot be piped.
#
# Every CLI call goes through the entrypoint. `docker compose exec` bypasses it,
# so a bare `calrs` would start without CALRS_SECRET_KEY — and calrs then
# generates its own secret.key in the data directory and encrypts with that
# instead of the Docker Secret the server uses.
set -euo pipefail
cd "$(dirname "$0")/.."

cli() { docker compose exec -T calrs-app /bin/sh /entrypoint.sh calrs "$@"; }

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

if cli user list 2>/dev/null | grep -q '@'; then
  echo "already bootstrapped — a user exists. Nothing changed."
  cli user list
  exit 0
fi

echo "Creating the administrator. The password is not echoed."
docker compose exec calrs-app /bin/sh /entrypoint.sh calrs user create --email "$email" --name "$name" --admin

cli config auth --registration false

echo
cli user list
cli config show | grep -i registration

echo
echo "Done. Registration is closed; further accounts are created with"
echo "'docker compose exec calrs-app /bin/sh /entrypoint.sh calrs user create'."
