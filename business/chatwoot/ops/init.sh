#!/usr/bin/env bash
# Generates the three secrets and prepares the data directories. Refuses to
# overwrite existing secrets.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd redis_pwd secret_key_base; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 24)" > .secrets/db_pwd.txt
printf '%s' "$(openssl rand -hex 24)" > .secrets/redis_pwd.txt
# Rails signs sessions and derives its encryption keys from this.
printf '%s' "$(openssl rand -hex 64)" > .secrets/secret_key_base.txt
# Four containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/storage volumes/postgres volumes/redis

echo "Created .secrets/{db_pwd,redis_pwd,secret_key_base}.txt"
echo
echo "Next:"
echo "  sudo chown 1000:1000 volumes/storage"
echo "  sudo chown 999:999 volumes/redis"
echo "  docker compose up -d"
echo "  then open the site over the VPN — the first visit creates the administrator"
