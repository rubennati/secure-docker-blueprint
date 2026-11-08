#!/bin/sh
#
# Authentik volume init — idempotent, POSIX sh.
#
# Runs inside a short-lived Alpine init container as root. Creates the
# bind-mount subdirectories Authentik expects and sets ownership to
# UID/GID 1000, which is the fixed user the goauthentik/server image
# runs as (it refuses to self-fix permissions when non-root).
#
# Upstream guidance:
#   https://docs.goauthentik.io/troubleshooting/image_upload/
#
# The init-perms service in docker-compose.yml mounts the host's
# ./volumes/data, ./volumes/certs, and ./volumes/custom-templates
# into /mnt/* and invokes this script as its entrypoint. It also mounts
# ./volumes/redis, which belongs to the redis image's own user (999:1000):
# Redis starts as that user and has no capability to fix it itself.

set -eu

AK_UID=1000
AK_GID=1000
REDIS_UID=999
REDIS_GID=1000

log() { printf '[authentik-init] %s\n' "$*"; }

log "Ensuring directories exist..."
mkdir -p /mnt/data /mnt/certs /mnt/custom-templates /mnt/redis

log "Setting ownership to ${AK_UID}:${AK_GID}..."
chown -R "${AK_UID}:${AK_GID}" /mnt/data /mnt/certs /mnt/custom-templates
chown -R "${REDIS_UID}:${REDIS_GID}" /mnt/redis

log "Setting permissions..."
chmod ug+rwx /mnt/data
chmod ug+rx  /mnt/certs /mnt/custom-templates

log "Done."
