#!/bin/sh
set -e

# Vikunja has no _FILE env var support — secrets are injected here.
#
# VIKUNJA_SERVICE_SECRET  — JWT signing secret (env var per upstream docs)
# VIKUNJA_DATABASE_PASSWORD — DB password
# VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET — Authentik OIDC client secret
export VIKUNJA_SERVICE_SECRET="$(cat /run/secrets/VIKUNJA_JWT_SECRET)"
export VIKUNJA_DATABASE_PASSWORD="$(cat /run/secrets/VIKUNJA_DB_PWD)"
export VIKUNJA_AUTH_OPENID_PROVIDERS_AUTHENTIK_CLIENTSECRET="$(cat /run/secrets/VIKUNJA_OIDC_SECRET)"

exec /app/vikunja/vikunja "$@"
