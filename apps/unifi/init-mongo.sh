#!/bin/bash
# -----------------------------------------------------------------------------
# UniFi MongoDB bootstrap
# -----------------------------------------------------------------------------
# Runs ONCE when the mongo data volume is empty. Creates the application user
# used by the UniFi Network Application. The MongoDB root credentials come
# from MONGO_INITDB_ROOT_* and are not created here.
#
# Secrets:
#   - /run/secrets/DB_ROOT_PWD   → root password (also used by Mongo itself)
#   - /run/secrets/DB_APP_PWD    → application user password
# Environment:
#   - UNIFI_APP_USER   → application username (e.g. "unifi-app")
#   - UNIFI_APP_DB     → primary database name (e.g. "unifi")
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_PWD="$(cat /run/secrets/DB_ROOT_PWD)"
APP_PWD="$(cat /run/secrets/DB_APP_PWD)"

mongo --quiet <<EOF
use admin
db.auth("${MONGO_INITDB_ROOT_USERNAME}", "${ROOT_PWD}")

use ${UNIFI_APP_DB}
db.createUser({
  user: "${UNIFI_APP_USER}",
  pwd: "${APP_PWD}",
  roles: [
    { db: "${UNIFI_APP_DB}", role: "dbOwner" },
    { db: "${UNIFI_APP_DB}_stat", role: "dbOwner" }
  ]
})
EOF
