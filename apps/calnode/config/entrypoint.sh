#!/bin/sh
set -e

# Calnode reads its key-encryption input from CALNODE_ENCRYPTION_KEY and has no
# _FILE variant. Read the Docker Secrets here, then hand off to the image's own
# entrypoint.
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status — use an
# intermediate variable so set -e aborts if the secret file is missing.
_key="$(cat /run/secrets/CALNODE_ENCRYPTION_KEY)"
export CALNODE_ENCRYPTION_KEY="$_key"
if [ -f /run/secrets/CALNODE_RECOVERY_SECRET ]; then
  _rec="$(cat /run/secrets/CALNODE_RECOVERY_SECRET)"
  export CALNODE_RECOVERY_SECRET="$_rec"
fi
unset _key _rec

exec "$@"
