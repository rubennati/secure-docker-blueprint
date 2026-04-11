#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Removing generated config files..."
rm -f "${ROOT_DIR}/config/traefik.yml" \
      "${ROOT_DIR}/config/haproxy.cfg.template" || true

rm -f "${ROOT_DIR}/config/dynamic"/*.yml 2>/dev/null || true

echo "Done. Templates stay in ops/templates/."
