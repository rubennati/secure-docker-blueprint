#!/usr/bin/env bash
# =========================================================
# Render dnsmasq templates → config/
# Usage: ./ops/scripts/render.sh
# =========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE_DIR="$PROJECT_DIR/ops/templates"
CONFIG_DIR="$PROJECT_DIR/config"

# Load .env
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env first." >&2
  exit 1
fi
set -a
# shellcheck source=/dev/null
source "$PROJECT_DIR/.env"
set +a

mkdir -p "$CONFIG_DIR"

echo "Rendering dnsmasq.conf ..."
envsubst < "$TEMPLATE_DIR/dnsmasq.conf.tmpl" > "$CONFIG_DIR/dnsmasq.conf"

echo "Done. Config written to: $CONFIG_DIR/dnsmasq.conf"
