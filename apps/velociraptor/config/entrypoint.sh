#!/bin/sh
set -e

# No _FILE support (verified: absent from upstream's own entrypoint script)
# — VELOCIRAPTOR_INITIAL_ADMIN_PASSWORD is a plain env var, read only on
# the very first start (when no config file exists yet; every later start
# reuses the existing one and ignores this entirely). Injected from a
# Docker Secret here for the one boot where it actually matters.
_pwd="$(cat /run/secrets/admin_password)"
export VELOCIRAPTOR_INITIAL_ADMIN_PASSWORD="$_pwd"
unset _pwd

# /bin/entrypoint is not itself marked executable — upstream's own image
# CMD invokes it as `sh /bin/entrypoint`, not directly. Verified against a
# live container: exec'ing it directly fails with "Permission denied".
exec /bin/sh /bin/entrypoint "$@"
