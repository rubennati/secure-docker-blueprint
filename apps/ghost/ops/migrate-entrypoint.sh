#!/bin/sh
# Reads the DB password from the Docker Secret and runs the ActivityPub migrations.
set -e

MYSQL_PASSWORD="$(cat /run/secrets/DB_PWD)"

exec migrate \
  -path /migrations \
  -database "mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@tcp(${MYSQL_HOST}:3306)/${MYSQL_DATABASE}" \
  up
