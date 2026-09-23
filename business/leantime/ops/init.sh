#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in db_pwd db_root_pwd session_password; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
printf '%s' "$(openssl rand -hex 24)" > .secrets/db_pwd.txt
printf '%s' "$(openssl rand -hex 24)" > .secrets/db_root_pwd.txt
# Salts the session cookies. Changing it later signs everyone out.
printf '%s' "$(openssl rand -hex 32)" > .secrets/session_password.txt
# Two containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/mysql volumes/userfiles volumes/public-userfiles \
         volumes/storage volumes/plugins

echo "Created .secrets/{db_pwd,db_root_pwd,session_password}.txt"
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/userfiles volumes/public-userfiles \\"
echo "      volumes/storage volumes/plugins"
echo "  docker compose up -d leantime-db     # the database alone — no router yet"
echo "  ops/install.sh                       # creates the schema and the admin"
echo "  docker compose up -d                 # start the application"
echo
echo "Run ops/install.sh BEFORE the application container starts: until the"
echo "schema exists, Leantime answers its web installer to whoever asks first,"
echo "and that installer creates the administrator."
