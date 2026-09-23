#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
#
# The secret FILE names here are lower case; the secret NAMES in
# docker-compose.yml are the variable names Plausible looks for under
# /run/secrets, which is where it reads settings from before the environment.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd database_url clickhouse_database_url secret_key_base totp_vault_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

# The database name, user and service names have to match docker-compose.yml
# and .env, because the connection URL is assembled from them here.
DB_NAME="$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2- || true)"
DB_USER="$(grep -E '^DB_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
: "${DB_NAME:=plausible}"
: "${DB_USER:=plausible}"

umask 077
mkdir -p .secrets

DB_PWD="$(openssl rand -hex 24)"
printf '%s' "$DB_PWD" > .secrets/db_pwd.txt
printf 'postgres://%s:%s@plausible-db:5432/%s' "$DB_USER" "$DB_PWD" "$DB_NAME" \
    > .secrets/database_url.txt
unset DB_PWD

# No credential: that server has no user set up and is on an internal network.
printf 'http://plausible-events-db:8123/plausible_events_db' \
    > .secrets/clickhouse_database_url.txt

# At least 64 bytes, or the application refuses to start.
openssl rand -base64 48 | tr -d '\n' > .secrets/secret_key_base.txt
# Exactly 32 bytes, base64. This encrypts the two-factor secrets.
openssl rand -base64 32 | tr -d '\n' > .secrets/totp_vault_key.txt

# Three containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/postgres volumes/clickhouse volumes/clickhouse-logs volumes/plausible

echo "Created .secrets/{db_pwd,database_url,clickhouse_database_url,secret_key_base,totp_vault_key}.txt"
echo
echo "Keep a copy of .secrets/totp_vault_key.txt off this host: it encrypts the"
echo "two-factor secrets, and without it every account with 2FA is locked out."
echo
echo "Next:"
echo "  sudo chown -R 999:999 volumes/plausible"
echo "  docker compose up -d"
echo "  # then create the first account — see README, 'Setup'"
