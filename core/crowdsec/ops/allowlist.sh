#!/usr/bin/env bash
# =============================================
# CrowdSec – the administrative exemption (LAPI AllowList)
# =============================================
# Keeps the administrator's own devices out of every decision the engine
# serves — local scenarios and community blocklists alike — so that a scanner
# pattern an admin's browser happens to produce cannot close the management
# path (docs/bugfixes/crowdsec-firewall-bouncer-2026-08-28.md).
#
# Nothing here runs on its own. The operator decides, writes the devices into
# CROWDSEC_ALLOWLIST_ADMIN in .env, and runs:
#
#   ops/allowlist.sh apply            # create the list, add what .env names
#   ops/allowlist.sh status           # what the engine holds
#   ops/allowlist.sh check <address>  # is this address exempt?
#   ops/allowlist.sh remove <value>   # remove one entry, deliberately
#
# apply adds and never removes: an entry taken out of .env stays in the engine
# until `remove` is run for it, so a mistake in .env cannot silently lift an
# exemption. An empty variable means "no exemption, by decision" and apply
# does nothing; a value that is not an address or range is an error and
# nothing is applied.
#
# What the exemption is not: evidence that a device is trustworthy. An
# exempted device that is compromised stays exempt. That is why the
# recommendation is the administrator's devices, each by its own address,
# and not the VPN range — docs/firewall-bouncer.md, "VPN ranges are not RFC1918".
# =============================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIST_NAME="${CROWDSEC_ALLOWLIST_NAME:-admin-devices}"
LIST_DESCRIPTION="Administrative devices exempt from every decision — core/crowdsec/README.md, step 5"
# Whole VPN ranges: accepted, but named for what they are when they appear.
VPN_RANGES="100.64.0.0/10 fd7a:115c:a1e0::/48"

usage() { sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }

if [ -f "${ROOT_DIR}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${ROOT_DIR}/.env"
  set +a
fi

# The engine's cscli. ALLOWLIST_CSCLI replaces the docker exec in tests.
cscli() {
  if [ -n "${ALLOWLIST_CSCLI:-}" ]; then
    "${ALLOWLIST_CSCLI}" "$@"
  else
    docker exec "${CONTAINER_NAME_APP:-crowdsec}" cscli "$@"
  fi
}

is_address_or_range() {  # IPv4 or IPv6, with an optional prefix length
  local prefix="" host="${1%%/*}"
  case "$1" in
    */*) prefix="${1#*/}"; printf '%s' "${prefix}" | grep -qE '^[0-9]{1,3}$' || return 1 ;;
  esac
  if printf '%s' "${host}" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
    local o; IFS=. read -r -a o <<< "${host}"
    for n in "${o[@]}"; do [ "${n}" -le 255 ] || return 1; done
    [ -z "${prefix}" ] || [ "${prefix}" -le 32 ] || return 1
    return 0
  fi
  printf '%s' "${host}" | grep -qE '^[0-9A-Fa-f:]+$' && [ "${host#*:}" != "${host}" ] || return 1
  [ -z "${prefix}" ] || [ "${prefix}" -le 128 ]
}

is_vpn_range() {
  for r in ${VPN_RANGES}; do [ "$1" = "${r}" ] && return 0; done
  return 1
}

entries() {  # CROWDSEC_ALLOWLIST_ADMIN, split on commas and whitespace
  printf '%s' "${CROWDSEC_ALLOWLIST_ADMIN:-}" | tr ',' ' '
}

list_exists() { cscli allowlists inspect "${LIST_NAME}" >/dev/null 2>&1; }

list_holds() {  # <value> — present in the engine's copy of the list?
  cscli allowlists inspect "${LIST_NAME}" -o json 2>/dev/null | grep -qF "\"$1\""
}

cmd_apply() {
  [ -f "${ROOT_DIR}/.env" ] || { echo "ERROR: ${ROOT_DIR}/.env not found — copy .env.example to .env first"; exit 1; }
  local wanted invalid="" vpn="" added=0 present=0
  wanted="$(entries)"
  if [ -z "$(printf '%s' "${wanted}" | tr -d '[:space:]')" ]; then
    echo "CROWDSEC_ALLOWLIST_ADMIN is empty: no exemption is active, by decision."
    echo "To exempt the administrative devices, list their addresses there and run apply again."
    exit 0
  fi
  for v in ${wanted}; do
    is_address_or_range "${v}" || invalid="${invalid} ${v}"
    is_vpn_range "${v}" && vpn="${vpn} ${v}"
  done
  if [ -n "${invalid}" ]; then
    echo "ERROR: CROWDSEC_ALLOWLIST_ADMIN carries a value that is not an IP address or range:${invalid}"
    echo "       Nothing was applied. Fix the value, then run apply again."
    exit 1
  fi
  if [ -n "${vpn}" ]; then
    echo "WARNING: ${vpn# } is a whole VPN range. Every device on it is exempt from every decision,"
    echo "         a compromised one included. The recommendation is one entry per administrative"
    echo "         device. Applied as written."
  fi
  if list_exists; then
    echo "AllowList ${LIST_NAME} exists."
  else
    cscli allowlists create "${LIST_NAME}" -d "${LIST_DESCRIPTION}" >/dev/null
    echo "AllowList ${LIST_NAME} created."
  fi
  for v in ${wanted}; do
    if list_holds "${v}"; then
      echo "  present  ${v}"
      present=$((present + 1))
    else
      cscli allowlists add "${LIST_NAME}" "${v}" -d "administrative device (ops/allowlist.sh apply)" >/dev/null
      echo "  added    ${v}"
      added=$((added + 1))
    fi
  done
  echo "${added} added, ${present} already present. Nothing is removed by apply —"
  echo "an entry that left .env stays until: ops/allowlist.sh remove <value>."
  echo "Check from the device's side: ops/allowlist.sh check <its address>, IPv4 and IPv6 each."
}

cmd_status() {
  cscli allowlists list
  if list_exists; then cscli allowlists inspect "${LIST_NAME}"; else echo "AllowList ${LIST_NAME}: not created — no administrative exemption is active."; fi
}

cmd_check() {
  [ "$#" -eq 1 ] || usage
  is_address_or_range "$1" || { echo "ERROR: '$1' is not an IP address or range"; exit 1; }
  cscli allowlists check "$1"
}

cmd_remove() {
  [ "$#" -eq 1 ] || usage
  list_exists || { echo "AllowList ${LIST_NAME} does not exist — nothing to remove."; exit 1; }
  cscli allowlists remove "${LIST_NAME}" "$1"
  echo "removed ${1} from ${LIST_NAME}. Decisions against it can be served again from now on."
}

cmd="${1:-}"; shift || true
case "${cmd}" in
  apply)  cmd_apply ;;
  status) cmd_status ;;
  check)  cmd_check "$@" ;;
  remove) cmd_remove "$@" ;;
  *) usage ;;
esac
