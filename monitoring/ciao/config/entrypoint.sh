#!/bin/sh
set -e

# ciao reads every secret from the environment and has no _FILE variant, so the
# values are exported here from Docker Secrets and the image's own command runs
# after them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string.

# --- Session signing key (required) ---
# Left unset, start.sh generates a new one on every start, which invalidates
# every session and every signed cookie the previous start handed out.
_secret_key_base="$(cat /run/secrets/CIAO_SECRET_KEY_BASE)"
export SECRET_KEY_BASE="$_secret_key_base"
unset _secret_key_base

# --- HTTP basic auth (required as shipped) ---
# BASIC_AUTH_USERNAME comes from the environment; without the pair, ciao serves
# its interface and its REST API to anyone who reaches the port.
if [ -s /run/secrets/CIAO_BASIC_AUTH_PASSWORD ]; then
    _basic_auth_password="$(cat /run/secrets/CIAO_BASIC_AUTH_PASSWORD)"
    export BASIC_AUTH_PASSWORD="$_basic_auth_password"
    unset _basic_auth_password
fi

# --- Prometheus endpoint (optional) ---
# /metrics sits outside the application's basic auth and carries its own pair.
if [ -s /run/secrets/CIAO_PROMETHEUS_PASSWORD ]; then
    _prometheus_password="$(cat /run/secrets/CIAO_PROMETHEUS_PASSWORD)"
    export PROMETHEUS_BASIC_AUTH_PASSWORD="$_prometheus_password"
    unset _prometheus_password
fi

# --- SMTP (optional) ---
if [ -s /run/secrets/CIAO_SMTP_PASSWORD ]; then
    _smtp_password="$(cat /run/secrets/CIAO_SMTP_PASSWORD)"
    export SMTP_PASSWORD="$_smtp_password"
    unset _smtp_password
fi

exec "$@"
