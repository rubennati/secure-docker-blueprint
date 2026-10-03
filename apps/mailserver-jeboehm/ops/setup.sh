#!/usr/bin/env bash
# First start: creates the mail domain, the administrator and the DKIM key.
# Run once, after ops/init.sh.
#   ops/setup.sh           docker-compose.yml, reads .env
#   ops/setup.sh --local   docker-compose.local.yml, reads .env.local
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--local" ]; then
  COMPOSE=(docker compose -f docker-compose.local.yml --env-file .env.local)
  ENV_FILE=.env.local
  BASE=volumes/local
  WEB=web
  CONSOLE=(/entrypoint.sh /opt/admin/bin/console)
else
  COMPOSE=(docker compose)
  ENV_FILE=.env
  BASE=volumes
  WEB=mailserver-jeboehm-web
  CONSOLE=(/bin/sh /config/entrypoint-web.sh /opt/admin/bin/console)
fi

[ -f "$ENV_FILE" ] || { echo "$ENV_FILE is missing — copy it from its example first" >&2; exit 1; }
[ -s "$BASE/certs/tls.crt" ] && [ -s "$BASE/certs/tls.key" ] || {
  echo "$BASE/certs needs tls.crt and tls.key — README, 'Certificate'" >&2; exit 1; }
[ ! -s .secrets/admin_pwd.txt ] || { echo ".secrets/admin_pwd.txt exists — this installation is already set up" >&2; exit 1; }

DOMAIN=$(grep -E '^APP_MAIL_DOMAIN=' "$ENV_FILE" | tail -1 | cut -d= -f2-)
[ -n "$DOMAIN" ] || { echo "APP_MAIL_DOMAIN must be set in $ENV_FILE" >&2; exit 1; }

"${COMPOSE[@]}" up -d --wait

console() { "${COMPOSE[@]}" exec -T "$WEB" "${CONSOLE[@]}" "$@"; }

console domain:add "$DOMAIN"
PW=$(openssl rand -hex 16)
console user:add --admin --enable --password="$PW" postmaster "$DOMAIN" >/dev/null
( umask 077; printf '%s' "$PW" > .secrets/admin_pwd.txt )
console dkim:setup --enable "$DOMAIN" > "$BASE/dkim-$DOMAIN.txt"

echo
echo "The mail server is set up."
echo "  Administrator: postmaster@$DOMAIN"
echo "  Password:      .secrets/admin_pwd.txt"
echo "  DKIM record:   $BASE/dkim-$DOMAIN.txt"
if [ "${1:-}" = "--local" ]; then
  echo "  Interface:     http://localhost:8080"
else
  echo
  echo "Next: the DNS records — README, 'DNS'."
  echo "Then the mail ports: docker compose -f docker-compose.yml -f mail.yml up -d"
fi
