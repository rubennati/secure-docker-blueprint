#!/usr/bin/env bash
# Generates the encryption key and the recovery secret. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in calnode_encryption_key calnode_recovery_secret; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 32)" > .secrets/calnode_encryption_key.txt
printf '%s' "$(openssl rand -hex 32)" > .secrets/calnode_recovery_secret.txt
# The container runs as uid 1000 and reads these through a bind mount.
chmod 644 .secrets/*.txt
chmod 700 .secrets

echo "Created .secrets/calnode_encryption_key.txt and .secrets/calnode_recovery_secret.txt"
echo "Back both up, off this host. Losing the encryption key makes every stored"
echo "calendar and provider credential unreadable."
echo
echo "Next:"
echo "  mkdir -p volumes/data && sudo chown 1000:1000 volumes/data"
echo "  docker compose up -d"
echo "  ops/setup.sh you@example.com 'Your Name'   # creates the first user"
