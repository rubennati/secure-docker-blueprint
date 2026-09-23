#!/usr/bin/env bash
# Prepares the data directory. headscale generates its own keys on first start.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p volumes/lib

echo "Created volumes/lib"
echo
echo "headscale has no password of its own: the node key and, if you enable the"
echo "embedded relay, the DERP key are generated into volumes/lib on the first"
echo "start. Clients authenticate with pre-auth keys you create."
echo
echo "Back up volumes/lib/noise_private.key off this host — it is the tailnet's"
echo "identity, and without it every node has to be registered again."
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/lib   # the uid headscale runs as"
echo "  docker compose up -d"
echo "  docker compose exec headscale /ko-app/headscale users create ops"
echo "  docker compose exec headscale /ko-app/headscale users list          # note the ID"
echo "  docker compose exec headscale /ko-app/headscale preauthkeys create --user 1 --expiration 1h"
echo
echo "--user takes the numeric ID, not the name: v0.29.4 rejects a name with"
echo "'strconv.ParseUint: parsing \"ops\": invalid syntax'."
