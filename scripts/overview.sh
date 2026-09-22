#!/usr/bin/env bash
set -euo pipefail

# =============================================
# Secure Docker Blueprint – Service Overview
# =============================================
# Scans all components and prints a summary
# table from .env (or .env.example as fallback).
# =============================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

# Collect rows: name|domain|port|type|source
rows=()

scan_component() {
  local dir="$1"
  local type="$2"

  # Prefer .env, fall back to .env.example
  local env_file=""
  local source_label=""
  if [ -f "${dir}/.env" ]; then
    env_file="${dir}/.env"
    source_label="live"
  elif [ -f "${dir}/.env.example" ]; then
    env_file="${dir}/.env.example"
    source_label="example"
  else
    # A stack with no env file of either kind — host-installed, or not yet
        # configured. Bare `return` would inherit the failed test's status and, under
        # `set -e`, end the whole survey at the first such stack.
        return 0
  fi

  local name
  name="$(basename "$dir")"

  # Read values from env file (without exporting into current shell)
  local domain="" port="" project=""

  domain="$(grep -E '^APP_TRAEFIK_HOST=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"
  project="$(grep -E '^COMPOSE_PROJECT_NAME=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"

  # The container-internal port is a property of the image, so it is a literal in
  # the Traefik label rather than a variable in the env file. Anchor on the
  # unsuffixed service name: overlays add further routers on their own ports
  # (ghost's activitypub, seafile's seadoc), and those are not the app's port.
  port="$(grep -hoE 'services\.\$\{COMPOSE_PROJECT_NAME\}\.loadbalancer\.server\.port=[0-9]+' \
          "${dir}"/*.yml 2>/dev/null | head -1 | cut -d= -f2 || true)"

  # Traefik special case
  if [ -z "$domain" ]; then
    domain="$(grep -E '^TRAEFIK_DASHBOARD_HOST=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"
  fi
  if [ -z "$port" ]; then
    port="$(grep -E '^TRAEFIK_HTTPS_PORT=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"
  fi

  [ -z "$domain" ] && domain="-"
  [ -z "$port" ] && port="-"
  [ -z "$project" ] && project="$name"

  rows+=("${project}|${domain}|${port}|${type}|${source_label}")
}

# Scan all component directories
for category in "core:core" "apps:app" "monitoring:mon"; do
  dir_name="${category%%:*}"
  type_label="${category##*:}"
  target="${ROOT_DIR}/${dir_name}"

  [ -d "$target" ] || continue

  for component in "${target}"/*/; do
    [ -d "$component" ] || continue
    scan_component "$component" "$type_label"
  done
done

# Print table
printf "\n"
printf "${BOLD} Secure Docker Blueprint – Service Overview${RESET}\n"
printf "${DIM} Scanned: $(date '+%Y-%m-%d %H:%M')${RESET}\n"

# Which blueprint release this deployment came from, and whether it still matches
# it. A host that has drifted from a tag cannot be reasoned about from the
# CHANGELOG, so the drift is stated rather than left to be discovered later.
if git -C "$ROOT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  release="$(git -C "$ROOT_DIR" describe --tags --exact-match 2>/dev/null || true)"
  if [ -n "$release" ]; then
    printf "${DIM} Blueprint: ${RESET}${BOLD}%s${RESET}\n" "$release"
  else
    nearest="$(git -C "$ROOT_DIR" describe --tags --abbrev=0 2>/dev/null || echo 'no tag reachable')"
    printf "${DIM} Blueprint: ${YELLOW}not on a release${RESET}${DIM} — %s + %s commit(s)${RESET}\n" \
      "$nearest" "$(git -C "$ROOT_DIR" rev-list --count "$nearest"..HEAD 2>/dev/null || echo '?')"
  fi
  if [ -n "$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null | grep -vE '\.env$|\.secrets/|/volumes/' || true)" ]; then
    printf "${DIM} ${YELLOW}Working tree modified${RESET}${DIM} beyond .env, .secrets/ and volumes/${RESET}\n"
  fi
else
  printf "${DIM} Blueprint: ${YELLOW}not a git checkout${RESET}${DIM} — the release cannot be identified${RESET}\n"
fi
printf "\n"

# Header
printf " ${BOLD}%-16s %-32s %-8s %-6s %-8s${RESET}\n" "COMPONENT" "DOMAIN" "PORT" "TYPE" "SOURCE"
printf " ${DIM}%-16s %-32s %-8s %-6s %-8s${RESET}\n" "────────────────" "────────────────────────────────" "────────" "──────" "────────"

# Sort: core first, then app, then mon
IFS=$'\n' sorted=($(printf '%s\n' "${rows[@]}" | sort -t'|' -k4,4 -k1,1))
unset IFS

for row in "${sorted[@]}"; do
  IFS='|' read -r name domain port type source <<< "$row"

  case "$type" in
    core) color="$CYAN" ;;
    app)  color="$GREEN" ;;
    mon)  color="$YELLOW" ;;
    *)    color="$RESET" ;;
  esac

  printf " ${color}%-16s${RESET} %-32s %-8s ${DIM}%-6s %-8s${RESET}\n" \
    "$name" "$domain" "$port" "$type" "$source"
done

# Summary
printf "\n"
printf " ${DIM}Total: ${#rows[@]} component(s)${RESET}\n"
printf " ${DIM}Source: ${CYAN}live${RESET}${DIM} = .env | ${YELLOW}example${RESET}${DIM} = .env.example${RESET}\n"
printf "\n"
