#!/bin/sh
# The image upstream recommends — invoiceninja-debian — starts through
# /usr/local/bin/init.sh, which reads plain environment variables and has no
# _FILE handling. (The alpine branch does, but upstream no longer updates it.)
#
# So read the secrets here and export them as the variables Laravel expects,
# then hand over to the image's own entrypoint unchanged.
set -e

secret() {
  # secret VAR /run/secrets/NAME
  [ -f "$2" ] || return 0
  export "$1"
  eval "$1=\$(cat \"\$2\")"
}

secret DB_PASSWORD    /run/secrets/DB_PWD
secret APP_KEY        /run/secrets/APP_KEY
secret REDIS_PASSWORD /run/secrets/REDIS_PWD
secret MAIL_PASSWORD  /run/secrets/MAIL_PWD

# Only read on the very first start, to create the initial account.
secret IN_PASSWORD    /run/secrets/IN_PWD

# init.sh branches on the exact command it is given, so pass it through as-is.
exec /usr/local/bin/init.sh "$@"
