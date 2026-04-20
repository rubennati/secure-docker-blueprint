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
# into /mnt/* and invokes this script as its entrypoint.

set -eu

AK_UID=1000
AK_GID=1000

log() { printf '[authentik-init] %s\n' "$*"; }

log "Ensuring directories exist..."
mkdir -p /mnt/data /mnt/certs /mnt/custom-templates

log "Setting ownership to ${AK_UID}:${AK_GID}..."
chown -R "${AK_UID}:${AK_GID}" /mnt/data /mnt/certs /mnt/custom-templates

log "Setting permissions..."
chmod ug+rwx /mnt/data
chmod ug+rx  /mnt/certs /mnt/custom-templates

log "Done."
