#!/bin/sh
set -e

# Scrutiny reads its settings through viper with a SCRUTINY prefix — the
# variable for the InfluxDB token is SCRUTINY_WEB_INFLUXDB_TOKEN — and it has
# no _FILE variant. Left to itself it falls back to the default token baked
# into the binary and dies with `panic: unauthorized: unauthorized access`,
# which names neither the token nor the variable.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. The value goes
# through an intermediate variable so a missing secret aborts the start.

_influxdb_token="$(cat /run/secrets/INFLUXDB_TOKEN)"
export SCRUTINY_WEB_INFLUXDB_TOKEN="$_influxdb_token"
unset _influxdb_token

exec /opt/scrutiny/bin/scrutiny "$@"
