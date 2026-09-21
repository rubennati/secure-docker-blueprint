#!/usr/bin/env bash
# Creates the first user and prints the API key it returns.
#
# POST /v1/setup is public and works exactly once — afterwards it answers 409.
# Until it has run, whoever reaches the instance first owns the workspace, which
# is why the shipped access policy is VPN-only.
#
# The API key is shown once, by the application, and is not stored anywhere else.
set -euo pipefail
cd "$(dirname "$0")/.."

email="${1:-}"
name="${2:-Administrator}"
timezone="${3:-UTC}"
if [ -z "$email" ]; then
  echo "usage: ops/setup.sh <email> [name] [timezone]" >&2
  exit 1
fi

if ! docker compose ps --status running --services | grep -qx calnode-app; then
  echo "the calnode-app service is not running — start it with 'docker compose up -d' first" >&2
  exit 1
fi

body=$(printf '{"name":%s,"email":%s,"timezone":%s}' \
  "$(printf '%s' "$name" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "$email" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
  "$(printf '%s' "$timezone" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")

# From inside the container: the port is not published and the route is internal.
out=$(docker compose exec -T calnode-app wget -qO- \
  --header 'Content-Type: application/json' \
  --post-data "$body" \
  http://127.0.0.1:3000/v1/setup 2>/dev/null) || {
    echo "setup failed — it may already have run. Current state:" >&2
    docker compose exec -T calnode-app wget -qSO- --header 'Content-Type: application/json' \
      --post-data "$body" http://127.0.0.1:3000/v1/setup 2>&1 | head -3 >&2
    exit 1
  }

echo "$out"
echo
echo "Store the api_key above: it is shown once and cannot be read back."
