#!/usr/bin/env bash
# Creates what Authelia needs before its first start: the secrets, the data
# directories and the first user. Safe to run again — nothing that exists is
# overwritten.
#
# Usage: ops/init.sh [username] [email]
#        ops/init.sh --local [username]   for docker-compose.local.yml
set -euo pipefail
cd "$(dirname "$0")/.."

local_mode=false
if [ "${1:-}" = "--local" ]; then
  local_mode=true
  shift
fi

if $local_mode; then
  env_file=.env.local
  root=volumes/local
else
  env_file="${ENV_FILE:-.env}"
  root=volumes
fi
if [ ! -f "$env_file" ]; then
  echo "create $env_file first — cp ${env_file}.example $env_file" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
. "./$env_file"
set +a

user="${1:-admin}"
email="${2:-admin@${SESSION_COOKIE_DOMAIN:-example.localhost}}"
image="authelia/authelia:${APP_TAG}"

mkdir -p "$root/data" "$root/runtime"
[ -e "$root/runtime/healthcheck.env" ] || : > "$root/runtime/healthcheck.env"

if $local_mode; then
  pwd_file="$root/admin_pwd.txt"
  mkdir -p "$root/tls"
  if [ ! -s "$root/tls/public.crt" ]; then
    docker run --rm --user 0 --entrypoint authelia -v "$PWD/$root/tls:/tls" "$image" \
      crypto certificate rsa generate --common-name auth.example.localhost \
      --sans auth.example.localhost --directory /tls >/dev/null
  fi
else
  pwd_file=.secrets/admin_pwd.txt
  mkdir -p .secrets "$root/postgres" "$root/redis"
  chmod 700 .secrets
  new_secret() {
    [ -s ".secrets/$1" ] || openssl rand -hex "$2" > ".secrets/$1"
  }
  new_secret db_pwd.txt 32
  new_secret jwt_secret.txt 64
  new_secret session_secret.txt 64
  new_secret storage_encryption_key.txt 64
  [ -e .secrets/smtp_password.txt ] || : > .secrets/smtp_password.txt
fi

# The first user. Authelia generates the password and prints it once with its
# hash, so the password never appears on a command line.
if [ ! -s "$root/data/users_database.yml" ]; then
  out="$(docker run --rm "$image" authelia crypto hash generate argon2 --random --random.length 32)"
  printf '%s' "$(printf '%s\n' "$out" | sed -n 's/^Random Password: //p')" > "$pwd_file"
  chmod 600 "$pwd_file"
  digest="$(printf '%s\n' "$out" | sed -n 's/^Digest: //p')"
  cat > "$root/data/users_database.yml" <<USERS
users:
  ${user}:
    disabled: false
    displayname: '${user}'
    password: '${digest}'
    email: '${email}'
    groups:
      - 'admins'
USERS
  echo "created user '${user}' — the password is in ${pwd_file}"
fi

# Ownership as the containers see it: Authelia and Redis run as fixed users and
# read their files themselves. A throwaway container sets it, so no sudo.
docker run --rm --user 0 --entrypoint sh -v "$PWD:/stack" -e ROOT="$root" -e LOCAL="$local_mode" "$image" -c '
  chown -R 1000:1000 "/stack/$ROOT/data" "/stack/$ROOT/runtime"
  if [ "$LOCAL" = true ]; then
    chown -R 1000:1000 "/stack/$ROOT/tls"
  else
    chown -R 999:1000 "/stack/$ROOT/redis"
    for f in db_pwd jwt_secret session_secret storage_encryption_key smtp_password; do
      chgrp 1000 "/stack/.secrets/$f.txt" && chmod 640 "/stack/.secrets/$f.txt"
    done
  fi
'
echo "done"
