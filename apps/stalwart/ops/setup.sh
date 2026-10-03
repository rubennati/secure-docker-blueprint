#!/usr/bin/env bash
# First start: completes Stalwart's setup over its API and applies the security
# settings this stack ships. Run once, after ops/init.sh.
#   ops/setup.sh           docker-compose.yml, reads .env
#   ops/setup.sh --local   docker-compose.local.yml, reads .env.local
#
# APP_BAN_HOURS=24 ops/setup.sh   # how long an automatic ban lasts
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--local" ]; then
  COMPOSE=(docker compose -f docker-compose.local.yml --env-file .env.local)
  ENV_FILE=.env.local
  ETC=volumes/local/etc
  LOCAL=1
else
  COMPOSE=(docker compose)
  ENV_FILE=.env
  ETC=volumes/etc
  LOCAL=0
fi

[ -f "$ENV_FILE" ] || { echo "$ENV_FILE is missing — copy it from its example first" >&2; exit 1; }
[ -d "$ETC" ] || { echo "$ETC is missing — run ops/init.sh first" >&2; exit 1; }
[ ! -s "$ETC/config.json" ] || { echo "$ETC/config.json exists — this installation is already set up" >&2; exit 1; }

val() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2-; }
DOMAIN=$(val APP_MAIL_DOMAIN)
if [ "$LOCAL" = 1 ]; then HOST="mail.$DOMAIN"; else HOST=$(val APP_TRAEFIK_HOST); fi
[ -n "$DOMAIN" ] && [ -n "$HOST" ] || { echo "APP_MAIL_DOMAIN and APP_TRAEFIK_HOST must be set in $ENV_FILE" >&2; exit 1; }
BAN_MS=$(( ${APP_BAN_HOURS:-24} * 3600000 ))

api() {  # $1 user:password   $2 JMAP method calls
  "${COMPOSE[@]}" exec -T stalwart curl -fsS -u "$1" -H 'Content-Type: application/json' \
    -X POST http://127.0.0.1:8080/jmap \
    -d "{\"using\":[\"urn:ietf:params:jmap:core\",\"urn:stalwart:jmap\"],\"methodCalls\":$2}"
}

wait_up() {
  for _ in $(seq 60); do
    if "${COMPOSE[@]}" exec -T stalwart curl -fsS -o /dev/null http://127.0.0.1:8080/healthz/live 2>/dev/null; then return 0; fi
    sleep 2
  done
  echo "Stalwart does not answer on port 8080 — see: ${COMPOSE[*]} logs stalwart" >&2
  exit 1
}

# 1. Bootstrap mode, with a one-time administrator that exists only for this run.
BOOT_PW=$(openssl rand -hex 16)
STALWART_RECOVERY_ADMIN="admin:$BOOT_PW" "${COMPOSE[@]}" up -d
wait_up

# 2. The setup wizard's fields. Certificates are requested separately — README.
OUT=$(api "admin:$BOOT_PW" "[[\"x:Bootstrap/set\",{\"update\":{\"singleton\":{
  \"serverHostname\":\"$HOST\",
  \"defaultDomain\":\"$DOMAIN\",
  \"requestTlsCertificate\":false,
  \"generateDkimKeys\":true,
  \"tracer\":{\"@type\":\"Stdout\",\"level\":\"info\",\"ansi\":false,\"multiline\":false,\"enable\":true,\"lossy\":false,\"events\":{},\"eventsPolicy\":\"exclude\"}
}}},\"c1\"]]")
ADMIN=$(printf '%s' "$OUT" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
ADMIN_PW=$(printf '%s' "$OUT" | sed -n 's/.*"secret":"\([^"]*\)".*/\1/p')
[ -n "$ADMIN" ] && [ -n "$ADMIN_PW" ] || { echo "Setup was refused: $OUT" >&2; exit 1; }
( umask 077; printf '%s' "$ADMIN_PW" > .secrets/admin_pwd.txt )

# 3. Normal mode, without the one-time administrator.
"${COMPOSE[@]}" up -d --force-recreate
wait_up

# 4. Security settings.
#    - Automatic bans expire; upstream's default keeps them until removed by hand.
#    - Behind Traefik the client address comes from X-Forwarded-For. Without it
#      every ban and every HTTP rate limit lands on the proxy's address.
CALLS="[\"x:Security/set\",{\"update\":{\"singleton\":{\"authBanPeriod\":$BAN_MS,\"abuseBanPeriod\":$BAN_MS,\"loiterBanPeriod\":$BAN_MS,\"scanBanPeriod\":$BAN_MS}}},\"c1\"]"
if [ "$LOCAL" = 0 ]; then
  CALLS="$CALLS,[\"x:Http/set\",{\"update\":{\"singleton\":{\"useXForwarded\":true}}},\"c2\"]"
fi
OUT=$(api "$ADMIN:$ADMIN_PW" "[$CALLS]")
case "$OUT" in
  *notUpdated*|*error*) echo "Security settings were refused: $OUT" >&2; exit 1 ;;
esac
"${COMPOSE[@]}" restart stalwart >/dev/null
wait_up

echo
echo "Stalwart is set up."
echo "  Administrator: $ADMIN"
echo "  Password:      .secrets/admin_pwd.txt"
if [ "$LOCAL" = 1 ]; then
  echo "  Interface:     http://localhost:8080/admin"
else
  echo "  Interface:     https://$HOST/admin"
  echo
  echo "Next: the DNS records and the certificate — README, 'DNS' and 'Certificate'."
  echo "Then the mail ports: docker compose -f docker-compose.yml -f mail.yml up -d"
fi
