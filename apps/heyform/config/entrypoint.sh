#!/bin/sh
set -e

# HeyForm reads every setting from the environment and has no _FILE variant,
# so the credentials are exported here from Docker Secrets and the image's own
# entrypoint runs after them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string, which the application would then treat
# as "not configured" and carry on with.

# --- MongoDB connection URL (required) ---
# Carries the user and password inline, which is why the whole URL is the
# secret rather than the password alone.
_mongo_uri="$(cat /run/secrets/MONGO_URI)"
export MONGO_URI="$_mongo_uri"
unset _mongo_uri

# --- Session signing key (required) ---
# Signs the session cookie. Changing it signs everyone out.
_session_key="$(cat /run/secrets/SESSION_KEY)"
export SESSION_KEY="$_session_key"
unset _session_key

# --- Form encryption key (required) ---
# Encrypts form-level passwords and the hidden-field payloads carried in a
# form URL. Changing it after forms exist makes those unreadable.
_form_encryption_key="$(cat /run/secrets/FORM_ENCRYPTION_KEY)"
export FORM_ENCRYPTION_KEY="$_form_encryption_key"
unset _form_encryption_key

# --- Valkey password (required) ---
_cache_pwd="$(cat /run/secrets/CACHE_PWD)"
export REDIS_PASSWORD="$_cache_pwd"
unset _cache_pwd

# --- SMTP password (optional) ---
# An instance without outgoing mail has no password to hand over. The file is
# allowed to be absent or empty; an empty value is left unset so the mail
# library does not offer an empty credential to a server that wants none.
if [ -s /run/secrets/SMTP_PWD ]; then
    _smtp_pwd="$(cat /run/secrets/SMTP_PWD)"
    export SMTP_PASSWORD="$_smtp_pwd"
    unset _smtp_pwd
fi

exec docker-entrypoint.sh "$@"
