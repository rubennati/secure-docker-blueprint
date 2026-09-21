#!/usr/bin/env bash
# Generates the secrets and prepares the mounted paths. Refuses to overwrite.
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
# Hex: no character that needs quoting on a command line, in a URL or in PHP.
for f in db_pwd db_root_pwd admin_pwd; do
  printf '%s' "$(openssl rand -hex 24)" > ".secrets/$f.txt"
done
# The containers read these through bind mounts: the application as root before
# Apache drops to www-data, config.php and the cron job as www-data, MariaDB as
# the mysql user.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/facturascripts volumes/mysql

echo "Created .secrets/{db_pwd,db_root_pwd,admin_pwd}.txt"
echo
echo "Next:"
echo "  sudo chown -R 33:33 volumes/facturascripts"
echo "  docker compose up -d"
echo "  ops/install.sh admin"
