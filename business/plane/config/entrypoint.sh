#!/bin/sh
set -e

# Plane reads every setting from the environment and has no _FILE variant for
# any of them. The same wrapper is mounted into all four backend services and
# into the live server; each keeps its own command.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start.

# --- Django's signing key (required) ---
# Sessions, password-reset links and anything else signed. Changing it signs
# everyone out.
if [ -f /run/secrets/SECRET_KEY ]; then
    _secret_key="$(cat /run/secrets/SECRET_KEY)"
    export SECRET_KEY="$_secret_key"
    unset _secret_key
fi

# --- The live server's shared key (required) ---
# The API and the live server authenticate to each other with it.
if [ -f /run/secrets/LIVE_SERVER_SECRET_KEY ]; then
    _live_key="$(cat /run/secrets/LIVE_SERVER_SECRET_KEY)"
    export LIVE_SERVER_SECRET_KEY="$_live_key"
    unset _live_key
fi

# --- PostgreSQL (required) ---
# The URL carries the password inline, which is why the whole URL is the
# secret. POSTGRES_PASSWORD is set as well: parts of the backend read it
# directly rather than parsing the URL.
if [ -f /run/secrets/DATABASE_URL ]; then
    _database_url="$(cat /run/secrets/DATABASE_URL)"
    export DATABASE_URL="$_database_url"
    unset _database_url
fi
if [ -f /run/secrets/POSTGRES_PASSWORD ]; then
    _pg_password="$(cat /run/secrets/POSTGRES_PASSWORD)"
    export POSTGRES_PASSWORD="$_pg_password"
    unset _pg_password
fi

# --- RabbitMQ (required) ---
if [ -f /run/secrets/AMQP_URL ]; then
    _amqp_url="$(cat /run/secrets/AMQP_URL)"
    export AMQP_URL="$_amqp_url"
    unset _amqp_url
fi

# --- MinIO / S3 (required) ---
# Upstream's defaults are literally `access-key` and `secret-key`.
if [ -f /run/secrets/AWS_ACCESS_KEY_ID ]; then
    _aws_key_id="$(cat /run/secrets/AWS_ACCESS_KEY_ID)"
    export AWS_ACCESS_KEY_ID="$_aws_key_id"
    unset _aws_key_id
fi
if [ -f /run/secrets/AWS_SECRET_ACCESS_KEY ]; then
    _aws_secret="$(cat /run/secrets/AWS_SECRET_ACCESS_KEY)"
    export AWS_SECRET_ACCESS_KEY="$_aws_secret"
    unset _aws_secret
fi

exec "$@"
