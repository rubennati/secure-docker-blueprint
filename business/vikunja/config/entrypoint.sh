#!/bin/sh
set -e

# Inject Docker Secrets into environment before starting Vikunja.
# Vikunja has no _FILE env var support — all secrets are injected here.
#
# POSIX quirk: `export VAR=$(cmd)` masks cmd's exit status (export is a
# special builtin). Use intermediate variables so `set -e` correctly aborts
# the container if a secret file is missing or unreadable.
_jwt="$(cat /run/secrets/VIKUNJA_JWT_SECRET)"
_pwd="$(cat /run/secrets/VIKUNJA_DB_PWD)"
export VIKUNJA_SERVICE_SECRET="$_jwt"
export VIKUNJA_DATABASE_PASSWORD="$_pwd"
unset _jwt _pwd

# Only inject OIDC client secret when OIDC is actually enabled.
# The secret file still exists when OIDC is disabled (placeholder) — ignore it.
if [ "${VIKUNJA_AUTH_OPENID_ENABLED:-false}" = "true" ]; then
  _oidc="$(cat /run/secrets/VIKUNJA_OIDC_SECRET)"
  export VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET="$_oidc"
  unset _oidc
fi

exec /app/vikunja/vikunja "$@"
