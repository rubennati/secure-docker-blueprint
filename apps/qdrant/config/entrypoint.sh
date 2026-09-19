#!/bin/sh
set -e

# Qdrant reads its API key from an environment variable, not a file — there is
# no _FILE variant. Read the secret here and export it before handing off to
# the image's own entrypoint.
_key="$(cat /run/secrets/QDRANT_API_KEY)"
export QDRANT__SERVICE__API_KEY="$_key"
unset _key

exec "$@"
