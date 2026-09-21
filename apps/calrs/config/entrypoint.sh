#!/bin/sh
set -e

# calrs reads its credential-encryption key from CALRS_SECRET_KEY and has no
# _FILE variant. Read the Docker Secret here, then hand off to the image's own
# command.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use an
# intermediate variable so set -e aborts if the secret file is missing.
_key="$(cat /run/secrets/CALRS_SECRET_KEY)"
export CALRS_SECRET_KEY="$_key"
unset _key

exec "$@"
