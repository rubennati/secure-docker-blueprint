#!/bin/bash
set -e

# Read Docker Secret and export as plain env var.
# Euro-Office (OnlyOffice fork) reads JWT_SECRET from env only — no _FILE support.

[ -f /run/secrets/EURO_OFFICE_JWT_SECRET ] && \
  export JWT_SECRET="$(cat /run/secrets/EURO_OFFICE_JWT_SECRET)"

exec "$@"
