#!/usr/bin/env bash
# Creates the Frappe site and installs ERPNext into it. bench uses the database
# and user MariaDB created from the Docker Secrets, so it never needs the MariaDB
# root password.
#
# Usage: ops/create-site.sh
# Local file: COMPOSE_FILE=docker-compose.local.yml ENV_FILE=.env.local ops/create-site.sh
set -euo pipefail
cd "$(dirname "$0")/.."

env_file="${ENV_FILE:-.env}"
dc() { docker compose --env-file "$env_file" "$@"; }

if ! dc ps --status running --services | grep -qx erpnext-backend; then
  echo "the erpnext-backend service is not running — start it with 'docker compose up -d' first" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "./$env_file"
set +a

# shellcheck disable=SC2016  # expanded inside the container
if dc exec -T -e SITE_NAME="$SITE_NAME" erpnext-backend \
    sh -c 'test -e "sites/$SITE_NAME/site_config.json"'; then
  echo "already created — sites/$SITE_NAME exists. Nothing changed."
  exit 0
fi

# The passwords are read from the Docker Secrets inside the container, so they
# never pass through this shell. Frappe's command runner is called directly, as
# bench itself calls it: bench logs every command line, passwords included, to
# logs/bench.log.
dc exec -T \
  -e SITE_NAME="$SITE_NAME" -e DB_NAME="$DB_NAME" -e DB_USER="$DB_USER" -e APP_URL="$APP_URL" \
  erpnext-backend bash -s <<'EOF'
set -euo pipefail
cd sites
fc() { ../env/bin/python -m frappe.utils.bench_helper frappe "$@"; }
fc new-site "$SITE_NAME" \
  --db-name "$DB_NAME" --db-user "$DB_USER" --db-password "$(cat /run/secrets/DB_PWD)" \
  --no-setup-db \
  --admin-password "$(cat /run/secrets/ADMIN_PWD)" \
  --install-app erpnext --set-default
fc --site "$SITE_NAME" set-config host_name "$APP_URL"
EOF

echo
echo "Created $SITE_NAME. Log in as Administrator with the password in .secrets/admin_pwd.txt."
