#!/bin/sh
# Creates the ActivityPub database and grants the Ghost DB user access.
# This script runs automatically on first MySQL initialisation (empty data dir).
# For existing deployments run it manually:
#   docker exec -i ghost-db sh /docker-entrypoint-initdb.d/01-activitypub-db.sh
mysql -u root -p"$(cat /run/secrets/DB_ROOT_PWD)" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS activitypub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON activitypub.* TO '${MYSQL_USER}'@'%';
    FLUSH PRIVILEGES;
EOSQL
