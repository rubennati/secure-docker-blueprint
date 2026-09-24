#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_root_pwd mongo_uri cache_pwd session_key form_encryption_key smtp_pwd; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

# The connection URL is assembled from these, so they have to match .env.
DB_ROOT_USER="$(grep -E '^DB_ROOT_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
DB_NAME="$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2- || true)"
: "${DB_ROOT_USER:=heyform}"
: "${DB_NAME:=heyform}"

umask 077
mkdir -p .secrets

# Hex throughout: this password goes into a MongoDB URL, and hex has no
# character that would need percent-encoding there.
DB_PWD="$(openssl rand -hex 24)"
printf '%s' "$DB_PWD" > .secrets/db_root_pwd.txt
# authSource=admin because MONGO_INITDB_ROOT_* creates the user in `admin`,
# not in the application database.
printf 'mongodb://%s:%s@heyform-db:27017/%s?authSource=admin' \
    "$DB_ROOT_USER" "$DB_PWD" "$DB_NAME" > .secrets/mongo_uri.txt
unset DB_PWD

# Handed to valkey-server on its command line by config/cache-entrypoint.sh.
openssl rand -hex 24 | tr -d '\n' > .secrets/cache_pwd.txt

# Signs the session cookie. Changing it signs everyone out.
openssl rand -hex 32 | tr -d '\n' > .secrets/session_key.txt

# Encrypts form-level passwords and the hidden-field payloads in a form URL.
# Changing it after forms exist makes those unreadable.
openssl rand -hex 32 | tr -d '\n' > .secrets/form_encryption_key.txt

# Empty on purpose: an instance without SMTP has no password to put here, and
# the file existing is what keeps the mount from failing.
: > .secrets/smtp_pwd.txt

# Three containers with different uids read these through Docker Secrets.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/mongodb volumes/upload
# The application container runs as 1000:1000 with a read-only filesystem, and
# the upload directory is the one path it writes to.
chown 1000:1000 volumes/upload 2>/dev/null || {
  echo "note: could not chown volumes/upload — run as root, or:" >&2
  echo "      sudo chown 1000:1000 volumes/upload" >&2
}

echo "Created .secrets/{db_root_pwd,mongo_uri,cache_pwd,session_key,form_encryption_key,smtp_pwd}.txt"
echo
echo "Next:"
echo "  docker compose up -d"
echo "  # then create the first account — see README, 'Setup'"
