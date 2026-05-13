#!/bin/sh
set -e

# Inject Docker Secrets into environment before starting Vikunja.
# Vikunja has no _FILE env var support — all secrets are injected here.
#
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status (export is a
# special builtin). Use intermediate variables so `set -e` correctly aborts
# the container if a secret file is missing or unreadable.
_jwt="$(cat /run/secrets/jwt_key)"
_pwd="$(cat /run/secrets/db_pwd)"
export VIKUNJA_SERVICE_SECRET="$_jwt"
export VIKUNJA_DATABASE_PASSWORD="$_pwd"
unset _jwt _pwd

# Only inject OIDC client secret when OIDC is actually enabled.
# The secret file still exists when OIDC is disabled (placeholder) — ignore it.
if [ "${VIKUNJA_AUTH_OPENID_ENABLED:-false}" = "true" ]; then
  _oidc="$(cat /run/secrets/oidc_secret)"
  export VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET="$_oidc"
  unset _oidc
fi

# Only inject SMTP password when mailer is enabled.
# smtp_pwd.txt exists as placeholder when mailer is disabled — safe to ignore.
if [ "${VIKUNJA_MAILER_ENABLED:-false}" = "true" ]; then
  _smtp="$(cat /run/secrets/smtp_pwd)"
  export VIKUNJA_MAILER_PASSWORD="$_smtp"
  unset _smtp
fi

exec /app/vikunja/vikunja "$@"
