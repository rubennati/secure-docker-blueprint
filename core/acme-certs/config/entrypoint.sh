#!/bin/sh
# =========================================================
# Load CF_Token from Docker Secret at runtime.
# acme.sh does not support _FILE env vars natively.
# =========================================================
set -e

if [ -f /run/secrets/CF_TOKEN ]; then
  export CF_Token="$(cat /run/secrets/CF_TOKEN)"
fi

exec "$@"
