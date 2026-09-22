#!/usr/bin/env bash
# Installs Akaunting without the web installer, then removes the database
# password from .env.
#
# Until this has run, the web installer is reachable and asks for nothing but a
# database. The shipped access policy keeps the router VPN-only for that reason.
#
# Usage: ops/install.sh <admin-email> <company-name> <company-email> [locale]
set -euo pipefail
cd "$(dirname "$0")/.."

admin_email="${1:-}"
company_name="${2:-}"
company_email="${3:-}"
locale="${4:-en-GB}"
if [ -z "$admin_email" ] || [ -z "$company_name" ] || [ -z "$company_email" ]; then
  echo "usage: ops/install.sh <admin-email> <company-name> <company-email> [locale]" >&2
  exit 1
fi

if ! docker compose ps --status running --services | grep -qx akaunting-app; then
  echo "the akaunting-app service is not running — start it with 'docker compose up -d' first" >&2
  exit 1
fi

# volumes/app.env belongs to www-data with mode 600, so it is read inside the
# container. The guard matters: the installer writes a new APP_KEY on every run,
# and a second run would make everything encrypted with the old key unreadable.
installed=$(docker compose exec -T --user www-data akaunting-app \
  sh -c 'grep -c "^APP_INSTALLED=true" .env || true')
case "$installed" in
  0) ;;
  "")
    echo "cannot read .env inside the container — nothing changed" >&2
    exit 1
    ;;
  *)
    echo "already installed — .env has APP_INSTALLED=true. Nothing changed."
    exit 0
    ;;
esac

set -a
# shellcheck disable=SC1091
. ./.env
set +a

# The passwords are read inside the container, from the Docker Secrets, so they
# never pass through this shell. They are arguments to the installer for the
# few seconds it runs.
docker compose exec -T --user www-data \
  -e ADMIN_EMAIL="$admin_email" -e COMPANY_NAME="$company_name" \
  -e COMPANY_EMAIL="$company_email" -e LOCALE="$locale" \
  akaunting-app sh -c '
    php artisan install \
      --db-host=db --db-port=3306 \
      --db-name="$DB_DATABASE" --db-username="$DB_USERNAME" \
      --db-password="$(cat /run/secrets/DB_PWD)" --db-prefix="$DB_PREFIX" \
      --company-name="$COMPANY_NAME" --company-email="$COMPANY_EMAIL" \
      --admin-email="$ADMIN_EMAIL" --admin-password="$(cat /run/secrets/ADMIN_PWD)" \
      --locale="$LOCALE" --no-interaction'

# The installer writes the database password into .env. Laravel reads real
# environment variables first, and the container already has it from the
# secret — so the copy in the file is removed. Inside the container, as the
# file's owner, and rewritten in place: the file is a bind mount.
docker compose exec -T --user www-data akaunting-app sh -c '
  grep -v "^DB_PASSWORD=" .env > /tmp/app.env && cat /tmp/app.env > .env && rm -f /tmp/app.env'
if [ "$(docker compose exec -T --user www-data akaunting-app sh -c 'grep -c "^DB_PASSWORD=" .env || true')" != 0 ]; then
  echo "the database password is still in .env — remove the DB_PASSWORD line from volumes/app.env" >&2
  exit 1
fi

docker compose restart akaunting-app >/dev/null

echo
echo "Installed. Log in as $admin_email with the password in .secrets/admin_pwd.txt."
echo "The web installer now redirects to the login page."
