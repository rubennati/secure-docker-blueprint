#!/usr/bin/env bash
# One-time setup: the three passwords, the server's own TLS certificate, and
# the repository. Refuses to overwrite anything that already exists, so it is
# safe to run again.
#
# Runs against docker-compose.yml. To set up the local variant instead:
#   COMPOSE_FILE=docker-compose.local.yml ops/init.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-.env}"
[ -f "$ENV_FILE" ] || { echo "refusing: $ENV_FILE is missing — copy .env.example first" >&2; exit 1; }
# shellcheck disable=SC1090
set -a; . "./$ENV_FILE"; set +a

mkdir -p .secrets volumes/repository volumes/config volumes/cache volumes/logs

new_secret() {
  if [ -e "$1" ]; then
    echo "keeping   $1"
    return
  fi
  printf '%s' "$(openssl rand -base64 24 | tr -d '\n')" > "$1"
  # 644 inside a 700 directory: the directory is what keeps other users out,
  # and the server reads the file as APP_UID, which need not be your own uid.
  chmod 644 "$1"
  echo "created   $1"
}

new_secret .secrets/kopia_repository_password.txt
new_secret .secrets/kopia_server_password.txt
new_secret .secrets/kopia_server_control_password.txt
chmod 700 .secrets

if [ -e volumes/config/tls.crt ]; then
  echo "keeping   volumes/config/tls.crt"
else
  # Kopia's own --tls-generate-cert refuses to start once the file exists, so
  # the certificate is made here instead. Traefik does not verify it — see
  # backend-selfsigned in core/traefik — and Kopia clients pin it by
  # fingerprint when they connect to the container directly.
  docker compose ${ENV_FILE:+--env-file "$ENV_FILE"} run --rm --entrypoint openssl kopia-server \
    req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -subj "/CN=${APP_TRAEFIK_HOST:-kopia.example.com}" \
    -addext "subjectAltName=DNS:${APP_TRAEFIK_HOST:-kopia.example.com}" \
    -keyout /app/config/tls.key -out /app/config/tls.crt
  echo "created   volumes/config/tls.crt"
fi

if [ -e volumes/config/repository.config ]; then
  echo "keeping   volumes/config/repository.config"
else
  docker compose ${ENV_FILE:+--env-file "$ENV_FILE"} run --rm kopia-server \
    /bin/kopia repository create filesystem --path=/repository
  echo "created   the repository under volumes/repository"
fi

echo
echo "Back up .secrets/kopia_repository_password.txt somewhere else."
echo "It is the key to the data: without it the snapshots cannot be read, and"
echo "nothing in the repository can recover it."
echo
echo "Next:"
echo "  docker compose up -d"
echo "  # through the entrypoint — a plain exec has no repository password and prompts"
echo "  docker compose exec kopia-server /bin/sh /config/entrypoint.sh \\"
echo "      /bin/kopia server user add <user>@<machine>"
echo "  docker compose restart kopia-server     # or 'kopia server refresh'"
