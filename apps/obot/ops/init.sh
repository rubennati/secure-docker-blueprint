#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd obot_server_dsn obot_bootstrap_token; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

# The connection string is assembled from these, so they have to match .env.
DB_NAME="$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2- || true)"
DB_USER="$(grep -E '^DB_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
: "${DB_NAME:=obot}"
: "${DB_USER:=obot}"

umask 077
mkdir -p .secrets

# A hex password needs no URL-encoding inside the connection string.
DB_PWD="$(openssl rand -hex 24)"
printf '%s' "$DB_PWD" > .secrets/db_pwd.txt
printf 'postgresql://%s:%s@obot-db:5432/%s' "$DB_USER" "$DB_PWD" "$DB_NAME" \
    > .secrets/obot_server_dsn.txt
unset DB_PWD

# The first sign-in. Upstream requires at least six characters and prints a
# generated one into the container log when it is absent — which is where it
# then stays.
openssl rand -hex 24 | tr -d '\n' > .secrets/obot_bootstrap_token.txt

# Two containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/postgres volumes/data

echo "Created .secrets/{db_pwd,obot_server_dsn,obot_bootstrap_token}.txt"
echo
echo "The bootstrap token is the first sign-in. Read it from the file, not"
echo "from the log:  cat .secrets/obot_bootstrap_token.txt"
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/data   # the uid obot runs as"
echo "  docker compose up -d"
echo "  # sign in with the token, then configure an authentication provider"
echo "  # and create a real administrator — see README, 'Setup'"
