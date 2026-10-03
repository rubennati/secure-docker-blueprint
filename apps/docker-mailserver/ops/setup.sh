#!/usr/bin/env bash
# First start: creates the postmaster mailbox and the DKIM key. Run once, after
# ops/init.sh.
#   ops/setup.sh           docker-compose.yml, reads .env
#   ops/setup.sh --local   docker-compose.local.yml, reads .env.local
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--local" ]; then
  COMPOSE=(docker compose -f docker-compose.local.yml --env-file .env.local)
  ENV_FILE=.env.local
  BASE=volumes/local
else
  COMPOSE=(docker compose)
  ENV_FILE=.env
  BASE=volumes
fi

[ -f "$ENV_FILE" ] || { echo "$ENV_FILE is missing — copy it from its example first" >&2; exit 1; }
[ -s "$BASE/certs/fullchain.pem" ] && [ -s "$BASE/certs/privkey.pem" ] || {
  echo "$BASE/certs needs fullchain.pem and privkey.pem — README, 'Certificate'" >&2; exit 1; }
[ ! -s "$BASE/config/postfix-accounts.cf" ] || { echo "$BASE/config/postfix-accounts.cf exists — this installation is already set up" >&2; exit 1; }

DOMAIN=$(grep -E '^APP_MAIL_DOMAIN=' "$ENV_FILE" | tail -1 | cut -d= -f2-)
[ -n "$DOMAIN" ] || { echo "APP_MAIL_DOMAIN must be set in $ENV_FILE" >&2; exit 1; }

"${COMPOSE[@]}" up -d

# The container stops itself unless a mailbox exists within two minutes of its
# start. /etc/dms-settings appears once the start script has read the environment.
for _ in $(seq 30); do
  if "${COMPOSE[@]}" exec -T app test -f /etc/dms-settings 2>/dev/null; then break; fi
  sleep 2
done
PW=$(openssl rand -hex 16)
( umask 077; printf '%s' "$PW" > .secrets/postmaster_pwd.txt )
printf '%s\n%s\n' "$PW" "$PW" | "${COMPOSE[@]}" exec -T app setup email add "postmaster@$DOMAIN" >/dev/null
grep -q "^postmaster@$DOMAIN|" "$BASE/config/postfix-accounts.cf" || {
  echo "The postmaster mailbox was not created — see: ${COMPOSE[*]} logs app" >&2; exit 1; }

# The DKIM key is created once Rspamd runs; the command reloads it.
for _ in $(seq 60); do
  if "${COMPOSE[@]}" exec -T app supervisorctl status rspamd 2>/dev/null | grep -q RUNNING; then break; fi
  sleep 2
done
"${COMPOSE[@]}" exec -T app setup config dkim domain "$DOMAIN" >/dev/null

echo
echo "docker-mailserver is set up."
echo "  Mailbox:   postmaster@$DOMAIN"
echo "  Password:  .secrets/postmaster_pwd.txt"
echo "  DKIM:      $BASE/config/rspamd/dkim/rsa-2048-mail-$DOMAIN.public.dns.txt"
if [ "${1:-}" != "--local" ]; then
  echo
  echo "Next: the DNS records — README, 'DNS'."
  echo "Then the mail ports: docker compose -f docker-compose.yml -f mail.yml up -d"
fi
