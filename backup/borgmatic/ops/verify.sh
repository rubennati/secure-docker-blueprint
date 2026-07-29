#!/bin/sh
# Answer three questions about the newest archive that "the command exited 0"
# does not: is there a database dump in it, does it hold the paths you expect,
# and does it hold anything you never meant to capture.
#
#   sudo ./verify.sh                          # inspect the newest archive
#   sudo ./verify.sh /srv/docker              # also assert this path is present
#   sudo ./verify.sh /srv/docker /srv/other   # …and that this one is absent
#
# Exits non-zero if an expected path is missing or an excluded one is present,
# so it can be run from a monitoring hook.
set -eu

[ "$(id -u)" -eq 0 ] || { echo "run as root — borgmatic reads root-only credentials" >&2; exit 2; }

EXPECT="${1:-}"
FORBID="${2:-}"

archive() {
  borgmatic list --json 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["archives"][-1]["name"])'
}

count() {
  # borgmatic prefixes progress lines with the repository label; drop them.
  borgmatic list --archive "$1" --find "$2" 2>/dev/null | grep -cv '^[a-z-]*:' || true
}

A="$(archive)"
[ -n "$A" ] || { echo "no archives in the repository" >&2; exit 1; }
echo "archive: $A"

echo
echo "database dumps"
DUMPS="$(borgmatic list --archive "$A" --find '*_databases/*' 2>/dev/null \
  | grep '^-' | grep -v 'dumps.json' | awk '{printf "  %10s bytes  %s\n", $4, $NF}')"
if [ -n "$DUMPS" ]; then echo "$DUMPS"
else echo "  none — if a stack here has a database, its hook is not configured"; fi

RC=0

if [ -n "$EXPECT" ]; then
  echo
  echo "expected content"
  N="$(count "$A" "*${EXPECT}*")"
  echo "  ${EXPECT}: ${N} entries"
  [ "$N" -gt 0 ] || { echo "  MISSING" >&2; RC=1; }
fi

if [ -n "$FORBID" ]; then
  echo
  echo "must not be present"
  N="$(count "$A" "*${FORBID}*")"
  if [ "$N" -eq 0 ]; then
    echo "  ${FORBID}: absent"
  else
    echo "  ${FORBID}: ${N} entries — this configuration reaches further than intended" >&2
    RC=1
  fi
fi

exit "$RC"
