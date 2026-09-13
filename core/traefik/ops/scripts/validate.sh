#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ ! -f "${ROOT_DIR}/.env" ]; then
  echo "ERROR: .env not found. Copy .env.example -> .env"
  exit 1
fi

# Check the syntax before sourcing. `set -a; source .env` runs the file as bash,
# so an unquoted value containing a space is parsed as a command and the operator
# gets a bash error naming the second word, not the variable. Refuse the file
# first and say which line is wrong.
env_syntax_errors=0
while IFS= read -r line_no_and_text; do
  line_no="${line_no_and_text%%:*}"
  line="${line_no_and_text#*:}"
  case "${line}" in
    ''|'#'*) continue ;;
  esac
  # Must be NAME=... — anything else is not an assignment bash will accept here.
  if ! printf '%s' "${line}" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*='; then
    echo "ERROR: .env line ${line_no} is not a NAME=value assignment: ${line}"
    env_syntax_errors=$((env_syntax_errors + 1))
    continue
  fi
  value="${line#*=}"
  # A value wrapped in a matching pair of quotes is fine whatever is inside it.
  # Compare the first and last character rather than globbing for a quote, which
  # needs escaping that is easy to get wrong and silently matches nothing.
  first_char="${value%"${value#?}"}"
  last_char="${value#"${value%?}"}"
  if [ "${#value}" -ge 2 ] && [ "${first_char}" = "${last_char}" ] \
     && { [ "${first_char}" = '"' ] || [ "${first_char}" = "'" ]; }; then
    continue
  fi
  # An unquoted value with whitespace is parsed as a command by `source`.
  case "${value}" in
    *[[:space:]]*)
      echo "ERROR: .env line ${line_no} has an unquoted value containing a space — quote it: ${line}"
      env_syntax_errors=$((env_syntax_errors + 1))
      ;;
  esac
done < <(grep -n '' "${ROOT_DIR}/.env")

if [ "${env_syntax_errors}" -gt 0 ]; then
  echo ""
  echo "Refusing to continue: ${env_syntax_errors} syntax problem(s) in .env."
  echo "render.sh sources the same file, so it would fail the same way with a less useful message."
  exit 1
fi

set -a
source "${ROOT_DIR}/.env"
set +a

REQUIRED=(
  TZ
  TRAEFIK_IMAGE
  SOCKET_PROXY_IMAGE
  PUBLIC_NETWORK
  SOCKET_PROXY_NETWORK
  TRAEFIK_HTTP_PORT
  TRAEFIK_HTTPS_PORT
  DOCKER_SOCKET_PROXY_ENDPOINT
  TAILSCALE_CIDR_V4
  TAILSCALE_CIDR_V6
  ACME_EMAIL
  ACME_STORAGE
  ACME_RESOLVER_DNS
  ACME_RESOLVER_HTTP
  ACME_DNS_RESOLVER_1
  ACME_DNS_RESOLVER_2
  TRAEFIK_DASHBOARD_HOST
  TLS_DEFAULT_OPTION
  TRAEFIK_DASHBOARD_TLS_OPTION
  TRAEFIK_LOG_LEVEL
  TRAEFIK_LOG_FORMAT
  TRAEFIK_LOG_FILE
  TRAEFIK_ACCESSLOG_FORMAT
  TRAEFIK_ACCESSLOG_FILE
  TRAEFIK_ACCESSLOG_BUFFER
  DSP_LOG_LEVEL
  DSP_SOCKET_PATH
  DSP_BIND_CONFIG
  DSP_POST
)

missing=0
for v in "${REQUIRED[@]}"; do
  if [ -z "${!v:-}" ]; then
    echo "MISSING: ${v}"
    missing=1
  fi
done
[ "$missing" -eq 0 ] || exit 1

# CrowdSec reverse-proxy remediation switch. render.sh applies it; this checks
# that what .env says is complete and that config/ agrees with it.
switch_declared="${CROWDSEC_BOUNCER_ENABLED+yes}"
CROWDSEC_BOUNCER_ENABLED="$(printf '%s' "${CROWDSEC_BOUNCER_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${CROWDSEC_BOUNCER_ENABLED}" in
  true|false) ;;
  *) echo "ERROR: CROWDSEC_BOUNCER_ENABLED must be true or false (got '${CROWDSEC_BOUNCER_ENABLED}')."; exit 1 ;;
esac
if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
  if [ -z "${CROWDSEC_BOUNCER_KEY:-}" ]; then
    echo "ERROR: CROWDSEC_BOUNCER_ENABLED=true but CROWDSEC_BOUNCER_KEY is empty."
    echo "       Generate one on the engine: docker exec crowdsec cscli bouncers add traefik-bouncer"
    exit 1
  fi
  version="${CROWDSEC_BOUNCER_PLUGIN_VERSION:-v1.7.1}"
  if ! printf '%s' "${version}" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: CROWDSEC_BOUNCER_PLUGIN_VERSION must be a release tag like v1.7.1 (got '${version}')."
    echo "       Releases: https://github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin/releases"
    exit 1
  fi
fi

# Warn about sentinel values (not a hard fail – HTTP-01 users don't need this)
if [ "${CF_DNS_API_TOKEN:-}" = "__REPLACE_ME__" ]; then
  echo "WARNING: CF_DNS_API_TOKEN is still set to __REPLACE_ME__. DNS-01 (wildcard certs) will fail."
fi

# Dashboard certificate strategy.
# The dashboard follows the same rule as application routers: a wildcard that
# covers its hostname makes a per-router resolver unnecessary. Coverage is a
# string relationship between two independent variables, not an assumption --
# *.example.com matches exactly one label, so traefik.admin.example.com and a
# dashboard on a different domain are NOT covered.
dashboard_covered_by_wildcard() {
  local host="$1" wild="${2:-}" label
  [ -n "$wild" ] || return 1
  [ "$host" = "$wild" ] && return 0          # apex, carried by the cert's main domain
  label="${host%".$wild"}"
  [ "$label" = "$host" ] && return 1         # different domain entirely
  [ -n "$label" ] || return 1
  [ "${label#*.}" = "$label" ]               # exactly one label below the wildcard
}

if dashboard_covered_by_wildcard "${TRAEFIK_DASHBOARD_HOST}" "${ACME_WILDCARD_DOMAIN:-}"; then
  if [ -n "${TRAEFIK_DASHBOARD_CERT_RESOLVER:-}" ]; then
    echo "WARNING: *.${ACME_WILDCARD_DOMAIN} already covers ${TRAEFIK_DASHBOARD_HOST}, and TRAEFIK_DASHBOARD_CERT_RESOLVER is set."
    echo "         Traefik will request a second certificate for that hostname, publishing it in Certificate Transparency logs."
    echo "         Leave the variable empty to serve the wildcard instead."
  fi
elif [ -z "${TRAEFIK_DASHBOARD_CERT_RESOLVER:-}" ]; then
  echo "SELECT A CERTIFICATE STRATEGY — neither is configured for ${TRAEFIK_DASHBOARD_HOST}."
  echo
  echo "  Wildcard    set ACME_WILDCARD_DOMAIN to the parent domain of that host,"
  echo "              and leave TRAEFIK_DASHBOARD_CERT_RESOLVER empty."
  echo "  Per-domain  set TRAEFIK_DASHBOARD_CERT_RESOLVER to a resolver name"
  echo "              (${ACME_RESOLVER_DNS} for DNS-01, ${ACME_RESOLVER_HTTP} for HTTP-01)."
  echo
  echo "  Both are supported. The shipped .env.example picks neither on purpose, so"
  echo "  the choice is made rather than inherited. Until one is set, Traefik would"
  echo "  answer HTTPS for that host with its self-signed default certificate."
  echo "  See core/traefik/README.md -> Certificate strategy."
  exit 1
fi

# Runtime files (after render)
if [ -f "${ROOT_DIR}/config/traefik.yml" ]; then
  # ensure no unsubstituted vars remain
  if grep -R '\${[A-Za-z_][A-Za-z0-9_]*}' -n "${ROOT_DIR}/config" >/dev/null 2>&1; then
    echo "ERROR: Unresolved variables found in generated config/."
    grep -R '\${[A-Za-z_][A-Za-z0-9_]*}' -n "${ROOT_DIR}/config" || true
    exit 1
  fi

  # check expected dynamic files exist
  for f in access.yml security-blocks.yml security-chains.yml integrations.yml tls-profiles.yml routers-system.yml; do
    test -f "${ROOT_DIR}/config/dynamic/${f}" || { echo "Missing config/dynamic/${f} (run render.sh)"; exit 1; }
  done

  # The rendered state has to match the switch. Both directions are errors: the
  # integration present while the switch is off is the drift render.sh refuses
  # to paper over, and the switch on without the rendered halves means render.sh
  # has not run since the switch was set.
  rendered_plugin=false; grep -qsE '^experimental:' "${ROOT_DIR}/config/traefik.yml" && rendered_plugin=true
  rendered_mw=false; grep -qsE '^[[:space:]]*crowdsec-(basic|appsec):' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null && rendered_mw=true
  if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
    if [ "${rendered_plugin}" != true ] || [ ! -f "${ROOT_DIR}/config/dynamic/crowdsec.yml" ]; then
      echo "ERROR: CROWDSEC_BOUNCER_ENABLED=true but config/ does not carry the integration — run render.sh."
      exit 1
    fi
  else
    if [ "${rendered_plugin}" = true ] || [ "${rendered_mw}" = true ]; then
      if [ -z "${switch_declared}" ]; then
        echo "ERROR: config/ carries the CrowdSec integration but CROWDSEC_BOUNCER_ENABLED is not set in .env."
        echo "       Set it to true to keep the integration (plus CROWDSEC_BOUNCER_PLUGIN_VERSION and"
        echo "       CROWDSEC_BOUNCER_KEY), or to false to remove it, then run render.sh."
      else
        echo "ERROR: CROWDSEC_BOUNCER_ENABLED=false but config/ still carries the integration — run render.sh."
      fi
      exit 1
    fi
  fi

  # CrowdSec bouncer key. envsubst turns an unset CROWDSEC_BOUNCER_KEY into an
  # empty string, so a bouncer that cannot authenticate renders without a word of
  # complaint. The key is required only where a CrowdSec middleware was actually
  # rendered — the default-off blueprint must validate without one.
  #
  # The grep is a pre-filter, not the decision: it keeps a default-off install
  # free of any Python dependency. When it matches, the rendered YAML is parsed
  # and that parse decides.
  if grep -rqE '^[[:space:]]*crowdsec-(basic|appsec):' "${ROOT_DIR}/config/dynamic" 2>/dev/null; then
    CROWDSEC_CHECK="${ROOT_DIR}/../../scripts/ci/check-crowdsec-config.py"
    if [ -f "${CROWDSEC_CHECK}" ] && command -v python3 >/dev/null 2>&1; then
      python3 "${CROWDSEC_CHECK}" --rendered "${ROOT_DIR}/config" || exit 1
    else
      echo "ERROR: a CrowdSec middleware is enabled in the rendered config, but the"
      echo "       bouncer key check could not run. It needs python3 with PyYAML and"
      echo "       scripts/ci/check-crowdsec-config.py. Install them, or confirm by hand"
      echo "       that crowdsecLapiKey is not empty before starting Traefik."
      exit 1
    fi
  fi
fi

echo "OK."
