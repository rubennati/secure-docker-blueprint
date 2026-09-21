#!/usr/bin/env bash
# Generates the three secrets and prepares the data directories. Refuses to
# overwrite existing secrets.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd redis_pwd encryption_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
# Hex for the passwords: both are embedded in connection URLs.
printf '%s' "$(openssl rand -hex 24)" > .secrets/db_pwd.txt
printf '%s' "$(openssl rand -hex 24)" > .secrets/redis_pwd.txt
# Upstream: `openssl rand -base64 32`.
printf '%s' "$(openssl rand -base64 32)" > .secrets/encryption_key.txt
# Four containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/storage volumes/postgres volumes/redis

echo "Created .secrets/{db_pwd,redis_pwd,encryption_key}.txt"
echo "Back up encryption_key.txt: stored connection credentials are unreadable without it."
echo
echo "Next:"
echo "  sudo chown 1000:1000 volumes/storage"
echo "  sudo chown 999:999 volumes/redis"
echo "  docker compose up -d"
