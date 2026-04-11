#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TPL_DIR="${ROOT_DIR}/ops/templates"
CFG_DIR="${ROOT_DIR}/config"

command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst not found (install gettext-base)"; exit 1; }

if [ ! -f "${ROOT_DIR}/.env" ]; then
  echo "ERROR: .env not found in repo root. Copy .env.example -> .env"
  exit 1
fi

set -a
source "${ROOT_DIR}/.env"
set +a

mkdir -p "${CFG_DIR}/dynamic"

echo "Rendering static config..."
envsubst < "${TPL_DIR}/traefik.yml.tmpl" > "${CFG_DIR}/traefik.yml"
envsubst < "${TPL_DIR}/haproxy.cfg.template.tmpl" > "${CFG_DIR}/haproxy.cfg.template"

echo "Rendering dynamic configs..."
for f in "${TPL_DIR}/dynamic/"*.yml.tmpl; do
  base="$(basename "${f%.tmpl}")"

  # Skip optional templates when their key var is empty
  case "$base" in
    acme-wildcard.yml)
      if [ -z "${ACME_WILDCARD_DOMAIN:-}" ]; then
        echo " -> ${base} (skipped – ACME_WILDCARD_DOMAIN not set)"
        continue
      fi
      ;;
  esac

  out="${CFG_DIR}/dynamic/${base}"
  envsubst < "$f" > "$out"
  echo " -> ${base}"
done

echo "Done. Generated files are in: config/ and config/dynamic/"
