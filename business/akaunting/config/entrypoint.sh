#!/bin/sh
set -e

# Replaces the image's own entrypoint, which on every start enables an Apache
# module, unpacks the application into the webroot only if it is missing, and
# recursively chowns the whole webroot — writes a read-only root filesystem
# refuses, and a webroot that keeps old code across image changes. The module is
# enabled by a mounted file instead (rewrite.load).

# The image carries the application as /tmp/akaunting.zip; the webroot is a
# tmpfs, so the code is unpacked from the pinned image on every start. As root,
# so www-data can read it but not change it. storage/ is a bind mount and
# bootstrap/cache/ its own tmpfs: neither is taken from the archive.
if [ ! -f /var/www/html/index.php ]; then
  unzip -q /tmp/akaunting.zip -d /var/www/html -x 'storage/*' 'bootstrap/cache/*'
fi

# Laravel reads real environment variables first; .env does not override them.
# The database password therefore comes from the Docker Secret and never has to
# be written into .env.
_db="$(cat /run/secrets/DB_PWD)"
export DB_PASSWORD="$_db"
unset _db

# The directories Laravel expects under storage/, created on the bind mount —
# as www-data. This script runs as root, but without CAP_DAC_OVERRIDE root
# cannot enter storage/, which belongs to www-data with mode 700.
setpriv --reuid=www-data --regid=www-data --clear-groups \
  mkdir -p storage/framework/sessions storage/framework/views storage/framework/cache \
           storage/app/uploads storage/logs

exec "$@"
