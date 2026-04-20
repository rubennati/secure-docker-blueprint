#!/bin/sh
set -e

# Load TOKEN from Docker Secret at runtime.
# Hawser reads TOKEN directly from env — no _FILE support.
[ -f /run/secrets/HAWSER_TOKEN ] && \
  export TOKEN="$(cat /run/secrets/HAWSER_TOKEN)"

exec /usr/local/bin/hawser "$@"
