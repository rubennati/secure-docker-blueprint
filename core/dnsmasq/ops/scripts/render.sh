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

# Wildcard zones: one address= line per family that is set. An empty address
# would render address=/zone/, which answers NXDOMAIN for the whole zone.
DNS_WILDCARD_LINES=""
for n in 1 2 3 4 5 6 7 8 9; do
  dom_var="DNS_WILDCARD_${n}_DOMAIN"; v4_var="DNS_WILDCARD_${n}_IP"; v6_var="DNS_WILDCARD_${n}_IP6"
  dom="${!dom_var:-}"; v4="${!v4_var:-}"; v6="${!v6_var:-}"
  [[ -n "$dom" ]] || continue
  if [[ -z "$v4" && -z "$v6" ]]; then
    echo "ERROR: $dom_var=$dom has neither $v4_var nor $v6_var." >&2; exit 1
  fi
  # _IP took either family before _IP6 existed; an IPv6 address there still works.
  if [[ -n "$v4" && ! "$v4" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && ! "$v4" =~ ^[0-9A-Fa-f:]+$ ]]; then
    echo "ERROR: $v4_var=$v4 is not an IP address." >&2; exit 1
  fi
  if [[ -n "$v6" && ! "$v6" =~ ^[0-9A-Fa-f:]+$ ]]; then
    echo "ERROR: $v6_var=$v6 is not an IPv6 address." >&2; exit 1
  fi
  [[ -n "$v4" ]] && DNS_WILDCARD_LINES+="address=/${dom}/${v4}"$'\n'
  [[ -n "$v6" ]] && DNS_WILDCARD_LINES+="address=/${dom}/${v6}"$'\n'
  [[ -n "$v6" || "$v4" == *:* ]] || echo "NOTE: $dom has no IPv6 address ($v6_var) — unless another slot gives one, IPv6-preferring clients resolve it upstream." >&2
done
export DNS_WILDCARD_LINES

echo "Rendering dnsmasq.conf ..."
envsubst < "$TEMPLATE_DIR/dnsmasq.conf.tmpl" > "$CONFIG_DIR/dnsmasq.conf"

echo "Done. Config written to: $CONFIG_DIR/dnsmasq.conf"
