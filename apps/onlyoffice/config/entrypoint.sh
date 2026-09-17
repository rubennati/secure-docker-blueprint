#!/bin/bash
set -e

# Read Docker Secret and export as plain env var.
# OnlyOffice reads JWT_SECRET from env only — no _FILE support.

[ -f /run/secrets/ONLYOFFICE_JWT_SECRET ] && \
  export JWT_SECRET="$(cat /run/secrets/ONLYOFFICE_JWT_SECRET)"

exec "$@"
