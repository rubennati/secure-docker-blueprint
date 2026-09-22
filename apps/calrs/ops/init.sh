#!/usr/bin/env bash
# Generates the credential-encryption key. Refuses to overwrite an existing one.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e .secrets/calrs_secret_key.txt ]; then
  echo "refusing: .secrets/calrs_secret_key.txt exists" >&2
  exit 1
fi

umask 077
mkdir -p .secrets
# calrs expects base64 of exactly 32 bytes; it refuses to start on anything else.
printf '%s' "$(openssl rand -base64 32)" > .secrets/calrs_secret_key.txt
# The container runs as uid 999 and reads this through a bind mount.
chmod 644 .secrets/calrs_secret_key.txt
chmod 700 .secrets

echo "Created .secrets/calrs_secret_key.txt"
echo "Back it up: without it, stored CalDAV and SMTP passwords cannot be decrypted."
echo
echo "Next:"
echo "  mkdir -p volumes/data && sudo chown 999:999 volumes/data"
echo "  docker compose up -d"
echo "  ops/bootstrap-admin.sh you@example.com 'Your Name'"
