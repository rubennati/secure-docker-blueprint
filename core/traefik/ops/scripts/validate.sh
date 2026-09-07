#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ ! -f "${ROOT_DIR}/.env" ]; then
  echo "ERROR: .env not found. Copy .env.example -> .env"
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
