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
. "${ROOT_DIR}/ops/scripts/exposure-profile.sh"

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

# AppSec inspection is a second switch inside the same plugin: true places
# threat-crowdsec-appsec at the entrypoint instead of threat-crowdsec. It needs
# the engine's AppSec component answering on crowdsec:7422 (see
# dynamic/crowdsec.yml.tmpl) and the bouncer switch on.
CROWDSEC_APPSEC_ENABLED="$(printf '%s' "${CROWDSEC_APPSEC_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${CROWDSEC_APPSEC_ENABLED}" in
  true|false) ;;
  *)
    echo "ERROR: CROWDSEC_APPSEC_ENABLED must be true or false (got '${CROWDSEC_APPSEC_ENABLED}')."
    exit 1
    ;;
esac
if [ "${CROWDSEC_APPSEC_ENABLED}" = true ] && [ "${CROWDSEC_BOUNCER_ENABLED}" != true ]; then
  echo "ERROR: CROWDSEC_APPSEC_ENABLED=true needs CROWDSEC_BOUNCER_ENABLED=true — AppSec inspection runs inside the bouncer plugin."
  exit 1
fi

# The entrypoint middlewares (traefik.yml.tmpl, entryPoints.websecure.http):
# the threat position when the bouncer is on, then compression — in that
# order, so a banned address is refused before any work is done on its
# request. Every router on the entrypoint gets them in front of its own list.
ENTRYPOINT_MIDDLEWARES_YAML="        - compress@file"
ENTRYPOINT_THREAT=""
if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
  ENTRYPOINT_THREAT="threat-crowdsec"
  [ "${CROWDSEC_APPSEC_ENABLED}" = true ] && ENTRYPOINT_THREAT="threat-crowdsec-appsec"
  ENTRYPOINT_MIDDLEWARES_YAML="        - ${ENTRYPOINT_THREAT}@file"$'\n'"${ENTRYPOINT_MIDDLEWARES_YAML}"
fi
export ENTRYPOINT_MIDDLEWARES_YAML

# Authentik forward-auth: the same shape. AUTHENTIK_FORWARD_AUTH_ENABLED decides
# whether dynamic/authentik.yml.tmpl is rendered; the address defaults to the
# embedded outpost of a core/authentik on this host.
auth_switch_declared="${AUTHENTIK_FORWARD_AUTH_ENABLED+yes}"
AUTHENTIK_FORWARD_AUTH_ENABLED="$(printf '%s' "${AUTHENTIK_FORWARD_AUTH_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${AUTHENTIK_FORWARD_AUTH_ENABLED}" in
  true|false) ;;
  *)
    echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED must be true or false (got '${AUTHENTIK_FORWARD_AUTH_ENABLED}')."
    exit 1
    ;;
esac
export AUTHENTIK_FORWARD_AUTH_ADDRESS="${AUTHENTIK_FORWARD_AUTH_ADDRESS:-http://authentik-server:9000/outpost.goauthentik.io/auth/traefik}"

# Resolver names are keys in the rendered YAML. An .env written before a
# resolver existed would render an empty key and an unparseable document, so
# each one carries the default from .env.example.
export ACME_RESOLVER_DNS="${ACME_RESOLVER_DNS:-cloudflare-dns}"
export ACME_RESOLVER_HTTP="${ACME_RESOLVER_HTTP:-httpResolver}"
export ACME_RESOLVER_TLS="${ACME_RESOLVER_TLS:-tlsResolver}"

# The HSTS base every header profile of the model carries (dynamic/model.yml).
# Two years, as every chain sent before; digits only.
export HSTS_MAX_AGE="${HSTS_MAX_AGE:-63072000}"
if ! printf '%s' "${HSTS_MAX_AGE}" | grep -qE '^[0-9]+$'; then
  echo "ERROR: HSTS_MAX_AGE must be a number of seconds (got '${HSTS_MAX_AGE}')."
  exit 1
fi

# The TLS profile `default` is built from (dynamic/tls-profiles.yml); the
# anchor selects the profile's content inside the template. An .env from before
# the model names tls-basic / tls-aplus / tls-modern — scripts/migrate-traefik-env.sh
# rewrites it.
case "${TLS_DEFAULT_OPTION:-}" in
  tls-compatible)  TLS_DEFAULT_ANCHOR=tls_compatible ;;
  tls-standard)    TLS_DEFAULT_ANCHOR=tls_standard ;;
  tls-strict)      TLS_DEFAULT_ANCHOR=tls_strict ;;
  tls-basic|tls-aplus|tls-modern)
    echo "ERROR: TLS_DEFAULT_OPTION=${TLS_DEFAULT_OPTION} is a name from before the middleware model —"
    echo "       scripts/migrate-traefik-env.sh core/traefik rewrites .env (tls-compatible / tls-standard / tls-strict)."
    exit 1
    ;;
  *)
    echo "ERROR: TLS_DEFAULT_OPTION must be tls-compatible, tls-standard or tls-strict (got '${TLS_DEFAULT_OPTION:-}')."
    exit 1
    ;;
esac
export TLS_DEFAULT_ANCHOR

# Entrypoint timeouts. The defaults are Traefik's own, so an .env written
# before the variables existed renders the behaviour it had.
export TRAEFIK_READ_TIMEOUT="${TRAEFIK_READ_TIMEOUT:-60s}"
export TRAEFIK_WRITE_TIMEOUT="${TRAEFIK_WRITE_TIMEOUT:-0s}"
export TRAEFIK_IDLE_TIMEOUT="${TRAEFIK_IDLE_TIMEOUT:-180s}"

# The senders whose forwarded headers the entrypoints trust: one range per line
# in ops/cloudflare-ips.txt, rendered into the YAML list under
# forwardedHeaders.trustedIPs. A list kept in a file can be compared with its
# source by a script; one kept inside the template could not.
CF_LIST="${ROOT_DIR}/ops/cloudflare-ips.txt"
if [ ! -f "${CF_LIST}" ]; then
  echo "ERROR: ${CF_LIST} not found — it carries the trusted proxy ranges."
  exit 1
fi
CLOUDFLARE_TRUSTED_IPS_YAML=""
while IFS= read -r range; do
  range="${range%%#*}"
  range="$(printf '%s' "${range}" | tr -d '[:space:]')"
  [ -n "${range}" ] || continue
  if ! printf '%s' "${range}" | grep -qE '^[0-9A-Fa-f:.]+/[0-9]{1,3}$'; then
    echo "ERROR: ${CF_LIST}: '${range}' is not an IPv4 or IPv6 range."
    exit 1
  fi
  CLOUDFLARE_TRUSTED_IPS_YAML="${CLOUDFLARE_TRUSTED_IPS_YAML}        - \"${range}\""$'\n'
done < "${CF_LIST}"
if [ -z "${CLOUDFLARE_TRUSTED_IPS_YAML}" ]; then
  echo "ERROR: ${CF_LIST} carries no range — the entrypoints would trust no forwarded header."
  exit 1
fi
CLOUDFLARE_TRUSTED_IPS_YAML="${CLOUDFLARE_TRUSTED_IPS_YAML%$'\n'}"

# Does a rendered traefik.yml trust any sender? The shape decides, not a value:
# the first entrypoint list under forwardedHeaders is `trustedIPs:` followed by
# `- "<range>"` lines (trusting) or by `[]` (trusting nobody). A value would go
# blind the day the ranges file changes its first entry. Comment lines are
# skipped: every release up to v0.9.4 rendered `# Cloudflare IPv4` right after
# the key, and a guard that read that line as "nobody" was blind to exactly
# the installations it exists for. Only the key directly under
# forwardedHeaders: counts (proxyProtocol has a trustedIPs of its own), and a
# flow list on the key line — `["…"]` trusts, `[]` nobody — is read too, so a
# hand-rewritten block cannot turn into a silent `none`.
rendered_trusts_ranges() {  # <traefik.yml>
  [ -f "$1" ] || return 1
  awk '/^[[:space:]]*(#|$)/ { next }
       /^[[:space:]]*trustedIPs:[^*]*$/ && prev ~ /^[[:space:]]*forwardedHeaders:[[:space:]]*$/ {
         rest = $0; sub(/^[[:space:]]*trustedIPs:[[:space:]]*/, "", rest); sub(/^&[^[:space:]]+[[:space:]]*/, "", rest)
         if (rest ~ /^\[/) { d = 1; exit (rest ~ /^\[[[:space:]]*\]/) ? 1 : 0 }
         t = 1; next
       }
       t { d = 1; exit ($0 ~ /^[[:space:]]*-[[:space:]]/) ? 0 : 1 }
       { prev = $0 }
       END { if (!d && !t) exit 1 }' "$1"
}

# ---------------------------------------------------------------------------
# Who may set the client address: TRAEFIK_FORWARDED_PROXY
#
#   none        the entrypoints trust no sender; every forwarded header is
#               deleted and the connecting address is the client
#   cloudflare  Cloudflare's published ranges are trusted at the entrypoints;
#               the CrowdSec bouncer gets the same ranges as
#               forwardedHeadersTrustedIPs and keeps its default header,
#               X-Forwarded-For. The entrypoint deletes that header from every
#               sender outside the ranges, so the bouncer compares a direct
#               client by its connection and, on a request from Cloudflare,
#               the last X-Forwarded-For entry outside the ranges — the client
#               Cloudflare appended. CF-Connecting-IP is never used here: the
#               plugin reads its header from any sender, and Traefik does not
#               delete that one. config/host/cloudflare-ranges.nft carries the
#               ranges for the host firewall.
#
# Absent or empty means none. Before this switch existed every rendered
# configuration trusted the Cloudflare ranges, so a config/ that still carries
# a list while .env says nothing is stopped: rendering `none` over it would make
# an installation behind Cloudflare see edge addresses — and ban them.
# ---------------------------------------------------------------------------
proxy_declared=""
[ -n "${TRAEFIK_FORWARDED_PROXY:-}" ] && proxy_declared=yes
TRAEFIK_FORWARDED_PROXY="$(printf '%s' "${TRAEFIK_FORWARDED_PROXY:-none}" | tr '[:upper:]' '[:lower:]')"
case "${TRAEFIK_FORWARDED_PROXY}" in
  none|cloudflare) ;;
  *)
    echo "ERROR: TRAEFIK_FORWARDED_PROXY must be none or cloudflare (got '${TRAEFIK_FORWARDED_PROXY}')."
    exit 1
    ;;
esac
if [ -z "${proxy_declared}" ] && rendered_trusts_ranges "${CFG_DIR}/traefik.yml"; then
  echo "ERROR: config/traefik.yml trusts Cloudflare's ranges, but TRAEFIK_FORWARDED_PROXY is not"
  echo "       set in .env. Rendering now would trust no sender — an installation behind"
  echo "       Cloudflare's proxy would then see edge addresses everywhere, and CrowdSec would"
  echo "       ban them."
  echo ""
  echo "       Records proxied by Cloudflare (orange cloud):  TRAEFIK_FORWARDED_PROXY=cloudflare"
  echo "       No Cloudflare proxy in front of this host:     TRAEFIK_FORWARDED_PROXY=none"
  echo "       Then run render.sh again. See core/traefik/README.md, 'Behind Cloudflare'."
  exit 1
fi
CROWDSEC_BOUNCER_FORWARDED_YAML=""
if [ "${TRAEFIK_FORWARDED_PROXY}" = cloudflare ]; then
  CROWDSEC_BOUNCER_FORWARDED_YAML="          forwardedHeadersTrustedIPs:"
  while IFS= read -r range; do
    range="${range%%#*}"; range="$(printf '%s' "${range}" | tr -d '[:space:]')"
    [ -n "${range}" ] || continue
    CROWDSEC_BOUNCER_FORWARDED_YAML="${CROWDSEC_BOUNCER_FORWARDED_YAML}"$'\n'"            - \"${range}\""
  done < "${CF_LIST}"
else
  CLOUDFLARE_TRUSTED_IPS_YAML="        []"
fi
export CLOUDFLARE_TRUSTED_IPS_YAML CROWDSEC_BOUNCER_FORWARDED_YAML

# ---------------------------------------------------------------------------
# Position 1's trusted class (DEC-076). TRUSTED_RANGES, quoted and
# space-separated, names the client networks access-trusted admits and
# access-trusted-vpn adds the VPN to; set and empty admits nobody. Unset stops
# the render: an .env from before the variable has to say what it trusts —
# scripts/migrate-traefik-env.sh adds the line and renames access-lan* in every
# stack. What a range may contain is validate.sh's check; the list is built
# here because envsubst renders a template once and knows no lists.
# ---------------------------------------------------------------------------
if [ -z "${TRUSTED_RANGES+set}" ]; then
  echo "ERROR: TRUSTED_RANGES is not set in .env. It names the client networks access-trusted"
  echo "       admits, quoted and space-separated; empty admits nobody:  TRUSTED_RANGES=\"\""
  echo "       access-lan and access-lan-vpn no longer exist: scripts/migrate-traefik-env.sh --all"
  echo "       adds the line and renames the policy in every stack's .env (CHANGELOG, Migration)."
  exit 1
fi
nl=$'\n'
ACCESS_TRUSTED_RANGES_YAML=""
for range in ${TRUSTED_RANGES}; do
  ACCESS_TRUSTED_RANGES_YAML="${ACCESS_TRUSTED_RANGES_YAML}${ACCESS_TRUSTED_RANGES_YAML:+${nl}}          - \"${range}\""
done
[ -n "${ACCESS_TRUSTED_RANGES_YAML}" ] || ACCESS_TRUSTED_RANGES_YAML="          - \"127.0.0.1/32\"  # TRUSTED_RANGES is empty: nobody"
n_ranges=$(printf '%s\n' ${TRUSTED_RANGES} | grep -c . || true)
export ACCESS_TRUSTED_RANGES_YAML

# ---------------------------------------------------------------------------
# Edge networks (DEC-075). EDGE_NETWORKS, quoted and space-separated, names the
# network of every installed stack — its TRAEFIK_NETWORK. They are rendered into
# config/edge-networks.yml, a Compose file COMPOSE_FILE applies: Traefik joins
# and creates each one, the stack declares it external. Unset stops the render
# (scripts/migrate-traefik-env.sh adds the line); empty means every stack is on
# the shared network. The list is checked here because a name Compose refuses
# would take Traefik down with it.
# ---------------------------------------------------------------------------
if [ -z "${EDGE_NETWORKS+set}" ]; then
  echo "ERROR: EDGE_NETWORKS is not set in .env. It names the edge network of every installed"
  echo "       stack (each stack's TRAEFIK_NETWORK), quoted and space-separated; empty means"
  echo "       every stack is on the shared network:  EDGE_NETWORKS=\"\""
  echo "       scripts/migrate-traefik-env.sh --all adds the line (docs/edge-networks.md)."
  exit 1
fi
seen_edges=" "
for edge in ${EDGE_NETWORKS}; do
  if ! printf '%s' "${edge}" | grep -qE '^[A-Za-z0-9][A-Za-z0-9_.-]*$'; then
    echo "ERROR: EDGE_NETWORKS: '${edge}' is not a Docker network name (letters, digits, _ . - ; starts with a letter or digit)."
    exit 1
  fi
  case "${edge}" in
    "${PUBLIC_NETWORK}"|"${SOCKET_PROXY_NETWORK}"|"${CROWDSEC_SECURITY_NETWORK}")
      echo "ERROR: EDGE_NETWORKS: '${edge}' is a network this stack already defines — the shared network"
      echo "       is not an edge network; a stack on it sets TRAEFIK_NETWORK=${PUBLIC_NETWORK} and is not listed."
      exit 1 ;;
  esac
  case "${seen_edges}" in *" ${edge} "*) echo "ERROR: EDGE_NETWORKS: '${edge}' is listed twice."; exit 1 ;; esac
  seen_edges="${seen_edges}${edge} "
done
n_edges=$(printf '%s\n' ${EDGE_NETWORKS} | grep -c . || true)

render_edge_networks() {
  printf '%s\n' \
    "# Rendered by ops/scripts/render.sh from EDGE_NETWORKS in .env — edit .env, never this file." \
    "# Traefik joins and creates each edge network; the stack whose TRAEFIK_NETWORK names it" \
    "# declares it external (DEC-075). COMPOSE_FILE in .env applies this file with docker-compose.yml." \
    "services:" \
    "  traefik:"
  if [ -z "${EDGE_NETWORKS}" ]; then
    printf '%s\n' "    networks: {}  # EDGE_NETWORKS is empty: every stack is on the shared network" "networks: {}"
    return
  fi
  printf '%s\n' "    networks:"
  for edge in ${EDGE_NETWORKS}; do printf '%s\n' "      ${edge}: {}"; done
  printf '%s\n' "networks:"
  for edge in ${EDGE_NETWORKS}; do
    # IPv4 only, like app-internal: Traefik dials a backend over IPv4 and no
    # client address is carried on this network.
    printf '%s\n' "  ${edge}:" "    name: ${edge}" "    driver: bridge"
  done
}

# The same ranges for the host firewall, as nftables defines, rendered only in
# cloudflare mode and installed by the operator (ops/host-files.manifest).
render_nft_ranges() {
  local v4="" v6="" range
  while IFS= read -r range; do
    range="${range%%#*}"; range="$(printf '%s' "${range}" | tr -d '[:space:]')"
    [ -n "${range}" ] || continue
    case "${range}" in *:*) v6="${v6:+${v6}, }${range}" ;; *) v4="${v4:+${v4}, }${range}" ;; esac
  done < "${CF_LIST}"
  printf '%s\n' \
    "# Rendered by core/traefik/ops/scripts/render.sh from ops/cloudflare-ips.txt — edit the" \
    "# file, never this one. Cloudflare's published ranges, for a chain on the forward hook" \
    "# (published container ports never traverse input) that admits 80 and 443 on the public" \
    "# interface from these sets and drops the rest: core/traefik/README.md, 'Behind Cloudflare'." \
    "define cloudflare_v4 = { ${v4} }" \
    "define cloudflare_v6 = { ${v6} }"
}

# ---------------------------------------------------------------------------
# The host firewall for the derived exposure profile (DEC-078.2): a recommended
# layer the operator installs (ops/host-files.manifest), never applied here.
# Input is closed except for what the host itself needs and the VPN brings;
# the forward path stays open — Docker's own traffic runs there — and carries
# only the two rules the profile needs: the VPN's IPv6 range is spoof-protected
# like Tailscale protects IPv4, and behind Cloudflare the published ports answer
# Cloudflare, the VPN and the trusted ranges alone.
# ---------------------------------------------------------------------------
nft_set_elements() {  # nft_set_elements <family 4|6> <ranges...>: "{ a, b }" or ""
  local fam="$1" out="" r; shift
  for r in "$@"; do
    case "${r}" in
      *:*) [ "${fam}" = 6 ] && out="${out:+${out}, }${r}" ;;
      *)   [ "${fam}" = 4 ] && out="${out:+${out}, }${r}" ;;
    esac
  done
  [ -n "${out}" ] && printf 'elements = { %s }' "${out}" || printf ''
}
render_ingress_nft() {  # render_ingress_nft <profile> <bind v4> <bind v6>
  local profile="$1" v4="$2" v6="$3" t4 t6 vpn_if="${VPN_INTERFACE:-tailscale0}"
  t4="$(nft_set_elements 4 ${TRUSTED_RANGES})"; t6="$(nft_set_elements 6 ${TRUSTED_RANGES})"
  printf '%s\n' \
    "#!/usr/sbin/nft -f" \
    "# Rendered by core/traefik/ops/scripts/render.sh for the exposure profile '${profile}'" \
    "# (TRAEFIK_BIND_V4=${v4:-none}, TRAEFIK_BIND_V6=${v6:-none}, TRAEFIK_FORWARDED_PROXY=${TRAEFIK_FORWARDED_PROXY})." \
    "# Edit .env and render again, never this file. How to load it with a way back, and" \
    "# what it closes: core/traefik/docs/host-firewall.md. It admits the management plane" \
    "# from the VPN ranges only — load it from a session that arrives over the VPN." \
    ""
  if [ "${profile}" = proxied ]; then
    printf '%s\n' '# Cloudflare'"'"'s ranges, rendered next to this file (defines cloudflare_v4, cloudflare_v6).' \
      'include "/etc/nftables.d/cloudflare-ranges.nft"' ""
  fi
  printf '%s\n' \
    "table inet blueprint_ingress {" \
    "  set vpn_v4 { type ipv4_addr; flags interval; elements = { ${TAILSCALE_CIDR_V4} } }" \
    "  set vpn_v6 { type ipv6_addr; flags interval; elements = { ${TAILSCALE_CIDR_V6} } }" \
    "  # TRUSTED_RANGES — the clients access-trusted admits; empty admits nobody" \
    "  set trusted_v4 { type ipv4_addr; flags interval; ${t4} }" \
    "  set trusted_v6 { type ipv6_addr; flags interval; ${t6} }"
  if [ "${profile}" = proxied ]; then
    printf '%s\n' \
      '  set cloudflare_v4 { type ipv4_addr; flags interval; elements = $cloudflare_v4 }' \
      '  set cloudflare_v6 { type ipv6_addr; flags interval; elements = $cloudflare_v6 }'
  fi
  printf '%s\n' \
    "" \
    "  # The host's own services: closed to the internet, open to the VPN. Published" \
    "  # container ports never traverse this hook — Docker translates and forwards them." \
    "  chain input {" \
    "    type filter hook input priority filter - 10; policy drop;" \
    "    iif lo accept" \
    "    ct state established,related accept" \
    "    ct state invalid drop" \
    "    # the VPN's IPv6 range arrives on the VPN interface only (Tailscale installs this for IPv4 alone)" \
    "    iifname != \"${vpn_if}\" ip6 saddr @vpn_v6 drop" \
    "    meta l4proto { icmp, ipv6-icmp } accept" \
    "    udp sport 67 udp dport 68 accept    # DHCPv4 client" \
    "    udp sport 547 udp dport 546 accept  # DHCPv6 client" \
    "    udp dport 41641 accept              # Tailscale: direct connections to this node" \
    "    # the management plane: what the VPN brings — SSH by key, and nothing the internet sees" \
    "    ip saddr @vpn_v4 accept" \
    "    ip6 saddr @vpn_v6 accept" \
    "  }" \
    "" \
    "  # The forward path carries Docker's traffic and stays open (docs/standards/networking.md)." \
    "  chain forward {" \
    "    type filter hook forward priority filter - 10; policy accept;" \
    "    iifname != \"${vpn_if}\" ip6 saddr @vpn_v6 drop"
  if [ "${profile}" = proxied ]; then
    printf '%s\n' \
      "    # the published ports (translated to Traefik's 80 and 443) answer Cloudflare, the VPN" \
      "    # and the trusted ranges; a direct client that knows the origin is refused here" \
      "    ct status dnat ct state new tcp dport { 80, 443 } ip saddr != @cloudflare_v4 ip saddr != @vpn_v4 ip saddr != @trusted_v4 drop" \
      "    ct status dnat ct state new udp dport 443 ip saddr != @cloudflare_v4 ip saddr != @vpn_v4 ip saddr != @trusted_v4 drop" \
      "    ct status dnat ct state new tcp dport { 80, 443 } ip6 saddr != @cloudflare_v6 ip6 saddr != @vpn_v6 ip6 saddr != @trusted_v6 drop" \
      "    ct status dnat ct state new udp dport 443 ip6 saddr != @cloudflare_v6 ip6 saddr != @vpn_v6 ip6 saddr != @trusted_v6 drop"
  fi
  printf '%s\n' "  }" "}"
}

rendered_has_bouncer() {
  grep -qsE '^experimental:' "${CFG_DIR}/traefik.yml" && return 0
  grep -qsE '^[[:space:]]*- threat-crowdsec(-appsec)?@file' "${CFG_DIR}/traefik.yml" && return 0
  # both name sets: a configuration rendered before the middleware model
  # carries crowdsec-basic / crowdsec-appsec
  grep -qsE '^[[:space:]]*(crowdsec-(basic|appsec)|threat-crowdsec(-appsec)?):' "${CFG_DIR}"/dynamic/*.yml 2>/dev/null
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
    echo "       Remove it: CROWDSEC_BOUNCER_ENABLED=false — then recreate the traefik container"
    echo "                  at once: the running entrypoint list names the threat middleware"
    echo "                  until the recreate, and every router on websecure is disabled in between."
    echo "       Then run render.sh again. See core/traefik/README.md, 'Migrating an installation"
    echo "       that enabled the integration before the switch'."
    exit 1
  fi
  if [ "${CROWDSEC_BOUNCER_ENABLED}" = false ]; then
    echo "NOTICE: CROWDSEC_BOUNCER_ENABLED=false — the CrowdSec plugin and the threat middleware are"
    echo "        removed from config/. Recreate the traefik container NOW: the running entrypoint"
    echo "        list (static configuration) still names threat-crowdsec@file, which the dynamic"
    echo "        configuration no longer defines — every router on websecure is disabled until then."
  fi
fi

rendered_has_forward_auth() {
  grep -qsE '^[[:space:]]*(auth-authentik|sec-authentik):' "${CFG_DIR}"/dynamic/*.yml 2>/dev/null
}

if rendered_has_forward_auth; then
  if [ -z "${auth_switch_declared}" ]; then
    echo "ERROR: config/dynamic carries the Authentik forward-auth middleware, but"
    echo "       AUTHENTIK_FORWARD_AUTH_ENABLED is not set in .env. Rendering now would remove"
    echo "       it while every router that names it goes dark."
    echo ""
    echo "       Keep it:   AUTHENTIK_FORWARD_AUTH_ENABLED=true"
    echo "                  AUTHENTIK_FORWARD_AUTH_ADDRESS=<the address config/dynamic names>"
    echo "       Remove it: AUTHENTIK_FORWARD_AUTH_ENABLED=false — after moving every router's"
    echo "                  APP_TRAEFIK_AUTH away from auth-authentik@file."
    echo "       Then run render.sh again. See core/traefik/README.md, 'Authentik forward-auth'."
    exit 1
  fi
  if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = false ]; then
    echo "NOTICE: AUTHENTIK_FORWARD_AUTH_ENABLED=false — the forward-auth middleware is removed"
    echo "        from config/. A router whose APP_TRAEFIK_AUTH still names auth-authentik@file"
    echo "        is disabled by Traefik until it is changed."
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
  echo " -> traefik.yml (CrowdSec bouncer plugin ${CROWDSEC_BOUNCER_PLUGIN_VERSION} declared; entrypoint: ${ENTRYPOINT_THREAT}@file, compress@file)"
else
  # Drop the marker-delimited plugin block; the markers are comments and go with it.
  envsubst < "${TPL_DIR}/traefik.yml.tmpl" \
    | sed '/^# >>> crowdsec-bouncer/,/^# <<< crowdsec-bouncer/d' | place "${CFG_DIR}/traefik.yml"
  echo " -> traefik.yml (no plugin — CROWDSEC_BOUNCER_ENABLED=false; entrypoint: compress@file)"
fi
envsubst < "${TPL_DIR}/haproxy.cfg.template.tmpl" | place "${CFG_DIR}/haproxy.cfg.template"
if [ "${TRAEFIK_FORWARDED_PROXY}" = cloudflare ]; then
  mkdir -p "${CFG_DIR}/host"
  render_nft_ranges | place "${CFG_DIR}/host/cloudflare-ranges.nft"
  echo " -> host/cloudflare-ranges.nft (TRAEFIK_FORWARDED_PROXY=cloudflare — the ranges for the host firewall)"
else
  rm -f "${CFG_DIR}/host/cloudflare-ranges.nft"
  echo " -> trusted proxy ranges: none (TRAEFIK_FORWARDED_PROXY=none)"
fi
# The exposure profile and the host firewall rendered for it (DEC-078). The
# IPv6 binding counts when COMPOSE_FILE applies the dual-stack overlay.
bind_v4_effective="${TRAEFIK_BIND_V4:-0.0.0.0}"
compose_file_named="${COMPOSE_FILE:-}"
bind_v6_effective="$(effective_bind_v6 ${compose_file_named//:/ })"
EXPOSURE_PROFILE="$(exposure_profile "${bind_v4_effective}" "${bind_v6_effective}" "${TRAEFIK_FORWARDED_PROXY}")"
mkdir -p "${CFG_DIR}/host"
render_ingress_nft "${EXPOSURE_PROFILE}" "${bind_v4_effective}" "${bind_v6_effective}" | place "${CFG_DIR}/host/ingress.nft"
echo " -> host/ingress.nft (exposure profile: ${EXPOSURE_PROFILE} — the host firewall for it, to install by hand)"

echo "Rendering dynamic configs..."
# The files of the templates the middleware model retired (acc-*, sec-*,
# hdr-*, rl-*). A render from before the model left them in config/dynamic;
# they would define names nothing references and, for compress, a second
# definition Traefik refuses.
for retired in access.yml security-blocks.yml security-chains.yml; do
  if [ -f "${CFG_DIR}/dynamic/${retired}" ]; then
    rm -f "${CFG_DIR}/dynamic/${retired}"
    echo " -> ${retired} (retired by the middleware model — removed)"
  fi
done
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
    authentik.yml)
      # Same rule as crowdsec.yml: rendered with the switch on, absent with it off.
      if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" != true ]; then
        rm -f "$out"
        echo " -> ${base} (skipped — AUTHENTIK_FORWARD_AUTH_ENABLED=false)"
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
  if [ "$base" = model.yml ]; then
    echo " -> ${base} (access-trusted: ${n_ranges} declared range(s))"
  else
    echo " -> ${base}"
  fi
done

render_edge_networks | place "${CFG_DIR}/edge-networks.yml"
echo " -> edge-networks.yml (${n_edges} edge network(s))"

echo "Done. Generated files are in: config/ and config/dynamic/"
