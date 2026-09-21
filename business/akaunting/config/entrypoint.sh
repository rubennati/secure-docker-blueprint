#!/bin/sh
set -e

# Replaces the image's own entrypoint, which on every start enables an Apache
# module and recursively chowns the whole webroot — both writes into the image,
# which a read-only root filesystem refuses. The module is enabled by a mounted
# file instead (rewrite.load), and ownership is already right where it matters:
# storage/ is the bind mount, bootstrap/cache/ is a tmpfs.

# Laravel reads real environment variables first; .env does not override them.
# The database password therefore comes from the Docker Secret and never has to
# be written into .env.
_db="$(cat /run/secrets/DB_PWD)"
export DB_PASSWORD="$_db"
unset _db

# The directories Laravel expects under storage/, created on the bind mount.
mkdir -p storage/framework/sessions storage/framework/views storage/framework/cache \
         storage/app/uploads storage/logs

exec "$@"
