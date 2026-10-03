#!/usr/bin/env bash
# Creates the data directories.
#   ops/init.sh           for docker-compose.yml
#   ops/init.sh --local   for docker-compose.local.yml
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--local" ]; then BASE=volumes/local; else BASE=volumes; fi

mkdir -p "$BASE/etc" "$BASE/data" .secrets
chmod 700 .secrets

echo "Created $BASE/etc, $BASE/data and .secrets"
echo
echo "Next:"
echo "  sudo chown -R 2000:2000 $BASE/etc $BASE/data   # the uid Stalwart runs as"
echo "  ops/setup.sh${1:+ $1}"
