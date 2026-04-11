#!/bin/sh
# =========================================================
# Convert PEM certificate to PFX (PKCS#12) format.
# Useful for Windows, Synology, and other devices.
#
# Usage: ./scripts/convert-to-pfx.sh <domain> <password>
# =========================================================
set -eu

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <domain> <password>"
  echo "Example: $0 example.com MySecretPass"
  exit 1
fi

DOMAIN="$1"
PASSWORD="$2"
DIR="/output/${DOMAIN}"

if [ ! -f "${DIR}/privkey.pem" ]; then
  echo "Error: ${DIR}/privkey.pem not found."
  echo "Issue a certificate first with: ./scripts/issue.sh"
  exit 1
fi

openssl pkcs12 -export \
  -out "${DIR}/${DOMAIN}.pfx" \
  -inkey "${DIR}/privkey.pem" \
  -in "${DIR}/cert.pem" \
  -certfile "${DIR}/ca.pem" \
  -password "pass:${PASSWORD}"

echo "PFX created: ${DIR}/${DOMAIN}.pfx"
