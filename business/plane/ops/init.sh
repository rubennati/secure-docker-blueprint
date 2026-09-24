#!/usr/bin/env bash
# Generates the secrets and prepares the data directories. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."

for f in secret_key live_server_secret_key database_url postgres_password \
         amqp_url rabbitmq_password aws_access_key_id aws_secret_access_key; do
  if [ -e ".secrets/$f.txt" ]; then
    echo "refusing: .secrets/$f.txt exists" >&2
    exit 1
  fi
done

# The URLs are assembled from these, so they have to match .env.
DB_NAME="$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2- || true)"
DB_USER="$(grep -E '^DB_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
MQ_USER="$(grep -E '^MQ_USER=' .env 2>/dev/null | cut -d= -f2- || true)"
MQ_VHOST="$(grep -E '^MQ_VHOST=' .env 2>/dev/null | cut -d= -f2- || true)"
: "${DB_NAME:=plane}"; : "${DB_USER:=plane}"
: "${MQ_USER:=plane}"; : "${MQ_VHOST:=plane}"

umask 077
mkdir -p .secrets

# Hex throughout: no character that would need URL-encoding inside a URL.
PG_PWD="$(openssl rand -hex 24)"
printf '%s' "$PG_PWD" > .secrets/postgres_password.txt
printf 'postgresql://%s:%s@plane-db/%s' "$DB_USER" "$PG_PWD" "$DB_NAME" > .secrets/database_url.txt
unset PG_PWD

MQ_PWD="$(openssl rand -hex 24)"
printf '%s' "$MQ_PWD" > .secrets/rabbitmq_password.txt
printf 'amqp://%s:%s@plane-mq:5672/%s' "$MQ_USER" "$MQ_PWD" "$MQ_VHOST" > .secrets/amqp_url.txt
unset MQ_PWD

# Django's signing key, and the key the API and the live server share.
openssl rand -hex 32 | tr -d '\n' > .secrets/secret_key.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/live_server_secret_key.txt

# MinIO. Upstream's defaults are literally `access-key` and `secret-key`.
openssl rand -hex 12 | tr -d '\n' > .secrets/aws_access_key_id.txt
openssl rand -hex 32 | tr -d '\n' > .secrets/aws_secret_access_key.txt

# Many containers with different uids read these through bind mounts.
chmod 644 .secrets/*.txt
chmod 700 .secrets

mkdir -p volumes/postgres volumes/redis volumes/rabbitmq volumes/uploads \
         volumes/logs volumes/proxy-config volumes/proxy-data

echo "Created eight secrets in .secrets/"
echo
echo "Next:"
echo "  sudo chown -R 1000:1000 volumes/redis volumes/uploads volumes/logs"
echo "  docker compose up -d       # the migrator runs first and takes a while"
echo
echo "Then open https://<your host>/god-mode and claim the instance."
echo "The FIRST visitor to that path becomes the administrator, and sign-up is"
echo "open until you close it there. Do it before anyone else can reach the"
echo "host name — see README, 'Claim /god-mode first'."
