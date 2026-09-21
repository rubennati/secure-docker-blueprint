#!/usr/bin/env bash
# Generates the login and prepares the mounted paths. Refuses to overwrite.
#
# Usage: ops/init.sh [user]      (default user: admin)
set -euo pipefail
cd "$(dirname "$0")/.."

user="${1:-admin}"

for f in gui_pwd.txt gui_htpasswd; do
  if [ -e ".secrets/$f" ]; then
    echo "refusing: .secrets/$f exists" >&2
    exit 1
  fi
done

umask 077
mkdir -p .secrets
# The password for you to log in with, and the hash rclone checks it against.
# rclone reads APR1 hashes; SHA-512 crypt ($6$) is not accepted. The password
# goes to openssl on stdin, not on the command line.
pw="$(openssl rand -hex 24)"
printf '%s' "$pw" > .secrets/gui_pwd.txt
printf '%s:%s\n' "$user" "$(printf '%s' "$pw" | openssl passwd -apr1 -stdin)" > .secrets/gui_htpasswd
unset pw
# rclone reads the hash through a bind mount as APP_UID.
chmod 644 .secrets/gui_htpasswd
chmod 700 .secrets

mkdir -p volumes/config volumes/data

echo "Created .secrets/gui_pwd.txt and .secrets/gui_htpasswd for user '$user'"
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/config volumes/data"
echo "  docker compose up -d"
