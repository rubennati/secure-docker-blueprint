#!/usr/bin/env bash
# Generates every secret DefectDojo needs, including the three connection URLs
# that carry the passwords, and prepares the data directories. Refuses to
# overwrite existing secrets.
set -euo pipefail
cd "$(dirname "$0")/.."

files=(db_pwd valkey_pwd dd_database_url dd_celery_broker_url dd_cache_url
       dd_secret_key dd_credential_aes_256_key dd_admin_password)
for f in "${files[@]}"; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

[ -f .env ] || { echo "copy .env.example to .env first" >&2; exit 1; }
set -a
# shellcheck disable=SC1091
. ./.env
set +a

umask 077
mkdir -p .secrets
w() { printf '%s' "$2" > ".secrets/$1.txt"; }
# Hex: both passwords are embedded in URLs.
db_pwd="$(openssl rand -hex 24)"
valkey_pwd="$(openssl rand -hex 24)"
w db_pwd "$db_pwd"
w valkey_pwd "$valkey_pwd"
w dd_database_url "postgresql://${DB_USER}:${db_pwd}@db:5432/${DB_NAME}"
w dd_celery_broker_url "redis://:${valkey_pwd}@valkey:6379/0"
w dd_cache_url "redis://:${valkey_pwd}@valkey:6379/1"
w dd_secret_key "$(openssl rand -hex 32)"
# AES-256: exactly 32 characters.
w dd_credential_aes_256_key "$(openssl rand -hex 16)"
w dd_admin_password "$(openssl rand -hex 16)"
# Several containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/media volumes/postgres volumes/valkey

echo "Created the secrets in .secrets/"
echo "Administrator: ${ADMIN_USER}, password in .secrets/dd_admin_password.txt"
echo
echo "Next:"
echo "  sudo chown 1001:1001 volumes/media"
echo "  sudo chown 999:1000 volumes/valkey"
echo "  docker compose up -d"
