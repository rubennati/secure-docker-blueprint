#!/usr/bin/env bash
# Generates the secrets and prepares the two mounted paths. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd db_root_pwd admin_pwd; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
# Hex: no character that needs quoting on a command line or in a URL.
for f in db_pwd db_root_pwd admin_pwd; do
  printf '%s' "$(openssl rand -hex 24)" > ".secrets/$f.txt"
done
# The application container reads these through bind mounts as root before
# Apache drops to www-data; MariaDB reads its own as the mysql user.
chmod 644 .secrets/*.txt
chmod 700 .secrets

# .env has to exist as a file before the first start, or Docker creates a
# directory in its place. The installer fills it in.
mkdir -p volumes/storage volumes/mysql
[ -e volumes/app.env ] || : > volumes/app.env
chmod 600 volumes/app.env

echo "Created .secrets/{db_pwd,db_root_pwd,admin_pwd}.txt and volumes/app.env"
echo
echo "Next:"
echo "  sudo chown -R 33:33 volumes/storage volumes/app.env"
echo "  docker compose up -d"
echo "  ops/install.sh admin@example.com 'Your Company' company@example.com"
