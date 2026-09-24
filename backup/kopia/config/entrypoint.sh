#!/bin/sh
set -e

# Kopia reads every password from the environment and has no _FILE variant, so
# the values are exported here from Docker Secrets and the command runs after
# them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string.

# --- Repository password (required) ---
# The key to the data. Losing it loses every snapshot in the repository: Kopia
# derives the encryption key from it and stores nothing that can recover it.
_repository_password="$(cat /run/secrets/KOPIA_REPOSITORY_PASSWORD)"
export KOPIA_PASSWORD="$_repository_password"
unset _repository_password

# --- Server login (required for the web interface and the control API) ---
_server_password="$(cat /run/secrets/KOPIA_SERVER_PASSWORD)"
export KOPIA_SERVER_PASSWORD="$_server_password"
unset _server_password

_server_control_password="$(cat /run/secrets/KOPIA_SERVER_CONTROL_PASSWORD)"
export KOPIA_SERVER_CONTROL_PASSWORD="$_server_control_password"
unset _server_control_password

exec "$@"
