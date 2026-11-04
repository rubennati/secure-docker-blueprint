#!/bin/bash
set -e

# Read Docker Secret and export as plain env var.
# Euro-Office (OnlyOffice fork) reads JWT_SECRET from env only — no _FILE support.

[ -f /run/secrets/EURO_OFFICE_JWT_SECRET ] && \
  export JWT_SECRET="$(cat /run/secrets/EURO_OFFICE_JWT_SECRET)"

# The log volume hides the directories the image creates under /var/log/euro-office;
# nginx and the services do not create them, and nginx failed to start without them.
mkdir -p /var/log/euro-office/documentserver/docservice /var/log/euro-office/documentserver/converter \
         /var/log/euro-office/documentserver/metrics /var/log/euro-office/documentserver/adminpanel
exec "$@"
