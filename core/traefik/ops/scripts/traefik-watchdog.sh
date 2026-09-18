#!/usr/bin/env bash
set -euo pipefail

# Optional, host-installed. Restarts the Traefik container after it has been
# reported unhealthy for several consecutive checks in a row — not on the
# first failure, and never more than once per confirmed episode. See
# ../../../host-watchdog/README.md for the shared model and why this runs on
# the host rather than in a container.
#
# Traefik is the one container in this repository this pattern is judged
# reasonable for: it holds no state of its own, so a wrong restart costs a
# few seconds of routing, not data. Do not copy this onto a stateful service
# without the same argument holding for it — see
# ../../../host-watchdog/README.md#what-this-is-not.
#
#   sudo cp traefik-watchdog.env.example /etc/traefik-watchdog.env
#   sudo nano /etc/traefik-watchdog.env        # set HEALTHCHECKS_PING_URL, CONTAINER_NAME
#   sudo cp traefik-watchdog.sh /usr/local/bin/traefik-watchdog.sh
#   sudo chmod 755 /usr/local/bin/traefik-watchdog.sh
#   sudo cp traefik-watchdog.service.example /etc/systemd/system/traefik-watchdog.service
#   sudo cp traefik-watchdog.timer.example /etc/systemd/system/traefik-watchdog.timer
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now traefik-watchdog.timer

ENV_FILE="${TRAEFIK_WATCHDOG_ENV:-/etc/traefik-watchdog.env}"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found — see traefik-watchdog.env.example" >&2; exit 1; }
# shellcheck source=/dev/null
source "$ENV_FILE"

: "${CONTAINER_NAME:?set in $ENV_FILE}"
: "${HEALTHCHECKS_PING_URL:?set in $ENV_FILE}"
CONFIRM_AFTER="${CONFIRM_AFTER:-3}"
SETTLE_SECONDS="${SETTLE_SECONDS:-15}"
STATE_FILE="${STATE_FILE:-/var/lib/traefik-watchdog/state}"

mkdir -p "$(dirname "$STATE_FILE")"
[ -f "$STATE_FILE" ] || echo "0 ok" > "$STATE_FILE"
read -r STREAK PHASE < "$STATE_FILE"

# $1: "" for a success ping, "/fail" for a failure ping. $2: log body, stored
# by Healthchecks against the ping for later reading. Never lets a ping
# failure abort the script.
report() {
  curl -fsS -m 10 --data-raw "$2" "${HEALTHCHECKS_PING_URL}${1}" >/dev/null 2>&1 || true
}

status="$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>&1)" \
  || { echo "0 ok" > "$STATE_FILE"; report /fail "cannot inspect $CONTAINER_NAME: $status"; exit 0; }

if [ "$status" != "unhealthy" ]; then
  echo "0 ok" > "$STATE_FILE"
  report "" "container status: $status"
  exit 0
fi

STREAK=$((STREAK + 1))

if [ "$PHASE" = "escalated" ]; then
  # Already tried once for this episode and it did not hold. Do not restart
  # again on every run — keep reporting failure until a human clears it or
  # the container recovers on its own.
  echo "$STREAK escalated" > "$STATE_FILE"
  report /fail "still unhealthy after the one restart attempt (streak $STREAK) — not retrying automatically"
  exit 0
fi

if [ "$STREAK" -lt "$CONFIRM_AFTER" ]; then
  echo "$STREAK watching" > "$STATE_FILE"
  report "" "unhealthy, streak $STREAK/$CONFIRM_AFTER — watching"
  exit 0
fi

# Confirmed: unhealthy for CONFIRM_AFTER consecutive checks. One attempt.
echo "$STREAK restarting" > "$STATE_FILE"
docker restart "$CONTAINER_NAME" >/dev/null 2>&1 || true
sleep "$SETTLE_SECONDS"

status_after="$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")"
if [ "$status_after" != "unhealthy" ]; then
  echo "0 ok" > "$STATE_FILE"
  report "" "restarted after $STREAK unhealthy checks, now $status_after"
else
  echo "$STREAK escalated" > "$STATE_FILE"
  report /fail "restarted after $STREAK unhealthy checks, still unhealthy — not retrying automatically"
fi
