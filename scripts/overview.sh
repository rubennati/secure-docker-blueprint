#!/usr/bin/env bash
set -euo pipefail

# =============================================
# Docker Ops Blueprint – Service Overview
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
    return
  fi

  local name
  name="$(basename "$dir")"

  # Read values from env file (without exporting into current shell)
  local domain="" port="" project=""

  domain="$(grep -E '^APP_TRAEFIK_HOST=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"
  port="$(grep -E '^APP_INTERNAL_PORT=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"
  project="$(grep -E '^COMPOSE_PROJECT_NAME=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)"

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
printf "${BOLD} Docker Ops Blueprint – Service Overview${RESET}\n"
printf "${DIM} Scanned: $(date '+%Y-%m-%d %H:%M')${RESET}\n"
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
