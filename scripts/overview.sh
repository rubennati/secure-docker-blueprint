#!/usr/bin/env bash
set -euo pipefail

# =============================================
# Secure Docker Blueprint – Service Overview
# =============================================
# Scans all components and prints a summary
# table from .env (or .env.example as fallback).
# =============================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --host     compare the files stacks install outside the checkout (host-files.sh)
#            and check the TLS option per host name across stacks
# --routers  list every Traefik router with its four positions and TLS option
WITH_HOST=0
WITH_ROUTERS=0
for arg in "$@"; do
  case "$arg" in
    --host) WITH_HOST=1 ;;
    --routers) WITH_ROUTERS=1 ;;
    *) echo "usage: $0 [--host] [--routers]" >&2; exit 2 ;;
  esac
done

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

# =============================================
# Traefik routers — the middleware model
# =============================================
# Every router carries four positions — access, limit, headers, auth — named
# through its stack's variables (core/traefik/config/dynamic/model.yml). This
# reads each stack's compose labels with its .env (or .env.example) values, the
# way Compose will, and reports what the deployment has not moved yet (a name
# the model replaces), what Traefik would disable (an empty position), and
# which routers name a TLS option other than the deployment standard.

ROUTER_ROOTS="core apps business monitoring backup development"

# The value of a variable in an env file, unquoted; empty when unset.
envval() {
  grep -E "^${2}=" "$1" 2>/dev/null | head -1 | cut -d= -f2- \
    | sed -E "s/^\"(.*)\"[[:space:]]*$/\1/; s/^'(.*)'[[:space:]]*$/\1/" || true
}

# ${VAR} and ${VAR:-default} in a label, from the stack's env file.
resolve() {
  local s="$1" env="$2" n=0 whole var def val
  while [ $n -lt 10 ] && [[ "$s" =~ \$\{([A-Za-z0-9_]+)(:?-[^}]*)?\} ]]; do
    whole="${BASH_REMATCH[0]}"; var="${BASH_REMATCH[1]}"; def="${BASH_REMATCH[2]}"
    def="${def#:}"; def="${def#-}"
    val="$(envval "$env" "$var")"
    [ -z "$val" ] && val="$def"
    s="${s//"$whole"/$val}"
    n=$((n + 1))
  done
  printf '%s' "$s"
}

# The model's names for the TLS profiles, so an old name compares equal.
tls_model_name() {
  case "$1" in
    tls-basic) echo tls-compatible ;;
    tls-aplus) echo tls-standard ;;
    tls-modern) echo tls-strict ;;
    *) echo "$1" ;;
  esac
}

traefik_env="${ROOT_DIR}/core/traefik/.env"
[ -f "$traefik_env" ] || traefik_env="${ROOT_DIR}/core/traefik/.env.example"
tls_standard="$(tls_model_name "$(envval "$traefik_env" TLS_DEFAULT_OPTION)")"
[ -z "$tls_standard" ] && tls_standard="(unset)"

router_rows=()      # stack|router|access|limit|headers|auth|tls|note
host_rows=()        # host|tls|stack:router
n_routers=0; n_old=0; n_empty=0; n_tls=0
old_stacks=""; tls_list=""

scan_routers() {
  local dir="$1" stack env files f labels names r raw rule mw tlsopt resolved
  stack="${dir#${ROOT_DIR}/}"; stack="${stack%/}"
  env=""
  [ -f "${dir}/.env" ] && env="${dir}/.env"
  [ -z "$env" ] && [ -f "${dir}/.env.example" ] && env="${dir}/.env.example"
  if [ -f "${dir}/docker-compose.yml" ]; then
    files="${dir}/docker-compose.yml"
  else
    files="$(ls "${dir}"/*.yml 2>/dev/null | grep -v '\.local\.yml$' || true)"
  fi
  [ -z "$files" ] && return 0
  # Router labels, uncommented, without the list dash and quotes.
  labels="$(printf '%s\n' "$files" | while IFS= read -r f; do
    grep -hE '^[[:space:]]*-[[:space:]]*"?traefik\.http\.routers\.' "$f" 2>/dev/null || true
  done | sed -E 's/^[[:space:]]*-[[:space:]]*"?//; s/"[[:space:]]*$//')"
  [ -z "$labels" ] && return 0
  names=""
  while IFS= read -r raw; do
    case "|$names|" in *"|$raw|"*) ;; *) names="${names:+$names|}$raw" ;; esac
  done <<< "$(printf '%s\n' "$labels" | sed -E 's/^traefik\.http\.routers\.([^.]+)\..*/\1/')"
  printf '%s\n' "$names" | tr '|' '\n' | while IFS= read -r raw; do
    [ -z "$raw" ] && continue
    rule="$(printf '%s\n' "$labels" | grep -F "traefik.http.routers.${raw}.rule=" | head -1 | cut -d= -f2-)"
    [ -z "$rule" ] && continue
    mw="$(printf '%s\n' "$labels" | grep -F "traefik.http.routers.${raw}.middlewares=" | head -1 | cut -d= -f2-)"
    tlsopt="$(printf '%s\n' "$labels" | grep -F "traefik.http.routers.${raw}.tls.options=" | head -1 | cut -d= -f2-)"
    r="$(resolve "$raw" "$env")"
    classify_router "$stack" "$r" "$rule" "$mw" "$tlsopt" "$env"
  done
}

# Prints one row: stack|router|access|limit|headers|auth|tls|note|hosts
classify_router() {
  local stack="$1" r="$2" rule="$3" mw="$4" tlsopt="$5" env="$6"
  local access="-" limit="-" headers="-" auth="-" tls note="" old=0 empty="" e name fam var val hosts
  local resolved authvals=""
  resolved="$(resolve "$mw" "$env")"
  # The auth position may carry a stack's own gate (<stack>-auth@docker): the
  # variable it comes from names the position.
  for var in $(printf '%s' "$mw" | grep -oE '\$\{[A-Z0-9_]*TRAEFIK[A-Z0-9_]*_AUTH[^}]*\}' | sed -E 's/^\$\{([A-Z0-9_]+).*/\1/' || true); do
    val="$(envval "$env" "$var")"; [ -n "$val" ] && authvals="${authvals} ${val} ${val}@file"
  done
  # A position whose variable is empty: Compose passes nothing, Traefik
  # disables the router.
  for var in $(printf '%s' "$mw" | grep -oE '\$\{[A-Z0-9_]*TRAEFIK[A-Z0-9_]*_(ACCESS|LIMIT|HEADERS|AUTH|SECURITY)\}' | sed -E 's/^\$\{//; s/\}$//' || true); do
    [ -z "$(envval "$env" "$var")" ] && empty="${empty:+$empty,}${var}"
  done
  local IFS=','
  for e in $resolved; do
    unset IFS
    e="${e#"${e%%[![:space:]]*}"}"; e="${e%"${e##*[![:space:]]}"}"
    [ -z "$e" ] && continue
    name="${e%%@*}"
    case "$name" in
      access-*|acc-*) access="$name" ;;
      limit-*|rl-*)   limit="$name" ;;
      headers-*|sec-*|hdr-*) headers="$name" ;;
      auth-*)         auth="$e" ;;
      *) case " ${authvals} " in *" ${e} "*) auth="$e" ;; esac ;;
    esac
    case "$name" in acc-*|sec-*|hdr-*|rl-*|crowdsec-*) old=1 ;; esac
  done
  unset IFS
  if [ -n "$tlsopt" ]; then
    tls="$(resolve "$tlsopt" "$env")"; tls="${tls%@file}"
  else
    tls="default"
  fi
  [ "$old" = 1 ] && note="old names"
  [ -n "$empty" ] && note="${note:+$note; }empty: ${empty}"
  if [ "$tls" != default ] && [ "$(tls_model_name "$tls")" != "$tls_standard" ]; then
    note="${note:+$note; }TLS exception"
  fi
  hosts="$(printf '%s' "$(resolve "$rule" "$env")" | grep -oE 'Host\(`[^`]+`\)' | sed -E 's/^Host\(`//; s/`\)$//' | tr '\n' ' ' || true)"
  local source=example
  case "$env" in */.env) source=live ;; esac
  printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$stack" "$r" "$access" "$limit" "$headers" "$auth" "$tls" "$note" "$hosts" "$source"
}

for root in $ROUTER_ROOTS; do
  [ -d "${ROOT_DIR}/${root}" ] || continue
  for component in "${ROOT_DIR}/${root}"/*/; do
    [ -d "$component" ] || continue
    while IFS= read -r row; do
      [ -z "$row" ] && continue
      router_rows+=("$row")
    done <<< "$(scan_routers "$component")"
  done
done

router_stacks=""
for row in "${router_rows[@]:-}"; do
  [ -z "$row" ] && continue
  IFS='|' read -r stack r access limit headers auth tls note hosts source <<< "$row"
  n_routers=$((n_routers + 1))
  case "|$router_stacks|" in *"|$stack|"*) ;; *) router_stacks="${router_stacks:+$router_stacks|}$stack" ;; esac
  case "$note" in *"old names"*)
    n_old=$((n_old + 1))
    case "|$old_stacks|" in *"|$stack|"*) ;; *) old_stacks="${old_stacks:+$old_stacks|}$stack" ;; esac ;;
  esac
  case "$note" in *"empty:"*) n_empty=$((n_empty + 1)) ;; esac
  case "$note" in *"TLS exception"*) n_tls=$((n_tls + 1)); tls_list="${tls_list:+$tls_list, }${stack##*/}:${r}=${tls}" ;; esac
  # Only a live .env carries a real host name; the example files share
  # placeholders, so they are not compared.
  [ "$source" = live ] || continue
  for h in $hosts; do
    tlsname="$tls"; [ "$tlsname" = default ] && tlsname="default (${tls_standard})"
    host_rows+=("${h}|${tlsname}|${stack}:${r}")
  done
done
n_router_stacks="$(printf '%s' "$router_stacks" | tr '|' '\n' | grep -c . || true)"
n_old_stacks="$(printf '%s' "$old_stacks" | tr '|' '\n' | grep -c . || true)"

printf " ${BOLD}Traefik routers${RESET} ${DIM}(the middleware model — core/traefik/config/dynamic/model.yml)${RESET}\n"
printf " ${DIM}%s router(s) in %s stack(s) · TLS standard: ${RESET}%s${DIM} (TLS_DEFAULT_OPTION, %s)${RESET}\n" \
  "$n_routers" "$n_router_stacks" "$tls_standard" "${traefik_env#${ROOT_DIR}/}"
if [ "$n_old" -gt 0 ]; then
  printf " ${YELLOW}old names:${RESET}       %s router(s) in %s stack(s) ${DIM}— scripts/migrate-traefik-env.sh (dry run) names every change${RESET}\n" "$n_old" "$n_old_stacks"
else
  printf " ${GREEN}old names:${RESET}       none\n"
fi
if [ "$n_empty" -gt 0 ]; then
  printf " ${YELLOW}empty positions:${RESET} %s router(s) ${DIM}— Traefik disables each; --routers names the variable${RESET}\n" "$n_empty"
else
  printf " ${GREEN}empty positions:${RESET} none\n"
fi
if [ "$n_tls" -gt 0 ]; then
  printf " ${CYAN}TLS exceptions:${RESET}  %s router(s) ${DIM}— %s${RESET}\n" "$n_tls" "$tls_list"
else
  printf " ${GREEN}TLS exceptions:${RESET}  none ${DIM}— every router takes the default option${RESET}\n"
fi
[ "$WITH_ROUTERS" = 1 ] || printf " ${DIM}--routers lists every router with its positions${RESET}\n"
printf "\n"

if [ "$WITH_ROUTERS" = 1 ] && [ "$n_routers" -gt 0 ]; then
  printf " ${BOLD}%-22s %-24s %-16s %-18s %-26s %-18s %-16s %s${RESET}\n" "STACK" "ROUTER" "ACCESS" "LIMIT" "HEADERS" "AUTH" "TLS" "NOTE"
  printf " ${DIM}%-22s %-24s %-16s %-18s %-26s %-18s %-16s %s${RESET}\n" "──────────────────────" "────────────────────────" "────────────────" "──────────────────" "──────────────────────────" "──────────────────" "────────────────" "────"
  for row in "${router_rows[@]}"; do
    IFS='|' read -r stack r access limit headers auth tls note hosts source <<< "$row"
    printf " %-22s %-24s %-16s %-18s %-26s %-18s %-16s ${YELLOW}%s${RESET}\n" "$stack" "$r" "$access" "$limit" "$headers" "$auth" "$tls" "$note"
  done
  printf "\n"
fi

# --host: the files some stacks install outside the checkout — a logrotate
# stanza, systemd units, a backup agent's configuration — compared with what
# the repository ships. A blueprint update changes the checkout and nothing
# under /etc; this is where that shows. Then the TLS option per host name
# across stacks: Traefik maps one option to a host name per entrypoint, and
# two routers naming different ones make it fall back to `default` for both
# (logged, not refused — core.strictTLSOptions is off). Exit status follows
# both checks, so the command can close a deployment step.
if [ "$WITH_HOST" = 1 ]; then
  printf " ${BOLD}Host files${RESET} ${DIM}(scripts/host-files.sh check — docs/standards/host-files.md)${RESET}\n"
  host_rc=0
  bash "${ROOT_DIR}/scripts/host-files.sh" check || host_rc=$?
  printf "\n"

  printf " ${BOLD}TLS option per host name${RESET} ${DIM}(across the stacks with a live .env)${RESET}\n"
  conflicts=0
  [ "${#host_rows[@]}" -eq 0 ] && printf " ${DIM}no stack has a .env — nothing to compare (the example files share placeholder names)${RESET}\n"
  for h in $(printf '%s\n' "${host_rows[@]:-}" | cut -d'|' -f1 | grep . | sort -u); do
    options="$(printf '%s\n' "${host_rows[@]}" | grep -F "${h}|" | cut -d'|' -f2 | sort -u)"
    if [ "$(printf '%s\n' "$options" | grep -c .)" -gt 1 ]; then
      conflicts=$((conflicts + 1))
      printf " ${YELLOW}%s${RESET} ${DIM}is served with different options — Traefik uses default for all of them:${RESET}\n" "$h"
      printf '%s\n' "${host_rows[@]}" | grep -F "${h}|" | while IFS='|' read -r _ opt who; do
        printf '     %-28s %s\n' "$opt" "$who"
      done
    fi
  done
  if [ "$conflicts" -eq 0 ] && [ "${#host_rows[@]}" -gt 0 ]; then
    printf " ${GREEN}no conflict${RESET} ${DIM}— one TLS option per host name${RESET}\n"
  fi
  printf "\n"
  [ "$host_rc" -ne 0 ] && exit "$host_rc"
  [ "$conflicts" -ne 0 ] && exit 1
  exit 0
fi
