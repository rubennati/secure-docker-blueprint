#!/bin/sh
set -e

# Valkey takes its password on the command line or from a config file. Both
# are visible: the command line shows up in `docker inspect` and in the
# process list, and a config file with the password in it would have to be
# mounted from the repository. Reading the Docker Secret here and handing it
# over on the command line of the exec'd process keeps it out of the compose
# file; it is still visible to anything that can read /proc inside this
# container, which is the container's own uid alone.
#
# `--save ""` turns snapshotting off. Everything here expires on its own and
# none of it has to survive a restart, so there is nothing worth writing — and
# with nothing to write, the container needs no writable filesystem.
#
# `volatile-lru` rather than the default `noeviction`: every key HeyForm sets
# carries a TTL — sessions, e-mail verification codes, sign-in attempt counters
# and the per-form submission cooldown — and nothing else lives here, so there
# is always something eligible to drop. Full memory then signs out whoever has
# been idle longest, instead of refusing every new session and taking sign-in
# down with it.

_cache_pwd="$(cat /run/secrets/CACHE_PWD)"

exec valkey-server \
    --requirepass "$_cache_pwd" \
    --save "" \
    --appendonly no \
    --maxmemory 192mb \
    --maxmemory-policy volatile-lru \
    "$@"
