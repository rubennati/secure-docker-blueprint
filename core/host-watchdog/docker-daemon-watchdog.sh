#!/bin/sh
# Optional, host-installed. Restarts the Docker daemon after its API has
# failed to answer for several consecutive checks in a row — not on the first
# failure, and never more than once per confirmed episode. See README.md for
# what this does and does not cover, and why it runs on the host rather than
# in a container.
#
#   sudo cp docker-daemon-watchdog.env.example /etc/docker-daemon-watchdog.env
#   sudo nano /etc/docker-daemon-watchdog.env    # set HEALTHCHECKS_PING_URL
#   sudo cp docker-daemon-watchdog.service.example /etc/systemd/system/docker-daemon-watchdog.service
#   sudo cp docker-daemon-watchdog.timer.example /etc/systemd/system/docker-daemon-watchdog.timer
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now docker-daemon-watchdog.timer
set -eu

[ "$(id -u)" -eq 0 ] || { echo "run as root — restarts a system service" >&2; exit 2; }

ENV_FILE="${DOCKER_WATCHDOG_ENV:-/etc/docker-daemon-watchdog.env}"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found — see docker-daemon-watchdog.env.example" >&2; exit 1; }
# shellcheck source=/dev/null
. "$ENV_FILE"

: "${HEALTHCHECKS_PING_URL:?set in $ENV_FILE}"
CONFIRM_AFTER="${CONFIRM_AFTER:-3}"
SETTLE_SECONDS="${SETTLE_SECONDS:-10}"
STATE_FILE="${STATE_FILE:-/var/lib/docker-daemon-watchdog/state}"
SOCK="${DOCKER_SOCKET:-/var/run/docker.sock}"

mkdir -p "$(dirname "$STATE_FILE")"
[ -f "$STATE_FILE" ] || echo "0 ok" > "$STATE_FILE"
read -r STREAK PHASE < "$STATE_FILE"

# $1: "" for a success ping, "/fail" for a failure ping. $2: log body,
# stored by Healthchecks against the ping for later reading — not sent
# anywhere else. Never lets a ping failure abort the script.
report() {
  curl -fsS -m 10 --data-raw "$2" "${HEALTHCHECKS_PING_URL}${1}" >/dev/null 2>&1 || true
}

api_ok() {
  curl -fsS -m 5 --unix-socket "$SOCK" http://localhost/_ping >/dev/null 2>&1
}

if api_ok; then
  echo "0 ok" > "$STATE_FILE"
  report "" "daemon responding"
  exit 0
fi

STREAK=$((STREAK + 1))

if [ "$PHASE" = "escalated" ]; then
  # Already tried once for this episode and it did not hold. Do not restart
  # again on every run — keep reporting failure until a human clears it or
  # the daemon recovers on its own (caught by the `api_ok` branch above).
  echo "$STREAK escalated" > "$STATE_FILE"
  report /fail "daemon still unresponsive after the one restart attempt (streak $STREAK) — not retrying automatically"
  exit 0
fi

if [ "$STREAK" -lt "$CONFIRM_AFTER" ]; then
  echo "$STREAK watching" > "$STATE_FILE"
  report "" "daemon unresponsive, streak $STREAK/$CONFIRM_AFTER — watching"
  exit 0
fi

# Confirmed: unresponsive for CONFIRM_AFTER consecutive checks. One attempt.
echo "$STREAK restarting" > "$STATE_FILE"
systemctl restart docker || true
sleep "$SETTLE_SECONDS"

if api_ok; then
  echo "0 ok" > "$STATE_FILE"
  report "" "restarted after $STREAK unresponsive checks, daemon now responding"
else
  echo "$STREAK escalated" > "$STATE_FILE"
  report /fail "restarted after $STREAK unresponsive checks, still unresponsive — not retrying automatically"
fi
