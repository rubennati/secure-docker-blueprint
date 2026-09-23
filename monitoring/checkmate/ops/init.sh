#!/usr/bin/env bash
# Generates the secrets and prepares the data directory. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_root_pwd db_connection_string jwt_secret encryption_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

# The connection string is assembled from these, so they have to match .env.
DB_ROOT_USER="$(grep -E '^DB_ROOT_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
DB_NAME="$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2- || true)"
: "${DB_ROOT_USER:=checkmate}"
: "${DB_NAME:=uptime_db}"

umask 077
mkdir -p .secrets

# No URL-encoding step: a hex password has no character that needs one.
DB_PWD="$(openssl rand -hex 24)"
printf '%s' "$DB_PWD" > .secrets/db_root_pwd.txt
# authSource=admin because MONGO_INITDB_ROOT_* creates the user in `admin`,
# not in the application database.
printf 'mongodb://%s:%s@checkmate-db:27017/%s?authSource=admin' \
    "$DB_ROOT_USER" "$DB_PWD" "$DB_NAME" > .secrets/db_connection_string.txt
unset DB_PWD

# Signs every session token. Changing it signs everyone out.
openssl rand -hex 32 | tr -d '\n' > .secrets/jwt_secret.txt

# Exactly 32 bytes as padded standard base64 — the application validates the
# shape and refuses to start on anything else.
openssl rand -base64 32 | tr -d '\n' > .secrets/encryption_key.txt

# Two containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/mongodb

echo "Created .secrets/{db_root_pwd,db_connection_string,jwt_secret,encryption_key}.txt"
echo
echo "Next:"
echo "  docker compose up -d"
echo "  # then create the first account immediately — see README, 'Setup'"
