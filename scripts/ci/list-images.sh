#!/usr/bin/env bash
# list-images.sh — extract resolved image:tag references from compose files.
#
# For each compose file in the provided list, sources the sibling .env.example
# then uses envsubst to resolve ${VAR} references in image: lines.
#
# Output: one image:tag per line, deduplicated, sorted.
# Usage:  scripts/ci/list-images.sh [compose-file ...]
#         (defaults to a curated high-priority list if no arguments given)
#
# Limitation: only images whose tags are defined in the sibling .env.example
# are emitted. Images using compose-level variable overrides, profiles, or
# build: blocks may be skipped or misresolved.

set -uo pipefail

command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst not found (install gettext-base)"; exit 1; }

COMPOSE_FILES=("$@")

# Default: curated list of high-risk compose files.
# These cover public-facing services and services holding sensitive data.
# Add entries here when a new high-risk service is added to the blueprint.
if [ "${#COMPOSE_FILES[@]}" -eq 0 ]; then
  COMPOSE_FILES=(
    core/traefik/docker-compose.yml
    core/authentik/docker-compose.yml
    core/crowdsec/docker-compose.yml
    apps/vaultwarden/docker-compose.yml
    apps/nextcloud/docker-compose.yml
    apps/immich/docker-compose.yml
    apps/paperless-ngx/docker-compose.yml
    apps/seafile/seafile-server.yml
    apps/wordpress/docker-compose.yml
    business/zammad/docker-compose.yml
    monitoring/uptime-kuma/docker-compose.yml
  )
fi

for compose in "${COMPOSE_FILES[@]}"; do
  [ -f "$compose" ] || continue
  dir=$(dirname "$compose")
  env_file="$dir/.env.example"

  # Source .env.example so envsubst can resolve ${VAR} references.
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file" 2>/dev/null || true
    set +a
  fi

  # Extract image: lines, resolve variables, filter unresolved/empty/local.
  # grep returns 1 on no match — that is normal, not an error here.
  { grep -E '^\s+image:' "$compose" 2>/dev/null || true; } \
  | grep -v '^\s*#' \
  | sed 's/.*image:\s*//' | sed "s/['\"]//g" | tr -d ' ' \
  | envsubst \
  | while IFS= read -r image; do
      [[ -z "$image" ]]       && continue   # empty
      [[ "$image" == *'$'* ]] && continue   # unresolved variable
      [[ "$image" == "."* ]]  && continue   # local build context
      echo "$image"
    done

done | sort -u
