#!/bin/sh
set -e

# obot reads every setting from the environment and has no _FILE variant, so the
# two that are credentials are exported here from Docker Secrets and the image's
# own entrypoint runs after them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string.

# --- Database (required) ---
# Setting this is what stops the image starting the PostgreSQL it bundles, whose
# user and password are `obot`/`obot` baked into the image. The URL carries the
# password inline, which is why the whole URL is the secret.
_server_dsn="$(cat /run/secrets/OBOT_SERVER_DSN)"
export OBOT_SERVER_DSN="$_server_dsn"
unset _server_dsn

# --- Bootstrap token (required) ---
# The first sign-in. Without it obot generates one and prints it to the
# container log, where it stays.
_bootstrap_token="$(cat /run/secrets/OBOT_BOOTSTRAP_TOKEN)"
export OBOT_BOOTSTRAP_TOKEN="$_bootstrap_token"
unset _bootstrap_token

exec run.sh "$@"
