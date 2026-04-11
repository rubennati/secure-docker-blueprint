#!/bin/sh
# =========================================================
# Interactive wizard for issuing certificates.
# Reads defaults from .env, then prompts for overrides.
#
# Run from the acme-certs directory:
#   ./scripts/wizard.sh
# =========================================================
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Error: ${ENV_FILE} not found."
  echo "Copy .env.example to .env first."
  exit 1
fi

echo ""
echo "Certificate Wizard"
echo "=================="
echo ""

# Read defaults from .env
DEFAULT_DOMAIN="$(grep '^CERT_DOMAIN=' "${ENV_FILE}" | cut -d= -f2- || true)"
DEFAULT_SAN="$(grep '^CERT_SAN=' "${ENV_FILE}" | cut -d= -f2- || true)"
DEFAULT_KEYLENGTH="$(grep '^CERT_KEYLENGTH=' "${ENV_FILE}" | cut -d= -f2- || true)"
DEFAULT_SERVER="$(grep '^ACME_SERVER=' "${ENV_FILE}" | cut -d= -f2- || true)"

printf "Domain [%s]: " "${DEFAULT_DOMAIN:-example.com}"
read DOMAIN
DOMAIN="${DOMAIN:-${DEFAULT_DOMAIN:-example.com}}"

printf "Wildcard / SAN (leave empty for none) [%s]: " "${DEFAULT_SAN:-}"
read SAN
SAN="${SAN:-${DEFAULT_SAN:-}}"

printf "Key type [ec-256|ec-384|2048|3072|4096] [%s]: " "${DEFAULT_KEYLENGTH:-ec-256}"
read KEYLENGTH
KEYLENGTH="${KEYLENGTH:-${DEFAULT_KEYLENGTH:-ec-256}}"

printf "ACME server [letsencrypt|zerossl|buypass] [%s]: " "${DEFAULT_SERVER:-letsencrypt}"
read SERVER
SERVER="${SERVER:-${DEFAULT_SERVER:-letsencrypt}}"

echo ""
echo "Configuration:"
echo "  Domain:     ${DOMAIN}"
echo "  SAN:        ${SAN:-<none>}"
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
