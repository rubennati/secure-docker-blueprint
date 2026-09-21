#!/usr/bin/env bash
# Installs FacturaScripts through upstream's own installer, unattended, then
# takes both passwords back out of config.php.
#
# Until this has run, the web installer is reachable and asks for nothing but a
# database. The shipped access policy keeps the router VPN-only for that reason.
#
# Usage: ops/install.sh <admin-username>
set -euo pipefail
cd "$(dirname "$0")/.."

admin_user="${1:-}"
if [ -z "$admin_user" ]; then
  echo "usage: ops/install.sh <admin-username>" >&2
  exit 1
fi

if ! docker compose ps --status running --services | grep -qx facturascripts-app; then
  echo "the facturascripts-app service is not running — start it with 'docker compose up -d' first" >&2
  exit 1
fi

if docker compose exec -T --user www-data facturascripts-app test -e /var/www/html/config.php; then
  echo "already installed — config.php exists. Nothing changed."
  exit 0
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

# The passwords are read from the Docker Secrets inside the container, so they
# never pass through this shell. mysql_socket is sent empty, as the web form
# sends it: without the field the installer stops halfway through config.php.
result="$(docker compose exec -T --user www-data \
  -e DB_NAME="$DB_NAME" -e DB_USER="$DB_USER" \
  -e ADMIN_USER="$admin_user" -e APP_LANG="$APP_LANG" \
  facturascripts-app sh -s <<'EOF'
curl -sS -X POST http://127.0.0.1/ \
  -d unattended=1 -d fs_db_type=mysql -d fs_db_host=db -d fs_db_port=3306 \
  -d mysql_socket= \
  --data-urlencode "fs_db_name=$DB_NAME" \
  --data-urlencode "fs_db_user=$DB_USER" \
  --data-urlencode "fs_db_pass@/run/secrets/DB_PWD" \
  --data-urlencode "fs_initial_user=$ADMIN_USER" \
  --data-urlencode "fs_initial_pass@/run/secrets/ADMIN_PWD" \
  --data-urlencode "fs_lang=$APP_LANG" \
  --data-urlencode "fs_timezone=$TZ"
EOF
)"
if [ "$result" != "OK" ]; then
  echo "the installer did not finish:" >&2
  printf '%s\n' "$result" | sed -e 's/<[^>]*>//g' | grep -v '^[[:space:]]*$' | head -20 >&2
  exit 1
fi

# The first request after the install creates the tables and the administrator,
# from FS_INITIAL_USER and FS_INITIAL_PASS in config.php.
docker compose exec -T facturascripts-app curl -fsS -o /dev/null http://127.0.0.1/login

# The installer writes the database password and the administrator's password
# into config.php. The first becomes a read of the Docker Secret; the second is
# not needed once the account exists.
docker compose exec -T --user www-data facturascripts-app sh -s <<'EOF'
sed -i \
  -e "s|^define('FS_DB_PASS', .*|define('FS_DB_PASS', trim((string) file_get_contents('/run/secrets/DB_PWD')));|" \
  -e "/^define('FS_INITIAL_USER'/d" \
  -e "/^define('FS_INITIAL_PASS'/d" \
  /var/www/html/config.php
EOF

echo
echo "Installed. Log in as $admin_user with the password in .secrets/admin_pwd.txt."
echo "The web installer is closed: config.php exists."
