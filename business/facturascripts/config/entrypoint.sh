#!/bin/sh
set -e

# Replaces the image's start script, which copies the code into the webroot and
# then runs chmod -R o+w over all of it. This one copies the code once, as
# www-data, and leaves the permissions as the copy makes them. After that, the
# code in the webroot belongs to FacturaScripts' own updater.
#
# The check runs as www-data as well: the webroot is www-data's with mode 700,
# and root without DAC capabilities cannot see into it.
setpriv --reuid=www-data --regid=www-data --init-groups sh -c \
  '[ -e /var/www/html/index.php ] || cp -R /usr/src/facturascripts/. /var/www/html/'

exec "$@"
