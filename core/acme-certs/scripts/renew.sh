#!/bin/sh
# =========================================================
# Renew an existing certificate and re-export.
# =========================================================
set -eu

: "${CERT_DOMAIN:?CERT_DOMAIN missing}"

ACME_HOME="/acme.sh"
OUT_DIR="/output/${CERT_DOMAIN}"

mkdir -p "${OUT_DIR}"

acme.sh --home "${ACME_HOME}" --renew -d "${CERT_DOMAIN}"

acme.sh --home "${ACME_HOME}" --install-cert -d "${CERT_DOMAIN}" \
  --key-file       "${OUT_DIR}/privkey.pem" \
  --cert-file      "${OUT_DIR}/cert.pem" \
  --fullchain-file "${OUT_DIR}/fullchain.pem" \
  --ca-file        "${OUT_DIR}/ca.pem"

chmod 600 "${OUT_DIR}/privkey.pem" || true

echo "Renewal complete: ${OUT_DIR}"
