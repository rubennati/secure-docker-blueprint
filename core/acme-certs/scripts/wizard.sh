#!/bin/sh
# =========================================================
# Interactive wizard for issuing certificates.
#
# Usage:
#   ./scripts/wizard.sh                    # fully interactive
#   ./scripts/wizard.sh example.com        # single domain
#   ./scripts/wizard.sh example.com -w     # domain + wildcard
#   ./scripts/wizard.sh example.com --wild # domain + wildcard
#
# Run from the acme-certs directory.
# =========================================================
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Error: ${ENV_FILE} not found."
  echo "Copy .env.example to .env first."
  exit 1
fi

# Read defaults from .env
DEFAULT_KEYLENGTH="$(grep '^CERT_KEYLENGTH=' "${ENV_FILE}" | cut -d= -f2- || echo "ec-256")"
DEFAULT_SERVER="$(grep '^ACME_SERVER=' "${ENV_FILE}" | cut -d= -f2- || echo "letsencrypt")"

# Parse CLI arguments
ARG_DOMAIN="${1:-}"
ARG_WILDCARD=""
if [ "${2:-}" = "-w" ] || [ "${2:-}" = "--wild" ] || [ "${2:-}" = "--wildcard" ]; then
  ARG_WILDCARD="yes"
fi

echo ""
echo "Certificate Wizard"
echo "=================="
echo ""

# Domain
if [ -n "${ARG_DOMAIN}" ]; then
  DOMAIN="${ARG_DOMAIN}"
  echo "Domain: ${DOMAIN}"
else
  printf "Domain: "
  read DOMAIN
  if [ -z "${DOMAIN}" ]; then
    echo "Error: Domain is required."
    exit 1
  fi
fi

# Validate domain (basic check)
case "${DOMAIN}" in
  *..* | *.* ) ;; # has at least one dot, OK
  *)
    echo "Error: '${DOMAIN}' doesn't look like a valid domain."
    exit 1
    ;;
esac

# Wildcard
if [ -n "${ARG_WILDCARD}" ]; then
  SAN="*.${DOMAIN}"
  echo "Wildcard: ${SAN}"
else
  printf "Type: [1] Single domain  [2] Wildcard (*.%s)  [1]: " "${DOMAIN}"
  read CERT_TYPE
  case "${CERT_TYPE}" in
    2)
      SAN="*.${DOMAIN}"
      ;;
    *)
      SAN=""
      ;;
  esac
fi

# Key type
printf "Key type [ec-256|ec-384|2048|3072|4096] [%s]: " "${DEFAULT_KEYLENGTH}"
read KEYLENGTH
KEYLENGTH="${KEYLENGTH:-${DEFAULT_KEYLENGTH}}"

# Validate key type
case "${KEYLENGTH}" in
  ec-256|ec-384|2048|3072|4096) ;;
  *)
    echo "Error: Invalid key type '${KEYLENGTH}'. Use: ec-256, ec-384, 2048, 3072, 4096"
    exit 1
    ;;
esac

# ACME server
printf "ACME server [letsencrypt|zerossl|buypass] [%s]: " "${DEFAULT_SERVER}"
read SERVER
SERVER="${SERVER:-${DEFAULT_SERVER}}"

# Validate ACME server
case "${SERVER}" in
  letsencrypt|zerossl|buypass) ;;
  *)
    echo "Error: Invalid ACME server '${SERVER}'. Use: letsencrypt, zerossl, buypass"
    exit 1
    ;;
esac

echo ""
echo "Configuration:"
echo "  Domain:     ${DOMAIN}"
if [ -n "${SAN}" ]; then
  echo "  Wildcard:   ${SAN}"
else
  echo "  Type:       single domain (no wildcard)"
fi
echo "  Key type:   ${KEYLENGTH}"
echo "  ACME:       ${SERVER}"
echo ""

printf "Issue certificate now? [y/N]: "
read CONFIRM
case "${CONFIRM}" in
  y|Y|yes|YES)
    docker compose exec \
      -e CERT_DOMAIN="${DOMAIN}" \
      -e CERT_SAN="${SAN}" \
      -e CERT_KEYLENGTH="${KEYLENGTH}" \
      -e ACME_SERVER="${SERVER}" \
      acme-certs /scripts/issue.sh
    ;;
  *)
    echo "Cancelled."
    exit 0
    ;;
esac

echo ""
echo "Done. Output at:"
echo "  ${ROOT_DIR}/volumes/output/${DOMAIN}/"
