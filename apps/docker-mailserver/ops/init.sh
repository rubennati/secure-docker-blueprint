#!/usr/bin/env bash
# Creates the data directories.
#   ops/init.sh           for docker-compose.yml
#   ops/init.sh --local   for docker-compose.local.yml, with a self-signed certificate
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--local" ]; then BASE=volumes/local; else BASE=volumes; fi

mkdir -p "$BASE/mail-data" "$BASE/mail-state" "$BASE/mail-logs" "$BASE/config" "$BASE/certs" .secrets
chmod 700 .secrets

if [ "${1:-}" = "--local" ]; then
  DOMAIN=$(grep -E '^APP_MAIL_DOMAIN=' .env.local | tail -1 | cut -d= -f2-)
  if [ ! -s "$BASE/certs/fullchain.pem" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
      -subj "/CN=mail.$DOMAIN" -addext "subjectAltName=DNS:mail.$DOMAIN" \
      -keyout "$BASE/certs/privkey.pem" -out "$BASE/certs/fullchain.pem" 2>/dev/null
    chmod 600 "$BASE/certs/privkey.pem"
  fi
  echo "Created $BASE/ with a self-signed certificate, and .secrets"
  echo
  echo "Next:"
  echo "  ops/setup.sh --local"
else
  echo "Created $BASE/ and .secrets"
  echo
  echo "Next:"
  echo "  put fullchain.pem and privkey.pem into $BASE/certs   # README, 'Certificate'"
  echo "  ops/setup.sh"
fi
