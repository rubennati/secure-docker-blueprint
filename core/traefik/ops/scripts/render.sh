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

# ---------------------------------------------------------------------------
# CrowdSec reverse-proxy remediation: one switch in .env
#
# CROWDSEC_BOUNCER_ENABLED decides whether two things are rendered — the plugin
# block between the crowdsec-bouncer markers in traefik.yml.tmpl, and the
# middleware file dynamic/crowdsec.yml.tmpl. Absent means false. Any value other
# than true or false is refused, because envsubst would otherwise pass whatever
# was typed straight into the configuration.
#
# The switch is the only supported way to enable the integration. The templates
# are tracked files; editing them to enable something is undone by the next
# checkout, and a render after that checkout would silently write a
# configuration without the plugin and without the middlewares while the
# running container still has both. The guard below catches exactly that
# state: config/ carries the integration, .env does not say so.
# ---------------------------------------------------------------------------
switch_declared="${CROWDSEC_BOUNCER_ENABLED+yes}"
CROWDSEC_BOUNCER_ENABLED="$(printf '%s' "${CROWDSEC_BOUNCER_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${CROWDSEC_BOUNCER_ENABLED}" in
  true|false) ;;
  *)
    echo "ERROR: CROWDSEC_BOUNCER_ENABLED must be true or false (got '${CROWDSEC_BOUNCER_ENABLED}')."
    exit 1
    ;;
esac
export CROWDSEC_BOUNCER_PLUGIN_VERSION="${CROWDSEC_BOUNCER_PLUGIN_VERSION:-v1.7.1}"

rendered_has_bouncer() {
  grep -qsE '^experimental:' "${CFG_DIR}/traefik.yml" && return 0
  grep -qsE '^[[:space:]]*crowdsec-(basic|appsec):' "${CFG_DIR}"/dynamic/*.yml 2>/dev/null
}

if rendered_has_bouncer; then
  if [ -z "${switch_declared}" ]; then
    echo "ERROR: config/ carries the CrowdSec integration (plugin block in traefik.yml or a"
    echo "       crowdsec-* middleware under dynamic/), but CROWDSEC_BOUNCER_ENABLED is not set"
    echo "       in .env. Rendering now would remove both while Traefik keeps running with them."
    echo ""
    echo "       Keep it:   CROWDSEC_BOUNCER_ENABLED=true"
    echo "                  CROWDSEC_BOUNCER_PLUGIN_VERSION=<the version config/traefik.yml names>"
    echo "                  CROWDSEC_BOUNCER_KEY=<the key config/dynamic names>"
    echo "       Remove it: CROWDSEC_BOUNCER_ENABLED=false — after removing crowdsec-*@file from"
    echo "                  every router, or those routers go dark."
    echo "       Then run render.sh again. See core/traefik/README.md, 'Migrating an installation"
    echo "       that enabled the integration before the switch'."
    exit 1
  fi
  if [ "${CROWDSEC_BOUNCER_ENABLED}" = false ]; then
    echo "NOTICE: CROWDSEC_BOUNCER_ENABLED=false — the CrowdSec plugin and middlewares are removed"
    echo "        from config/. A router still listing crowdsec-*@file is disabled by Traefik"
    echo "        until it is relabelled. The plugin block is static configuration: restart Traefik."
  fi
fi

mkdir -p "${CFG_DIR}/dynamic"

# Every output is written to a temporary file next to its destination and moved
# into place with mv — a rename on the same filesystem, which is atomic. Traefik
# watches config/dynamic/ and re-reads the whole directory on any change; a plain
# `> file` truncates first and fills afterwards, and a read that lands in between
# sees an empty file: every middleware it defined "does not exist" for that
# reload, and every router naming one is disabled until the next reload, up to
# providersThrottleDuration later. That happened on a host on 2026-09-14 during
# a render — `middleware "acc-public@file" does not exist` on 18 routers for one
# reload cycle. With rename, the watcher only ever sees complete files.
place() {  # place <destination>: stdin -> destination, atomically
  local dest="$1" tmp
  tmp="$(mktemp "${dest}.XXXXXX")"
  cat > "${tmp}"
  chmod 0644 "${tmp}"
  mv -f "${tmp}" "${dest}"
}

echo "Rendering static config..."
if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
  envsubst < "${TPL_DIR}/traefik.yml.tmpl" | place "${CFG_DIR}/traefik.yml"
  echo " -> traefik.yml (CrowdSec bouncer plugin ${CROWDSEC_BOUNCER_PLUGIN_VERSION} declared)"
else
  # Drop the marker-delimited plugin block; the markers are comments and go with it.
  envsubst < "${TPL_DIR}/traefik.yml.tmpl" \
    | sed '/^# >>> crowdsec-bouncer/,/^# <<< crowdsec-bouncer/d' | place "${CFG_DIR}/traefik.yml"
  echo " -> traefik.yml (no plugin — CROWDSEC_BOUNCER_ENABLED=false)"
fi
envsubst < "${TPL_DIR}/haproxy.cfg.template.tmpl" | place "${CFG_DIR}/haproxy.cfg.template"

echo "Rendering dynamic configs..."
for f in "${TPL_DIR}/dynamic/"*.yml.tmpl; do
  base="$(basename "${f%.tmpl}")"

  out="${CFG_DIR}/dynamic/${base}"

  # Optional templates and optional lines, keyed off .env
  case "$base" in
    crowdsec.yml)
      # Rendered only with the switch on. With it off the file must not exist:
      # a middleware file left behind would keep the integration alive in the
      # dynamic configuration after the operator switched it off.
      if [ "${CROWDSEC_BOUNCER_ENABLED}" != true ]; then
        rm -f "$out"
        echo " -> ${base} (skipped — CROWDSEC_BOUNCER_ENABLED=false)"
        continue
      fi
      ;;
    acme-wildcard.yml)
      if [ -z "${ACME_WILDCARD_DOMAIN:-}" ]; then
        echo " -> ${base} (skipped – ACME_WILDCARD_DOMAIN not set)"
        continue
      fi
      ;;
    routers-system.yml)
      # An empty dashboard resolver means the wildcard covers the dashboard
      # host, so the router carries no certResolver and Traefik serves the
      # wildcard through SNI — the same way application routers work. Drop the
      # line rather than render "certResolver:" with no value.
      if [ -z "${TRAEFIK_DASHBOARD_CERT_RESOLVER:-}" ]; then
        envsubst < "$f" | sed '/^[[:space:]]*certResolver:[[:space:]]*$/d' | place "$out"
        echo " -> ${base} (dashboard uses the wildcard – no certResolver)"
        continue
      fi
      ;;
  esac

  envsubst < "$f" | place "$out"
  echo " -> ${base}"
done

echo "Done. Generated files are in: config/ and config/dynamic/"
