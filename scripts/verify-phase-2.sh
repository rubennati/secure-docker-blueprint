#!/usr/bin/env bash
# =============================================
# Secure Docker Blueprint – Phase 2 host verification, the readable half
# =============================================
# Runs the checks of docs/host-verification-phase-2.md that only read state and
# prints one line per check: PASS, FAIL or SKIP with the reason. It changes
# nothing — no render, no install, no decision — and runs as the operator, not
# as root; a check that needs root says SKIP.
#
#   scripts/verify-phase-2.sh [2a|2b|2c|2d|2e|all]
#
# Values it reads from the environment:
#   WHOAMI_HOST  VAULT_HOST  MATOMO_HOST  KEYCLOAK_HOST  — host names behind the proxy
#   ADMIN_V4  ADMIN_V6                                   — the administrative device
#
# A manual row of the plan stays manual; this script does not replace it.
# =============================================
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRAEFIK="${ROOT_DIR}/core/traefik"
pass=0; fail=0; skip=0

ok()   { printf '  PASS  %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; fail=$((fail + 1)); }
skipc(){ printf '  SKIP  %s\n' "$1"; skip=$((skip + 1)); }
need() { [ -n "${!1:-}" ] || { skipc "$2 — set $1"; return 1; }; }

head_of() { curl -skI --max-time 15 "$1" 2>/dev/null; }
status_of() { head_of "$1" | awk 'NR==1{print $2}'; }
header_of() { head_of "$1" | awk -v h="$(printf '%s' "$2" | tr 'A-Z' 'a-z')" 'tolower($0) ~ "^"h":" {sub(/\r$/,""); sub(/^[^:]*:[ ]*/,""); print}'; }

# ---------------------------------------------------------------- 2a
phase_2a() {
  echo "2a — entrypoint and validation"
  local cfg="${TRAEFIK}/config/traefik.yml"
  if [ -f "${cfg}" ]; then
    for ep in web websecure; do
      if awk -v ep="$ep" '$0 ~ "^  "ep":" {f=1} f && /respondingTimeouts/ {t=1} f && /^  [a-z]+:/ && $0 !~ "^  "ep":" {f=0} END {exit !t}' "${cfg}"; then
        ok "A1 ${ep}: respondingTimeouts rendered"
      else
        bad "A1 ${ep}: respondingTimeouts missing in config/traefik.yml"
      fi
    done
    local want have
    want="$(grep -vE '^[[:space:]]*(#|$)' "${TRAEFIK}/ops/cloudflare-ips.txt" | tr -d '[:space:]' | sort | tr '\n' ' ')"
    have="$(grep -oE '^[[:space:]]+- "[0-9A-Fa-f:./]+"' "${cfg}" | tr -d ' "-' | sort -u | tr '\n' ' ')"
    for r in ${want}; do printf '%s' "${have}" | grep -qF "${r}" || { bad "A1 trustedIPs: ${r} from the file is not rendered"; want=""; break; }; done
    [ -n "${want}" ] && ok "A1 trustedIPs equal ops/cloudflare-ips.txt"
  else
    skipc "A1 — config/traefik.yml not rendered yet"
  fi
  if command -v docker >/dev/null && (cd "${TRAEFIK}" && docker compose ps --format '{{.Name}} {{.Health}}' 2>/dev/null | grep -q .); then
    if (cd "${TRAEFIK}" && docker compose ps --format '{{.Health}}' | grep -vq healthy); then bad "A2 a proxy service is not healthy"; else ok "A2 both proxy services healthy"; fi
    if [ -f "${TRAEFIK}/volumes/logs/traefik.log" ] && grep -q '"level":"error"' "${TRAEFIK}/volumes/logs/traefik.log"; then bad "A2 traefik.log carries errors"; else ok "A2 no error in traefik.log"; fi
  else
    skipc "A2 — the proxy is not running here"
  fi
  if command -v python3 >/dev/null && python3 "${ROOT_DIR}/scripts/ci/check-cloudflare-ips.py" --online >/dev/null 2>&1; then ok "A3 published ranges equal the file"; else bad "A3 check-cloudflare-ips.py --online"; fi
  skipc "A4, A5, A6 — change the configuration: manual, see the plan"
}

# ---------------------------------------------------------------- 2b
phase_2b() {
  echo "2b — host files"
  local out rc
  out="$(bash "${ROOT_DIR}/scripts/host-files.sh" check 2>&1)"; rc=$?
  printf '%s\n' "${out}" | sed 's/^/        /'
  if printf '%s' "${out}" | grep -qE '^\s+(identical|adapted|not installed|missing|differs|unreadable|not rendered|skipped)'; then ok "B3/B6 states reported (exit ${rc}); judge each row against the plan"; else bad "B3/B6 no state line from host-files.sh check"; fi
  # Content, not names: a path such as /root/.borg-passphrase may appear, its bytes must not.
  if printf '%s' "${out}" | grep -qE 'BEGIN [A-Z ]*PRIVATE KEY|^[A-Za-z0-9+/]{40,}={0,2}$'; then bad "B5 output contains secret-looking content"; else ok "B5 no secret content in the check output"; fi
  if [ -f /etc/logrotate.d/traefik ]; then
    if grep -qE 'docker kill|/path/to/' /etc/logrotate.d/traefik; then bad "B2 installed stanza is the old shape or carries the placeholder"; else ok "B2 installed stanza has no docker kill and no placeholder"; fi
    if [ "$(id -u)" -eq 0 ] && command -v logrotate >/dev/null; then
      if logrotate -d /etc/logrotate.d/traefik 2>&1 | grep -c 'considering log' | grep -qx 2; then ok "B2 logrotate -d lists both logs"; else bad "B2 logrotate -d does not list two logs"; fi
    else skipc "B2 logrotate -d — needs root"; fi
  else
    skipc "B2 — /etc/logrotate.d/traefik not installed"
  fi
}

# ---------------------------------------------------------------- 2c
phase_2c() {
  echo "2c — Authentik switch"
  need WHOAMI_HOST "C1/C2/C4/C5" || return
  local sw; sw="$(grep -E '^AUTHENTIK_FORWARD_AUTH_ENABLED=' "${TRAEFIK}/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr 'A-Z' 'a-z')"
  local s; s="$(status_of "https://${WHOAMI_HOST}/")"
  case "${sw:-false}" in
    true)
      [ -f "${TRAEFIK}/config/dynamic/authentik.yml" ] && ok "C2 authentik.yml rendered" || bad "C2 switch on but authentik.yml missing"
      if [ "${s}" = 302 ] && header_of "https://${WHOAMI_HOST}/" Location | grep -qi authentik; then ok "C2 whoami redirects to Authentik (302)"; elif [ "${s}" = 200 ]; then skipc "C2 whoami answers 200 — the router does not name auth-authentik yet, or a session cookie is in play"; else bad "C2 whoami answers ${s:-nothing}"; fi
      ;;
    *)
      [ -f "${TRAEFIK}/config/dynamic/authentik.yml" ] && bad "C1 switch off but authentik.yml present" || ok "C1 no authentik.yml with the switch off"
      [ "${s}" = 200 ] && ok "C1 whoami answers 200" || [ "${s}" = 404 ] && ok "C5 whoami disabled (404) — a router still names the gate" || bad "C1 whoami answers ${s:-nothing}"
      ;;
  esac
  skipc "C3, C4, C6, C7 — session, outpost stop, drift guard, independence: manual or scripted per the plan"
}

# ---------------------------------------------------------------- 2d
phase_2d() {
  echo "2d — stack fixes"
  if need VAULT_HOST "D1"; then
    local x; x="$(header_of "https://${VAULT_HOST}/" X-Frame-Options | tr 'A-Z' 'a-z')"
    case "${x}" in sameorigin) ok "D1 vault UI: X-Frame-Options SAMEORIGIN (the application's)";; deny) bad "D1 vault UI: DENY — the proxy's header still wins";; "") bad "D1 vault UI: no X-Frame-Options at all";; *) bad "D1 vault UI: ${x}";; esac
    x="$(header_of "https://${VAULT_HOST}/connector.html" X-Frame-Options)"
    [ -z "${x}" ] && ok "D1 connector.html: no X-Frame-Options" || bad "D1 connector.html carries X-Frame-Options: ${x}"
  fi
  if need MATOMO_HOST "D2"; then
    local x; x="$(header_of "https://${MATOMO_HOST}/index.php?module=Widgetize&action=iframe" X-Frame-Options)"
    [ -z "${x}" ] && ok "D2 Widgetize: no X-Frame-Options" || bad "D2 Widgetize carries X-Frame-Options: ${x}"
  fi
  if [ -n "${KEYCLOAK_HOST:-}" ]; then
    local x; x="$(header_of "https://${KEYCLOAK_HOST}/admin/master/console/" X-Frame-Options | tr 'A-Z' 'a-z')"
    [ "${x}" = sameorigin ] && ok "D3 Keycloak console: SAMEORIGIN" || bad "D3 Keycloak console: ${x:-none}"
  else skipc "D3 — set KEYCLOAK_HOST when the stack is deployed"; fi
  if command -v docker >/dev/null; then
    local d; d="$(docker info --format '{{.LoggingDriver}}' 2>/dev/null)"
    [ "${d}" = local ] && ok "D4 daemon log driver: local" || skipc "D4 daemon log driver is '${d:-unknown}' — manual step of the plan not done"
    (cd "${TRAEFIK}" && docker compose logs --tail 3 traefik 2>/dev/null | grep -q .) && ok "D5 docker compose logs prints lines" || skipc "D5 — proxy not running or no lines"
  fi
}

# ---------------------------------------------------------------- 2e
phase_2e() {
  echo "2e — the administrative exemption"
  if ! command -v docker >/dev/null || ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx crowdsec; then skipc "E1–E3 — the crowdsec container is not running here"; return; fi
  if need ADMIN_V4 "E1" && need ADMIN_V6 "E1"; then
    for a in "${ADMIN_V4}" "${ADMIN_V6}"; do
      if docker exec crowdsec cscli allowlists check "${a}" 2>/dev/null | grep -qi allowlist; then ok "E1 ${a} allowlisted"; else bad "E1 ${a} not allowlisted — run ops/allowlist.sh apply first (manual)"; fi
    done
  fi
  local n; n="$(docker exec crowdsec cscli allowlists inspect admin-devices -o json 2>/dev/null | grep -o '"value"' | wc -l | tr -d ' ')"
  [ -n "${n}" ] && ok "E2 admin-devices holds ${n} entries (compare with .env — apply never removes)" || skipc "E2 — list admin-devices not created"
  if docker exec crowdsec cscli metrics show acquisition 2>/dev/null | grep -q access.log; then ok "E3 acquisition reads the access log (lines from the device count here)"; else bad "E3 no acquisition row for the access log"; fi
  skipc "E4–E8 — decisions, bypass, bouncer, console drill: manual, console open"
}

case "${1:-all}" in
  2a) phase_2a ;; 2b) phase_2b ;; 2c) phase_2c ;; 2d) phase_2d ;; 2e) phase_2e ;;
  all) phase_2a; phase_2b; phase_2c; phase_2d; phase_2e ;;
  *) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
echo
echo "  ${pass} PASS  ${fail} FAIL  ${skip} SKIP — a SKIP is a manual row of docs/host-verification-phase-2.md or a missing input."
[ "${fail}" -eq 0 ]
