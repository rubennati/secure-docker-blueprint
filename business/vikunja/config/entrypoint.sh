#!/bin/sh
set -e

# Vikunja has no _FILE env var support — secrets are injected here.
#
# VIKUNJA_SERVICE_SECRET    — JWT signing secret (env var per upstream docs)
# VIKUNJA_DATABASE_PASSWORD — DB password
# VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET — only when OIDC is enabled
export VIKUNJA_SERVICE_SECRET="$(cat /run/secrets/VIKUNJA_JWT_SECRET)"
export VIKUNJA_DATABASE_PASSWORD="$(cat /run/secrets/VIKUNJA_DB_PWD)"

# Only inject OIDC client secret when OIDC is actually enabled.
# When VIKUNJA_AUTH_OPENID_ENABLED=false the secret file still exists but is ignored.
if [ "${VIKUNJA_AUTH_OPENID_ENABLED:-false}" = "true" ]; then
  export VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET="$(cat /run/secrets/VIKUNJA_OIDC_SECRET)"
fi

exec /app/vikunja/vikunja "$@"
