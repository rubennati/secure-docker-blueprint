#!/usr/bin/env bash
# =============================================================================
# migrate-traefik-env.sh — a deployment's .env files from the sec-*/acc-*
# vocabulary to the middleware model (core/traefik/config/dynamic/model.yml,
# decided 2026-10-18, D1–D8).
#
#   scripts/migrate-traefik-env.sh [--write] <stack-dir|env-file>...
#   scripts/migrate-traefik-env.sh [--write] --all
#
# Dry run by default: every change is printed as `-`/`+` lines, every
# consequence that is not a rename as a `note:` line, and nothing is written.
# `--write` first checks every file, then writes `<file>.pre-model` beside each
# file it changes and the migrated file over the original. A value this script
# does not know stops the run before anything is written (exit 2); a file that
# already has a `.pre-model` copy is refused the same way.
#
# What it maps, per stack .env:
#   *_TRAEFIK_ACCESS       acc-public|local|tailscale|private|deny
#                          → access-public|lan|vpn|lan-vpn|blocked
#   *_TRAEFIK_SECURITY     sec-* → *_TRAEFIK_LIMIT + *_TRAEFIK_HEADERS, and
#                          *_TRAEFIK_AUTH=auth-none@file where no AUTH exists
#   *_TRAEFIK_THREAT       removed — threat enforcement is an entrypoint
#                          decision (CROWDSEC_BOUNCER_ENABLED in core/traefik)
#   *_TRAEFIK_TLS_OPTION   tls-basic|aplus|modern → tls-compatible|standard|strict
# and per core/traefik/.env (recognised by TLS_DEFAULT_OPTION):
#   TLS_DEFAULT_OPTION, TRAEFIK_DASHBOARD_TLS_OPTION renamed; HSTS_MAX_AGE added.
#
# What it cannot do: a per-app block (frame-self, hsts-include-subdomains,
# csp-self-only) is named in the stack's compose file by the release, not in
# .env — the notes say which stack to look at. Values already in the model's
# vocabulary pass unchanged, so the run is repeatable.
#
# Runs with bash 3.2 or later and the POSIX tools of a Debian host; no awk.
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTS="core apps business monitoring backup development"

WRITE=0
ALL=0
TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --write) WRITE=1 ;;
    --all) ALL=1 ;;
    -h|--help) sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) TARGETS+=("$arg") ;;
  esac
done

if [ "$ALL" = 1 ]; then
  for root in $ROOTS; do
    for stack in "${ROOT_DIR}/${root}"/*/; do
      [ -f "${stack}.env" ] && TARGETS+=("${stack}.env")
    done
  done
fi
if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "usage: $0 [--write] <stack-dir|env-file>... | --all" >&2
  exit 2
fi

# ---- mapping tables ---------------------------------------------------------
# Each prints the new value, or nothing when the old one is not a name it knows.

map_access() {
  case "$1" in
    acc-public)     echo access-public ;;
    acc-local)      echo access-lan ;;
    acc-tailscale)  echo access-vpn ;;
    acc-private)    echo access-lan-vpn ;;
    acc-deny)       echo access-blocked ;;
    access-public|access-lan|access-vpn|access-lan-vpn|access-blocked) echo "$1" ;;
  esac
}

map_tls() {
  case "$1" in
    tls-basic)   echo tls-compatible ;;
    tls-aplus)   echo tls-standard ;;
    tls-modern)  echo tls-strict ;;
    tls-compatible|tls-standard|tls-strict) echo "$1" ;;
  esac
}

# A chain's limit position and headers position: "limit headers".
map_chain() {
  case "$1" in
    sec-0)                                   echo "limit-none headers-none" ;;
    sec-1|sec-1e)                            echo "limit-none headers-standard" ;;
    sec-2|sec-2e|sec-3|sec-3e)               echo "limit-standard headers-standard" ;;
    sec-2-spa|sec-3-spa|sec-3e-spa)          echo "limit-standard headers-standard" ;;
    sec-2-spa-xl)                            echo "limit-extra-large headers-standard" ;;
    sec-2-sync|sec-3e-sync)                  echo "limit-sync headers-standard" ;;
    sec-4|sec-5)                             echo "limit-strict headers-standard" ;;
  esac
}

# The consequences of a chain that are not a rename — one line each.
chain_notes() {
  local chain="$1" key="$2"
  case "$chain" in
    sec-0)
      echo "${key}=${chain} sent no headers; headers-none still sends the HSTS base — HTTPS is the only operating mode" ;;
  esac
  case "$chain" in
    sec-1|sec-1e)
      echo "${key}=${chain} had no counter; limit-none keeps that — confirm against the router's own requirement" ;;
    sec-2|sec-2e|sec-3|sec-3e)
      echo "${key}=${chain} counted 125/s with a burst of 200; limit-standard counts 125/s with a burst of 500 (D3) — one address may issue 300 more requests before the first 429" ;;
  esac
  case "$chain" in
    sec-3*|sec-4|sec-5)
      echo "${key}=${chain} sent HSTS with includeSubDomains and preload; the model sends max-age only — the block hsts-include-subdomains in the stack's compose file restores it, deliberately, for the host name at the registrable domain"
      echo "${key}=${chain} sent a report-only CSP, a referrer policy and Vary; headers-standard sends the referrer policy and the Permissions-Policy, no report-only CSP" ;;
  esac
  case "$chain" in
    sec-*e|sec-*e-*)
      echo "${key}=${chain} allowed same-origin framing; the model carries that as the block frame-self in the stack's compose file — check the release names it for this stack" ;;
  esac
  case "$chain" in
    sec-5)
      echo "${key}=${chain} enforced a CSP; the model carries that as the block csp-self-only in the stack's compose file — check the release names it for this stack" ;;
    sec-2-spa-xl)
      echo "${key}=${chain} is the whole-first-load bucket; limit-extra-large is accepted by CI only behind access-lan, access-vpn, access-lan-vpn or access-blocked" ;;
  esac
}

# ---- one file ---------------------------------------------------------------
# Reads the file once, prints the report, and leaves the migrated content in
# $NEW_CONTENT, the counts in CHANGES/NOTES and unknown values in UNKNOWN.

migrate_file() {
  local file="$1"
  local line key value rest quote new limit headers prefix mapped n
  CHANGES=0; NOTES=0; UNKNOWN=0; NEW_CONTENT=""
  local is_core=0 has_hsts=0 crlf=0
  grep -qE '^TLS_DEFAULT_OPTION=' "$file" && is_core=1
  grep -qE '^HSTS_MAX_AGE=' "$file" && has_hsts=1
  grep -q $'\r' "$file" && crlf=1

  # The AUTH keys the file already has, so a migrated SECURITY does not add a second.
  local auth_keys
  auth_keys="$(grep -oE '^[A-Z0-9_]*TRAEFIK[A-Z0-9_]*_AUTH=' "$file" | sed 's/=$//' || true)"

  printf '%s\n' "== ${file}"
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    if [[ "$line" =~ ^([A-Z0-9_]+)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"; rest="${BASH_REMATCH[2]}"
      # Keep the quoting style the line uses.
      quote=""
      value="$rest"
      if [[ "$rest" =~ ^\"(.*)\"$ ]]; then quote='"'; value="${BASH_REMATCH[1]}"; fi
      if [[ "$rest" =~ ^\'(.*)\'$ ]]; then quote="'"; value="${BASH_REMATCH[1]}"; fi
      value="${value%%[[:space:]]#*}"   # a trailing comment is dropped from the value
      value="${value%"${value##*[![:space:]]}"}"

      case "$key" in
        TLS_DEFAULT_OPTION|TRAEFIK_DASHBOARD_TLS_OPTION)
          mapped="$(map_tls "$value")"
          if [ -z "$mapped" ] && [ -n "$value" ]; then
            printf '  ! %s=%s — not a TLS profile this script knows\n' "$key" "$value"; UNKNOWN=$((UNKNOWN + 1))
          elif [ "$mapped" != "$value" ]; then
            printf '  - %s=%s\n  + %s=%s\n' "$key" "$value" "$key" "$mapped"; CHANGES=$((CHANGES + 1))
            line="${key}=${quote}${mapped}${quote}"
          fi
          ;;
        *TRAEFIK*_TLS_OPTION)
          mapped="$(map_tls "$value")"
          if [ -z "$mapped" ] && [ -n "$value" ]; then
            printf '  ! %s=%s — not a TLS profile this script knows\n' "$key" "$value"; UNKNOWN=$((UNKNOWN + 1))
          elif [ "$mapped" != "$value" ]; then
            printf '  - %s=%s\n  + %s=%s\n' "$key" "$value" "$key" "$mapped"; CHANGES=$((CHANGES + 1))
            line="${key}=${quote}${mapped}${quote}"
            if [ "$mapped" = tls-standard ]; then
              printf '  note: %s=tls-standard is the deployment standard — the release names tls.options on a stack only as a documented exception; otherwise the variable is no longer read\n' "$key"; NOTES=$((NOTES + 1))
            fi
          fi
          ;;
        *TRAEFIK*_ACCESS)
          mapped="$(map_access "$value")"
          if [ -z "$mapped" ] && [ -n "$value" ]; then
            printf '  ! %s=%s — not an access policy this script knows\n' "$key" "$value"; UNKNOWN=$((UNKNOWN + 1))
          elif [ "$mapped" != "$value" ]; then
            printf '  - %s=%s\n  + %s=%s\n' "$key" "$value" "$key" "$mapped"; CHANGES=$((CHANGES + 1))
            line="${key}=${quote}${mapped}${quote}"
          fi
          ;;
        *TRAEFIK*_SECURITY)
          mapped="$(map_chain "$value")"
          if [ -z "$mapped" ]; then
            printf '  ! %s=%s — not a security chain this script knows\n' "$key" "$value"; UNKNOWN=$((UNKNOWN + 1))
          else
            limit="${mapped%% *}"; headers="${mapped##* }"
            prefix="${key%_SECURITY}"
            printf '  - %s=%s\n  + %s_LIMIT=%s\n  + %s_HEADERS=%s\n' "$key" "$value" "$prefix" "$limit" "$prefix" "$headers"
            line="${prefix}_LIMIT=${quote}${limit}${quote}"$'\n'"${prefix}_HEADERS=${quote}${headers}${quote}"
            CHANGES=$((CHANGES + 1))
            if ! printf '%s\n' "$auth_keys" | grep -qx "${prefix}_AUTH"; then
              printf '  + %s_AUTH=auth-none@file\n' "$prefix"
              line="${line}"$'\n'"${prefix}_AUTH=${quote}auth-none@file${quote}"
              printf '  note: %s_AUTH=auth-none@file is the explicit "no gate"; auth-authentik@file or a stack'"'"'s own <stack>-auth@docker go here\n' "$prefix"; NOTES=$((NOTES + 1))
            fi
            while IFS= read -r n; do
              [ -n "$n" ] && { printf '  note: %s\n' "$n"; NOTES=$((NOTES + 1)); }
            done <<< "$(chain_notes "$value" "$key")"
          fi
          ;;
        *TRAEFIK*_THREAT)
          printf '  - %s=%s\n' "$key" "$value"; CHANGES=$((CHANGES + 1))
          if [ -n "$value" ]; then
            printf '  note: %s named the bouncer for this router; threat enforcement is now an entrypoint decision — CROWDSEC_BOUNCER_ENABLED in core/traefik/.env puts it in front of every router\n' "$key"
          else
            printf '  note: %s is removed; threat enforcement is an entrypoint decision — CROWDSEC_BOUNCER_ENABLED in core/traefik/.env\n' "$key"
          fi
          NOTES=$((NOTES + 1))
          line=""
          continue
          ;;
      esac
    fi
    NEW_CONTENT="${NEW_CONTENT}${line}"$'\n'
  done < "$file"

  if [ "$is_core" = 1 ] && [ "$has_hsts" = 0 ]; then
    printf '  + HSTS_MAX_AGE=63072000\n'; CHANGES=$((CHANGES + 1))
    printf '  note: HSTS_MAX_AGE is the max-age every header profile sends (two years); added at the end of the file — move it next to TLS_DEFAULT_OPTION if you keep the file ordered\n'; NOTES=$((NOTES + 1))
    NEW_CONTENT="${NEW_CONTENT}"$'\n'"# HSTS max-age (seconds) every header profile sends — two years."$'\n'"HSTS_MAX_AGE=63072000"$'\n'
  fi
  if [ "$crlf" = 1 ] && [ "$CHANGES" -gt 0 ]; then
    printf '  note: the file had CRLF line endings; the migrated file is written with LF\n'; NOTES=$((NOTES + 1))
  fi
  if [ "$CHANGES" -eq 0 ] && [ "$UNKNOWN" -eq 0 ]; then
    printf '  already in the model — nothing to change\n'
  fi
}

# ---- run --------------------------------------------------------------------
total_changes=0; total_unknown=0; total_files=0
PENDING_FILES=(); PENDING_CONTENT=()

for target in "${TARGETS[@]}"; do
  if [ -d "$target" ]; then
    file="${target%/}/.env"
  else
    file="$target"
  fi
  if [ ! -f "$file" ]; then
    printf '== %s\n  ! no such file\n' "$file"; total_unknown=$((total_unknown + 1)); continue
  fi
  migrate_file "$file"
  total_files=$((total_files + 1))
  total_changes=$((total_changes + CHANGES))
  total_unknown=$((total_unknown + UNKNOWN))
  if [ "$WRITE" = 1 ] && [ -e "${file}.pre-model" ] && [ "$CHANGES" -gt 0 ]; then
    printf '  ! %s.pre-model exists — a previous run left it; move it away before writing\n' "$file"
    total_unknown=$((total_unknown + 1))
  fi
  if [ "$CHANGES" -gt 0 ]; then
    PENDING_FILES+=("$file"); PENDING_CONTENT+=("$NEW_CONTENT")
  fi
done

printf '\n%s file(s), %s change(s)' "$total_files" "$total_changes"
if [ "$total_unknown" -gt 0 ]; then
  printf ', %s problem(s) — nothing written\n' "$total_unknown"
  exit 2
fi
if [ "$WRITE" = 0 ]; then
  printf ' — dry run, nothing written; add --write to apply\n'
  exit 0
fi
if [ "${#PENDING_FILES[@]}" -eq 0 ]; then
  printf ' — nothing to write\n'
  exit 0
fi
i=0
while [ "$i" -lt "${#PENDING_FILES[@]}" ]; do
  cp -p "${PENDING_FILES[$i]}" "${PENDING_FILES[$i]}.pre-model"
  printf '%s' "${PENDING_CONTENT[$i]}" > "${PENDING_FILES[$i]}"
  i=$((i + 1))
done
printf ' — written; the previous file of each is beside it as .env.pre-model\n'
