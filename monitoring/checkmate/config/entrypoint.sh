#!/bin/sh
set -e

# Checkmate reads every setting from the environment and has no _FILE variant,
# so the three that are credentials are exported here from Docker Secrets and
# the image's own entrypoint runs after them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string, which the application would then
# reject with a validation error that names the variable but not the cause.

# --- MongoDB connection string (required) ---
# Carries the user and password inline, which is why the whole URL is the
# secret rather than the password alone.
_db_connection_string="$(cat /run/secrets/DB_CONNECTION_STRING)"
export DB_CONNECTION_STRING="$_db_connection_string"
unset _db_connection_string

# --- JWT signing key (required) ---
# Every session token is signed with this. Changing it signs everyone out.
_jwt_secret="$(cat /run/secrets/JWT_SECRET)"
export JWT_SECRET="$_jwt_secret"
unset _jwt_secret

# --- Encryption key (optional) ---
# Encrypts stored Docker TLS client keys. Only monitors that reach a Docker
# daemon over TLS need it, so the file is allowed to be absent.
if [ -f /run/secrets/ENCRYPTION_KEY ]; then
    _encryption_key="$(cat /run/secrets/ENCRYPTION_KEY)"
    export ENCRYPTION_KEY="$_encryption_key"
    unset _encryption_key
fi

exec docker-entrypoint.sh "$@"
