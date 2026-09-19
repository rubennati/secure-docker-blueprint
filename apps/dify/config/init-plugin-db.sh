#!/bin/sh
# Runs once, on the first start of an empty data directory: the plugin daemon
# keeps its data in a second database next to the application's.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE dify_plugin OWNER \"$POSTGRES_USER\";"
