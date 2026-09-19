#!/bin/sh
set -e

# Hemmelig has no _FILE support (verified against a live container and the
# upstream docker-compose.yml, 2026-09-19) — both secrets arrive as plain env
# vars. This wrapper reads them from Docker Secrets and exports them, then
# hands off to the image's own entrypoint, which still needs to run as root
# first (it chowns /app/database and /app/uploads, then drops to "app" via
# gosu before running Prisma migrations and starting the server).
_secret="$(cat /run/secrets/better_auth_secret)"
export BETTER_AUTH_SECRET="$_secret"
unset _secret

_secret="$(cat /run/secrets/analytics_hmac_secret)"
export HEMMELIG_ANALYTICS_HMAC_SECRET="$_secret"
unset _secret

exec /app/docker-entrypoint.sh "$@"
