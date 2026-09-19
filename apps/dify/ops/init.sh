#!/usr/bin/env bash
# Generates every secret Dify needs. Refuses to overwrite existing files.
set -euo pipefail
cd "$(dirname "$0")/.."

files=(secret_key init_password db_password redis_password celery_broker_url
       pgvector_password sandbox_api_key plugin_daemon_key plugin_inner_api_key)
for f in "${files[@]}"; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
w() { printf '%s' "$2" > ".secrets/$1.txt"; }
# Hex only where the value is embedded in a URL.
w secret_key "$(openssl rand -base64 42 | tr -d '\n')"
w init_password "$(openssl rand -hex 12)"
w db_password "$(openssl rand -hex 24)"
w redis_password "$(openssl rand -hex 24)"
w celery_broker_url "redis://:$(cat .secrets/redis_password.txt)@redis:6379/1"
w pgvector_password "$(openssl rand -hex 24)"
w sandbox_api_key "$(openssl rand -base64 42 | tr -d '\n')"
w plugin_daemon_key "$(openssl rand -base64 42 | tr -d '\n')"
w plugin_inner_api_key "$(openssl rand -base64 42 | tr -d '\n')"
# Several containers with different uids read these through bind mounts, so the
# files are world-readable; the directory is what keeps other host users out.
chmod 644 .secrets/*.txt
chmod 700 .secrets

echo "Setup password (asked once, on the first visit to /install): $(cat .secrets/init_password.txt)"
echo
echo "Data directories:"
echo "  mkdir -p volumes/{storage,plugin_daemon,db,pgvector,redis}"
echo "  sudo chown 1001:1001 volumes/storage volumes/plugin_daemon"
echo "  sudo chown 999:999 volumes/redis"
echo "Then: docker compose up -d"
