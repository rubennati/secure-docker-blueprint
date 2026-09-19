#!/bin/sh
set -e

# docling-serve reads its API key from an environment variable, not a file —
# no native _FILE support. Read the secret here and export it before handing
# off to the image's own entrypoint.
_key="$(cat /run/secrets/DOCLING_API_KEY)"
export DOCLING_SERVE_API_KEY="$_key"
unset _key

exec "$@"
