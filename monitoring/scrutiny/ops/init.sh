#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in influxdb_password influxdb_token; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
openssl rand -base64 24 | tr -d '\n' > .secrets/influxdb_password.txt
# InfluxDB hands this token to whoever holds it; Scrutiny authenticates with it.
openssl rand -hex 32 | tr -d '\n' > .secrets/influxdb_token.txt
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/influxdb volumes/influxdb-config volumes/scrutiny-config

echo "Created .secrets/{influxdb_password,influxdb_token}.txt"
echo
echo "Scrutiny has no login of its own. Put a password in front of it before"
echo "you start — see README, 'The interface has no password':"
echo
echo "  htpasswd -nbB ops 'the-password' | sed -e 's/\\\$/\\\$\\\$/g'"
echo
echo "and paste the result into APP_BASIC_AUTH_USERS in .env."
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/influxdb volumes/influxdb-config"
echo "  sudo chown -R 1000:1000 volumes/scrutiny-config"
echo "  docker compose up -d"
