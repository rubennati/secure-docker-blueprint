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
  TRAEFIK_CONTAINER_NAME
  SOCKET_PROXY_CONTAINER_NAME
  PUBLIC_NETWORK
  SOCKET_PROXY_NETWORK
  CROWDSEC_SECURITY_NETWORK
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
if [ "$missing" -ne 0 ]; then
  echo ""
  echo "An .env written before a variable existed lacks it; .env.example carries each"
  echo "one with its default. CROWDSEC_SECURITY_NETWORK has no Compose default — unset,"
  echo "docker-compose.yml would create a network with an empty name."
  exit 1
fi

# Same defaults render.sh applies, so an .env written before a resolver
# existed validates against what will actually be rendered.
ACME_RESOLVER_TLS="${ACME_RESOLVER_TLS:-tlsResolver}"

# Entrypoint timeouts: Go durations (60s, 2m, 1h30m) or a bare number of
# seconds; 0 means no timeout. render.sh defaults each to Traefik's own value.
for v in TRAEFIK_READ_TIMEOUT TRAEFIK_WRITE_TIMEOUT TRAEFIK_IDLE_TIMEOUT; do
  val="${!v:-}"
  [ -n "${val}" ] || continue
  if ! printf '%s' "${val}" | grep -qE '^([0-9]+(ns|us|ms|s|m|h))+$|^[0-9]+$'; then
    echo "ERROR: ${v} must be a duration such as 60s, 2m or 0 (got '${val}')."
    exit 1
  fi
done

# Memory ceiling, when set: Docker's byte value with an optional unit.
if [ -n "${TRAEFIK_MEMORY:-}" ] && ! printf '%s' "${TRAEFIK_MEMORY}" | grep -qE '^[0-9]+[bkmgBKMG]?$'; then
  echo "ERROR: TRAEFIK_MEMORY must be a size such as 256m or 1g (got '${TRAEFIK_MEMORY}')."
  exit 1
fi

# The trusted proxy ranges render.sh reads: every line must be a range.
CF_LIST="${ROOT_DIR}/ops/cloudflare-ips.txt"
if [ ! -f "${CF_LIST}" ]; then
  echo "ERROR: ${CF_LIST} not found — render.sh needs it for forwardedHeaders.trustedIPs."
  exit 1
fi
cf_ranges=0
while IFS= read -r range; do
  range="${range%%#*}"
  range="$(printf '%s' "${range}" | tr -d '[:space:]')"
  [ -n "${range}" ] || continue
  if ! printf '%s' "${range}" | grep -qE '^[0-9A-Fa-f:.]+/[0-9]{1,3}$'; then
    echo "ERROR: ${CF_LIST}: '${range}' is not an IPv4 or IPv6 range."
    exit 1
  fi
  cf_ranges=$((cf_ranges + 1))
done < "${CF_LIST}"
if [ "${cf_ranges}" -eq 0 ]; then
  echo "ERROR: ${CF_LIST} carries no range."
  exit 1
fi

# Who may set the client address. render.sh applies it; this refuses a value
# it does not know and, after a render, a config/ that disagrees with .env or
# with the ranges file. The shape of the rendered list decides whether it
# trusts anyone (render.sh carries the same function); comment lines inside
# the list, as every release up to v0.9.4 rendered them, are skipped; only the
# key directly under forwardedHeaders: counts; a flow list on the key line is
# read too. rendered_ranges prints the entries by value — quotes, a trailing
# comment and a carriage return from a hand edit stripped — so the comparison
# with the ranges file speaks of the list, not of the editor.
rendered_trusts_ranges() {  # <traefik.yml>
  [ -f "$1" ] || return 1
  awk '/^[[:space:]]*(#|$)/ { next }
       /^[[:space:]]*trustedIPs:[^*]*$/ && prev ~ /^[[:space:]]*forwardedHeaders:[[:space:]]*$/ {
         rest = $0; sub(/^[[:space:]]*trustedIPs:[[:space:]]*/, "", rest); sub(/^&[^[:space:]]+[[:space:]]*/, "", rest)
         if (rest ~ /^\[/) { d = 1; exit (rest ~ /^\[[[:space:]]*\]/) ? 1 : 0 }
         t = 1; next
       }
       t { d = 1; exit ($0 ~ /^[[:space:]]*-[[:space:]]/) ? 0 : 1 }
       { prev = $0 }
       END { if (!d && !t) exit 1 }' "$1"
}
rendered_ranges() {  # <traefik.yml>: the entries of that list, one per line
  awk -v q="'" '/^[[:space:]]*(#|$)/ { next }
       /^[[:space:]]*trustedIPs:[^*]*$/ && prev ~ /^[[:space:]]*forwardedHeaders:[[:space:]]*$/ {
         rest = $0; sub(/^[[:space:]]*trustedIPs:[[:space:]]*/, "", rest); sub(/^&[^[:space:]]+[[:space:]]*/, "", rest)
         if (rest ~ /^\[/) {
           sub(/[[:space:]]*#.*$/, "", rest); gsub(/[][" \t\r]/, "", rest); gsub(q, "", rest)
           n = split(rest, a, ","); for (i = 1; i <= n; i++) if (a[i] != "") print a[i]
           exit
         }
         t = 1; next
       }
       t { if ($0 !~ /^[[:space:]]*-[[:space:]]/) exit
           sub(/^[[:space:]]*-[[:space:]]*/, ""); sub(/[[:space:]]*#.*$/, ""); gsub(/["\r[:space:]]/, ""); gsub(q, "")
           if ($0 != "") print; next }
       { prev = $0 }' "$1"
}
proxy_declared=""
[ -n "${TRAEFIK_FORWARDED_PROXY:-}" ] && proxy_declared=yes
TRAEFIK_FORWARDED_PROXY="$(printf '%s' "${TRAEFIK_FORWARDED_PROXY:-none}" | tr '[:upper:]' '[:lower:]')"
case "${TRAEFIK_FORWARDED_PROXY}" in
  none|cloudflare) ;;
  *) echo "ERROR: TRAEFIK_FORWARDED_PROXY must be none or cloudflare (got '${TRAEFIK_FORWARDED_PROXY}')."; exit 1 ;;
esac

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

# Authentik forward-auth switch: same checks as CrowdSec's — a value other than
# true/false is refused, and with the switch on the address has to be a URL.
auth_switch_declared="${AUTHENTIK_FORWARD_AUTH_ENABLED+yes}"
AUTHENTIK_FORWARD_AUTH_ENABLED="$(printf '%s' "${AUTHENTIK_FORWARD_AUTH_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${AUTHENTIK_FORWARD_AUTH_ENABLED}" in
  true|false) ;;
  *) echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED must be true or false (got '${AUTHENTIK_FORWARD_AUTH_ENABLED}')."; exit 1 ;;
esac
if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = true ]; then
  auth_address="${AUTHENTIK_FORWARD_AUTH_ADDRESS:-http://authentik-server:9000/outpost.goauthentik.io/auth/traefik}"
  if ! printf '%s' "${auth_address}" | grep -qE '^https?://[^[:space:]]+$'; then
    echo "ERROR: AUTHENTIK_FORWARD_AUTH_ADDRESS must be an http:// or https:// URL (got '${auth_address}')."
    echo "       The default is the embedded outpost of core/authentik on this host:"
    echo "       http://authentik-server:9000/outpost.goauthentik.io/auth/traefik"
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
  echo "  Per-domain  set TRAEFIK_DASHBOARD_CERT_RESOLVER to a resolver name:"
  echo "              ${ACME_RESOLVER_DNS}  DNS-01, no public port needed"
  echo "              ${ACME_RESOLVER_HTTP}  HTTP-01, needs public TCP 80"
  echo "              ${ACME_RESOLVER_TLS}  TLS-ALPN-01, needs public TCP 443 and no TLS"
  echo "              terminator in front (a CDN proxy in front breaks it)."
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

  # Before any file is named: a configuration that trusts a list while .env
  # does not say who may set the client address is the migration case, and
  # its message has to be the first thing the operator reads — not a missing
  # dynamic file from a later release (render.sh refuses for the same reason).
  if [ -z "${proxy_declared}" ] && rendered_trusts_ranges "${ROOT_DIR}/config/traefik.yml"; then
    echo "ERROR: config/traefik.yml trusts Cloudflare's ranges but TRAEFIK_FORWARDED_PROXY is not set in .env."
    echo "       Set it to cloudflare if Cloudflare proxies this host's records, to none if not, then run render.sh."
    exit 1
  fi

  # Every file render.sh writes unconditionally has to exist; the two
  # conditional ones have to exist exactly when their switch is set.
  test -f "${ROOT_DIR}/config/haproxy.cfg.template" \
    || { echo "Missing config/haproxy.cfg.template (run render.sh) — docker-compose.yml mounts it"; exit 1; }
  for f in access.yml security-blocks.yml security-chains.yml integrations.yml tls-profiles.yml \
           routers-system.yml redirects.yml servers-transports.yml; do
    test -f "${ROOT_DIR}/config/dynamic/${f}" || { echo "Missing config/dynamic/${f} (run render.sh)"; exit 1; }
  done
  if [ -n "${ACME_WILDCARD_DOMAIN:-}" ]; then
    test -f "${ROOT_DIR}/config/dynamic/acme-wildcard.yml" \
      || { echo "Missing config/dynamic/acme-wildcard.yml although ACME_WILDCARD_DOMAIN is set (run render.sh)"; exit 1; }
  elif [ -f "${ROOT_DIR}/config/dynamic/acme-wildcard.yml" ]; then
    echo "WARNING: config/dynamic/acme-wildcard.yml exists but ACME_WILDCARD_DOMAIN is empty —"
    echo "         a wildcard router from an earlier render is still in place. Remove the file"
    echo "         (bash ops/scripts/reset-templates.sh, then render.sh) if the wildcard is no longer wanted."
  fi

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

  # The trusted senders, both directions: the rendered entrypoints carry a
  # list exactly when the switch says cloudflare, that list is the ranges file
  # as it is now, the CrowdSec middlewares carry the same list exactly then,
  # and no middleware names a header the bouncer would read from any sender.
  rendered_trusts_cf=false
  rendered_trusts_ranges "${ROOT_DIR}/config/traefik.yml" && rendered_trusts_cf=true
  if grep -qsE '^[[:space:]]*forwardedHeadersCustomName:' "${ROOT_DIR}/config/dynamic/crowdsec.yml" 2>/dev/null; then
    echo "ERROR: config/dynamic/crowdsec.yml sets forwardedHeadersCustomName — the bouncer would read that header"
    echo "       from any sender, Traefik deletes only X-Forwarded-*. The templates never set it; run render.sh."
    exit 1
  fi
  if [ "${TRAEFIK_FORWARDED_PROXY}" = cloudflare ]; then
    if [ "${rendered_trusts_cf}" != true ]; then
      echo "ERROR: TRAEFIK_FORWARDED_PROXY=cloudflare but config/traefik.yml trusts no Cloudflare range — run render.sh."
      exit 1
    fi
    if [ "$(rendered_ranges "${ROOT_DIR}/config/traefik.yml" | sort)" != "$(grep -vE '^[[:space:]]*(#|$)' "${CF_LIST}" | sed 's/#.*//; s/[[:space:]]//g' | sort)" ]; then
      echo "ERROR: the list in config/traefik.yml differs from ops/cloudflare-ips.txt — the ranges file changed"
      echo "       since the last render, or the block was edited by hand — run render.sh, then recreate the traefik container."
      exit 1
    fi
    if [ -f "${ROOT_DIR}/config/dynamic/crowdsec.yml" ] && ! grep -qsE '^[[:space:]]*forwardedHeadersTrustedIPs:' "${ROOT_DIR}/config/dynamic/crowdsec.yml"; then
      echo "ERROR: TRAEFIK_FORWARDED_PROXY=cloudflare but config/dynamic/crowdsec.yml carries no trusted-proxy list — run render.sh."
      exit 1
    fi
    test -f "${ROOT_DIR}/config/host/cloudflare-ranges.nft" || { echo "Missing config/host/cloudflare-ranges.nft (run render.sh)"; exit 1; }
  elif [ "${rendered_trusts_cf}" = true ]; then
    # the undeclared case was refused above, before the file checks
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/traefik.yml still trusts Cloudflare's ranges — run render.sh."
    exit 1
  elif grep -qsE '^[[:space:]]*forwardedHeadersTrustedIPs:' "${ROOT_DIR}/config/dynamic/crowdsec.yml" 2>/dev/null; then
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/dynamic/crowdsec.yml carries a trusted-proxy list — run render.sh."
    exit 1
  elif [ -f "${ROOT_DIR}/config/host/cloudflare-ranges.nft" ]; then
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/host/cloudflare-ranges.nft exists — run render.sh, and remove the installed copy from the host firewall."
    exit 1
  fi

  # The Authentik middleware, both directions, like the CrowdSec integration.
  rendered_auth=false
  grep -qsE '^[[:space:]]*(auth-authentik|sec-authentik):' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null && rendered_auth=true
  if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = true ]; then
    if [ "${rendered_auth}" != true ] || [ ! -f "${ROOT_DIR}/config/dynamic/authentik.yml" ]; then
      echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED=true but config/dynamic carries no forward-auth middleware — run render.sh."
      exit 1
    fi
  elif [ "${rendered_auth}" = true ]; then
    if [ -z "${auth_switch_declared}" ]; then
      echo "ERROR: config/dynamic carries the Authentik forward-auth middleware but AUTHENTIK_FORWARD_AUTH_ENABLED is not set in .env."
      echo "       Set it to true to keep the middleware (plus AUTHENTIK_FORWARD_AUTH_ADDRESS), or to false to remove it, then run render.sh."
    else
      echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED=false but config/dynamic still carries the forward-auth middleware — run render.sh."
    fi
    exit 1
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
