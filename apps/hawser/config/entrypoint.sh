#!/bin/sh
# =========================================================
# Load TOKEN from Docker Secret at runtime.
# Hawser does not support TOKEN_FILE natively.
# =========================================================
set -e

export TOKEN="$(cat /run/secrets/HAWSER_TOKEN)"

exec /hawser "$@"
