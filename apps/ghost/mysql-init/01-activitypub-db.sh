#!/bin/sh
# Creates the ActivityPub database and grants the application user access.
# Runs automatically on first MySQL initialization (empty data volume).
#
# For existing deployments, run manually once before starting ActivityPub:
#   docker compose exec db sh /docker-entrypoint-initdb.d/01-activitypub-db.sh
#
# MYSQL_ROOT_PASSWORD and MYSQL_USER are available here because the MySQL
# Docker entrypoint resolves *_FILE variables before running init scripts.
set -e

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS activitypub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON activitypub.* TO '${MYSQL_USER}'@'%';
    FLUSH PRIVILEGES;
EOSQL
