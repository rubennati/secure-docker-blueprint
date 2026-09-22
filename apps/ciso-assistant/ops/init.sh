#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd django_secret_key admin_pwd; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 24)" > .secrets/db_pwd.txt
# Upstream generates the same shape itself: openssl rand -hex 32.
printf '%s' "$(openssl rand -hex 32)" > .secrets/django_secret_key.txt
printf '%s' "$(openssl rand -hex 16)" > .secrets/admin_pwd.txt
# Several containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/data volumes/postgres

echo "Created .secrets/{db_pwd,django_secret_key,admin_pwd}.txt"
echo "The administrator is created on the first start from ADMIN_EMAIL (.env) and"
echo "the password in .secrets/admin_pwd.txt."
echo
echo "Next:"
echo "  sudo chown 1001:1001 volumes/data"
echo "  docker compose up -d        # the first start takes several minutes"
