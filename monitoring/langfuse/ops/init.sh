#!/usr/bin/env bash
# Generates every secret Langfuse needs and prepares the data directories.
# Usage: ops/init.sh [admin-email]   (default admin@example.com)
# Refuses to overwrite existing files.
set -euo pipefail
cd "$(dirname "$0")/.."

email="${1:-admin@example.com}"
files=(pg_password ch_password redis_auth minio_password salt encryption_key
       nextauth_secret admin_password project_secret_key project_public_key)
for f in "${files[@]}"; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
# Hex only: the database password is embedded in a URL.
for f in pg_password ch_password redis_auth minio_password salt nextauth_secret; do
  printf '%s' "$(openssl rand -hex 24)" > ".secrets/$f.txt"
done
printf '%s' "$(openssl rand -hex 32)" > .secrets/encryption_key.txt
printf '%s' "$(openssl rand -hex 16)" > .secrets/admin_password.txt
printf 'pk-lf-%s' "$(openssl rand -hex 12)" > .secrets/project_public_key.txt
printf 'sk-lf-%s' "$(openssl rand -hex 24)" > .secrets/project_secret_key.txt
# Six containers with different uids read these through bind mounts, so the files
# are world-readable; the directory is what keeps other host users out.
chmod 644 .secrets/*.txt
chmod 700 .secrets

echo "Administrator: $email"
echo "Password:      $(cat .secrets/admin_password.txt)"
echo "Project API keys (for SDK clients):"
echo "  public: $(cat .secrets/project_public_key.txt)"
echo "  secret: $(cat .secrets/project_secret_key.txt)"
echo
echo "Data directories (owners are the container users):"
echo "  mkdir -p volumes/{postgres,clickhouse,redis,minio}"
echo "  sudo chown 101:101 volumes/clickhouse"
echo "  sudo chown 999:999 volumes/redis"
echo "  sudo chown 1000:1000 volumes/minio"
echo "Then: docker compose up -d"
