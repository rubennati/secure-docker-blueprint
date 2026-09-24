#!/usr/bin/env bash
# Generates the secret and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e ".secrets/db_pwd.txt" ]; then
  echo "refusing: .secrets/db_pwd.txt exists" >&2
  exit 1
fi

umask 077
mkdir -p .secrets
openssl rand -hex 24 | tr -d '\n' > .secrets/db_pwd.txt
# Three containers with different uids read this through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/postgres volumes/alertscripts volumes/externalscripts

echo "Created .secrets/db_pwd.txt"
echo
echo "Next:"
echo "  sudo chown -R 1997:1997 volumes/alertscripts volumes/externalscripts"
echo "  docker compose up -d      # the first start creates the schema, which"
echo "                            # takes a few minutes"
echo
echo "Then sign in as Admin / zabbix and change that password immediately."
echo "It is Zabbix' built-in account and it is the same on every installation."
