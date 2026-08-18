#!/usr/bin/env bash
# list-images.sh — extract resolved image:tag references from compose files.
#
# Output: one image:tag per line, deduplicated, sorted.
# Usage:  scripts/ci/list-images.sh [compose-file ...]
#         With no arguments it takes every compose file
#         `scripts/ci/check-structure.py --list` reports.
#
# Resolution order per file: source the sibling .env.example, then envsubst for
# ${VAR}, then sed for ${VAR:-default}. That sed takes the inline default even
# when .env.example sets the variable.
#
# Not emitted: locally built images (*-local:*), and images whose tag resolves
# from neither the sibling .env.example nor an inline default.

set -uo pipefail

command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst not found (install gettext-base)"; exit 1; }

COMPOSE_FILES=("$@")

if [ "$#" -eq 0 ]; then
  # One discovery for the whole repository — see scripts/ci/check-structure.py.
  # Read with a loop rather than mapfile: bash 3.2 ships without it, and this
  # script is run by hand on developer machines as well as in CI.
  COMPOSE_FILES=()
  while IFS= read -r line; do
    COMPOSE_FILES+=("$line")
  done < <(python3 "$(dirname "$0")/check-structure.py" --list)
fi

if [ "${#COMPOSE_FILES[@]}" -eq 0 ]; then
  echo "ERROR: no compose files discovered" >&2
  exit 1
fi

for compose in "${COMPOSE_FILES[@]}"; do
  [ -f "$compose" ] || continue
  dir=$(dirname "$compose")
  env_file="$dir/.env.example"

  # Source .env.example so envsubst can resolve ${VAR} references. Done in a
  # subshell per file so one stack's variables cannot leak into the next and
  # silently resolve a tag to the wrong version.
  (
    if [ -f "$env_file" ]; then
      set -a
      # shellcheck source=/dev/null
      source "$env_file" 2>/dev/null || true
      set +a
    fi

    # grep returns 1 on no match — normal here, not an error.
    { grep -E '^[[:space:]]+image:' "$compose" 2>/dev/null || true; } \
    | grep -v '^[[:space:]]*#' \
    | sed 's/.*image:[[:space:]]*//' | sed "s/['\"]//g" | tr -d ' ' \
    | envsubst \
    | sed 's/\${[A-Za-z0-9_]*:-\([^}]*\)}/\1/g' \
    | while IFS= read -r image; do
        [[ -z "$image" ]]        && continue   # empty
        [[ "$image" == *'$'* ]]  && continue   # unresolved variable
        [[ "$image" == "."* ]]   && continue   # local build context
        # Locally built images are never in a registry — business/vikunja builds
        # vikunja-local from its own Dockerfile. Trivy would fail to pull them.
        [[ "$image" == *-local:* ]] && continue
        echo "$image"
      done
  )
done | sort -u
