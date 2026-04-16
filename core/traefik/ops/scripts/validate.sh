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
  LOCAL_CIDR_V4
  LOCAL_CIDR_V6
  ACME_EMAIL
  ACME_STORAGE
  ACME_RESOLVER_DNS
  ACME_RESOLVER_HTTP
  ACME_DNS_RESOLVER_1
  ACME_DNS_RESOLVER_2
  TRAEFIK_DASHBOARD_HOST
  TLS_DEFAULT_OPTION
  TRAEFIK_DASHBOARD_TLS_OPTION
  TRAEFIK_DASHBOARD_CERT_RESOLVER
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
fi

echo "OK."
