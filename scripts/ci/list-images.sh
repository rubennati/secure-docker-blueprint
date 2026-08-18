#!/usr/bin/env bash
# list-images.sh — extract resolved image:tag references from compose files.
#
# For each compose file, sources the sibling .env.example then uses envsubst to
# resolve ${VAR} references in image: lines.
#
# Output: one image:tag per line, deduplicated, sorted.
# Usage:  scripts/ci/list-images.sh [compose-file ...]
#         With no arguments it takes every compose file the checkers see, via
#         `check-structure.py --list`.
#
# The default used to be eleven hand-listed paths, which resolved to 28 of the
# tree's 97 image references — no database image, no monitoring image, and
# nothing from apps/seafile-pro. A stack added afterwards stayed unscanned until
# someone remembered to edit this file. Discovery now comes from the same place
# check-baseline.py and the two shell jobs in ci.yml use, so a new stack is
# covered the moment it exists.
#
# envsubst does not understand ${VAR:-default}; the sed after it substitutes the
# default. Without that, two apps/seafile-pro images were dropped without a word —
# the exact failure this rewrite exists to remove.
#
# That sed takes the inline default even when .env.example sets the variable,
# which is the opposite of what compose does. It holds today because neither of
# the two references using that form has the variable set — checked, not assumed.
# Set one and this script would scan the wrong tag silently. Resolving it properly
# means reading the variable per occurrence rather than a blanket substitution.
#
# Limitation: only images whose tags resolve from the sibling .env.example or from
# an inline default are emitted. A compose-level override or a build: block may be
# skipped.

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
