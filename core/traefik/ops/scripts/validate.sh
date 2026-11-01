#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# --strict: the final acceptance after `docker compose up -d` — anything the
# published-address checks could not confirm fails instead of being reported.
# -f FILE: the compose files exactly as passed to `docker compose -f`, so the
# checks evaluate the configuration that is deployed. Without -f, Compose's own
# resolution applies: COMPOSE_FILE from .env, else docker-compose.yml.
STRICT=0
COMPOSE_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --strict) STRICT=1 ;;
    -f|--file)
      [ $# -ge 2 ] || { echo "ERROR: $1 needs a compose file."; exit 1; }
      case "$2" in /*) f="$2" ;; *) f="${PWD}/$2" ;; esac
      [ -f "${f}" ] || { echo "ERROR: compose file not found: $2"; exit 1; }
      COMPOSE_ARGS+=(--compose-file "${f}")
      shift ;;
    *) echo "ERROR: unknown argument '$1'. Usage: validate.sh [--strict] [-f compose-file]..."; exit 1 ;;
  esac
  shift
done

if [ ! -f "${ROOT_DIR}/.env" ]; then
  echo "ERROR: .env not found. Copy .env.example -> .env"
  exit 1
fi

# Check the syntax before sourcing. `set -a; source .env` runs the file as bash,
# so an unquoted value containing a space is parsed as a command and the operator
# gets a bash error naming the second word, not the variable. Refuse the file
# first and say which line is wrong.
env_syntax_errors=0
while IFS= read -r line_no_and_text; do
  line_no="${line_no_and_text%%:*}"
  line="${line_no_and_text#*:}"
  case "${line}" in
    ''|'#'*) continue ;;
  esac
  # Must be NAME=... — anything else is not an assignment bash will accept here.
  if ! printf '%s' "${line}" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*='; then
    echo "ERROR: .env line ${line_no} is not a NAME=value assignment: ${line}"
    env_syntax_errors=$((env_syntax_errors + 1))
    continue
  fi
  value="${line#*=}"
  # A value wrapped in a matching pair of quotes is fine whatever is inside it.
  # Compare the first and last character rather than globbing for a quote, which
  # needs escaping that is easy to get wrong and silently matches nothing.
  first_char="${value%"${value#?}"}"
  last_char="${value#"${value%?}"}"
  if [ "${#value}" -ge 2 ] && [ "${first_char}" = "${last_char}" ] \
     && { [ "${first_char}" = '"' ] || [ "${first_char}" = "'" ]; }; then
    continue
  fi
  # An unquoted value with whitespace is parsed as a command by `source`.
  case "${value}" in
    *[[:space:]]*)
      echo "ERROR: .env line ${line_no} has an unquoted value containing a space — quote it: ${line}"
      env_syntax_errors=$((env_syntax_errors + 1))
      ;;
  esac
done < <(grep -n '' "${ROOT_DIR}/.env")

if [ "${env_syntax_errors}" -gt 0 ]; then
  echo ""
  echo "Refusing to continue: ${env_syntax_errors} syntax problem(s) in .env."
  echo "render.sh sources the same file, so it would fail the same way with a less useful message."
  exit 1
fi

set -a
source "${ROOT_DIR}/.env"
set +a
. "${ROOT_DIR}/ops/scripts/exposure-profile.sh"

REQUIRED=(
  TZ
  TRAEFIK_IMAGE
  SOCKET_PROXY_IMAGE
  TRAEFIK_CONTAINER_NAME
  SOCKET_PROXY_CONTAINER_NAME
  PUBLIC_NETWORK
  SOCKET_PROXY_NETWORK
  CROWDSEC_SECURITY_NETWORK
  TRAEFIK_HTTP_PORT
  TRAEFIK_HTTPS_PORT
  DOCKER_SOCKET_PROXY_ENDPOINT
  TAILSCALE_CIDR_V4
  TAILSCALE_CIDR_V6
  ACME_EMAIL
  ACME_STORAGE
  ACME_RESOLVER_DNS
  ACME_RESOLVER_HTTP
  ACME_DNS_RESOLVER_1
  ACME_DNS_RESOLVER_2
  TRAEFIK_DASHBOARD_HOST
  TLS_DEFAULT_OPTION
  TRAEFIK_DASHBOARD_TLS_OPTION
  TRAEFIK_LOG_LEVEL
  TRAEFIK_LOG_FORMAT
  TRAEFIK_LOG_FILE
  TRAEFIK_ACCESSLOG_FORMAT
  TRAEFIK_ACCESSLOG_FILE
  TRAEFIK_ACCESSLOG_BUFFER
  DSP_LOG_LEVEL
  DSP_SOCKET_PATH
  DSP_BIND_CONFIG
  DSP_POST
)

missing=0
for v in "${REQUIRED[@]}"; do
  if [ -z "${!v:-}" ]; then
    echo "MISSING: ${v}"
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo ""
  echo "An .env written before a variable existed lacks it; .env.example carries each"
  echo "one with its default. CROWDSEC_SECURITY_NETWORK has no Compose default — unset,"
  echo "docker-compose.yml would create a network with an empty name."
  exit 1
fi

# Same defaults render.sh applies, so an .env written before a resolver
# existed validates against what will actually be rendered.
ACME_RESOLVER_TLS="${ACME_RESOLVER_TLS:-tlsResolver}"

# Entrypoint timeouts: Go durations (60s, 2m, 1h30m) or a bare number of
# seconds; 0 means no timeout. render.sh defaults each to Traefik's own value.
for v in TRAEFIK_READ_TIMEOUT TRAEFIK_WRITE_TIMEOUT TRAEFIK_IDLE_TIMEOUT; do
  val="${!v:-}"
  [ -n "${val}" ] || continue
  if ! printf '%s' "${val}" | grep -qE '^([0-9]+(ns|us|ms|s|m|h))+$|^[0-9]+$'; then
    echo "ERROR: ${v} must be a duration such as 60s, 2m or 0 (got '${val}')."
    exit 1
  fi
done

# Memory ceiling, when set: Docker's byte value with an optional unit.
if [ -n "${TRAEFIK_MEMORY:-}" ] && ! printf '%s' "${TRAEFIK_MEMORY}" | grep -qE '^[0-9]+[bkmgBKMG]?$'; then
  echo "ERROR: TRAEFIK_MEMORY must be a size such as 256m or 1g (got '${TRAEFIK_MEMORY}')."
  exit 1
fi

# Published ports: the port variables hold a number, the host address is one
# variable per family — TRAEFIK_BIND_V4, TRAEFIK_BIND_V6 (with
# network-dual-stack.yml) — rendered into config/published-ports.yml. An .env
# from before the bind variables may carry
# address:port; the message names the lines that keep the same binding.
port_error=0
port_v4_addrs=""
for v in TRAEFIK_HTTP_PORT TRAEFIK_HTTPS_PORT; do
  val="${!v}"
  if printf '%s' "${val}" | grep -qE '^[0-9]{1,5}$' && [ "${val}" -ge 1 ] && [ "${val}" -le 65535 ]; then
    continue
  fi
  port_error=1
  if printf '%s' "${val}" | grep -qE '^\[[0-9A-Fa-f:.]+\]:[0-9]{1,5}$'; then
    echo "ERROR: ${v}=${val} — an IPv6 host address belongs to TRAEFIK_BIND_V6."
    echo "       Keep the binding with:  ${v}=${val##*:}  and  TRAEFIK_BIND_V6=${val%:*}"
    echo "       with network-dual-stack.yml and its prerequisites (docs/ipv6-dual-stack.md)."
  elif printf '%s' "${val}" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$'; then
    echo "ERROR: ${v}=${val} — the port variable holds the port number only."
    echo "       Keep the binding with:  ${v}=${val##*:}  and  TRAEFIK_BIND_V4=${val%:*}"
    case " ${port_v4_addrs} " in *" ${val%:*} "*) ;; *) port_v4_addrs="${port_v4_addrs} ${val%:*}" ;; esac
  else
    echo "ERROR: ${v} must be a port number from 1 to 65535 (got '${val}')."
  fi
done
if [ "$(printf '%s' "${port_v4_addrs}" | wc -w)" -gt 1 ]; then
  echo "       The two ports name different addresses; TRAEFIK_BIND_V4 holds one for both."
fi
[ "${port_error}" -eq 0 ] || exit 1

# The subnets of a dual-stack proxy-public. The IPv6 value in .env.example is
# a placeholder: a prefix every reader of the file knows is the IPv6 shape of
# everyone picking 192.168.1.0/24, so it is refused, and so is any prefix
# outside the private ranges — proxy-public is an internal network and never
# carries a global address. Only judged when set; an IPv4-only install sets
# neither.
if [ -n "${PUBLIC_NETWORK_SUBNET_V4:-}${PUBLIC_NETWORK_SUBNET_V6:-}" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is needed to check PUBLIC_NETWORK_SUBNET_V4/_V6."; exit 1; }
  python3 - "${PUBLIC_NETWORK_SUBNET_V4:-}" "${PUBLIC_NETWORK_SUBNET_V6:-}" <<'PYEOF' || exit 1
import ipaddress, sys
v4, v6 = sys.argv[1], sys.argv[2]
EXAMPLE_V6 = ipaddress.ip_network("fd00:dead:beef:30::/64")
RFC1918 = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
ok = True
if v4:
    try:
        n4 = ipaddress.ip_network(v4, strict=True)
        if n4.version != 4 or not any(n4.subnet_of(p) for p in RFC1918):
            raise ValueError
    except ValueError:
        print(f"ERROR: PUBLIC_NETWORK_SUBNET_V4 must be a private IPv4 network (RFC 1918), got '{v4}'.")
        ok = False
if v6:
    try:
        n6 = ipaddress.ip_network(v6, strict=True)
        if n6.version != 6 or not n6.subnet_of(ipaddress.ip_network("fc00::/7")):
            raise ValueError
    except ValueError:
        print(f"ERROR: PUBLIC_NETWORK_SUBNET_V6 must be a unique local IPv6 network (fc00::/7), got '{v6}'.")
        ok = False
    else:
        if n6 == EXAMPLE_V6:
            print("ERROR: PUBLIC_NETWORK_SUBNET_V6 is the example prefix from .env.example. Generate your own:")
            print("         h=$(openssl rand -hex 5); printf 'fd%s:%s:%s::/64\\n' \"${h:0:2}\" \"${h:2:4}\" \"${h:6:4}\"")
            ok = False
sys.exit(0 if ok else 1)
PYEOF
fi

# TRUSTED_RANGES (DEC-076): the client networks access-trusted admits — set and
# empty admits nobody, unset is an .env from before the variable and is refused
# (render.sh says the same). Each entry is a network; none may contain or lie
# inside the VPN range (that is access-trusted-vpn's job, and a LAN that
# contains the VPN would admit every tailnet node as a LAN client) or a Docker
# network of this daemon (every container on it would pass). The daemon's
# networks are read when Docker answers; otherwise that part is reported as not
# checked.
if [ -z "${TRUSTED_RANGES+set}" ]; then
  echo "ERROR: TRUSTED_RANGES is not set in .env — the client networks access-trusted admits, quoted"
  echo "       and space-separated; empty admits nobody. scripts/migrate-traefik-env.sh --all adds the"
  echo "       line and renames access-lan/access-lan-vpn in every stack (CHANGELOG, Migration)."
  exit 1
fi
{
  command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is needed to check TRUSTED_RANGES."; exit 1; }
  docker_nets="[]"
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker_nets="$(docker network ls -q | xargs -r docker network inspect -f '{{json .IPAM.Config}} {{.Name}}' 2>/dev/null \
      | python3 -c '
import json, sys
out = []
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    cfg, _, name = line.partition(" ")
    for c in (json.loads(cfg) or []):
        if c.get("Subnet"): out.append([c["Subnet"], name])
print(json.dumps(out))' 2>/dev/null || echo "[]")"
    docker_checked=yes
  else
    docker_checked=""
  fi
  python3 - "${TRUSTED_RANGES}" "${TAILSCALE_CIDR_V4:-}" "${TAILSCALE_CIDR_V6:-}" "${PUBLIC_NETWORK_SUBNET_V4:-}" "${PUBLIC_NETWORK_SUBNET_V6:-}" "${docker_nets}" <<'PYEOF2' || exit 1
import ipaddress, json, sys
ranges, ts4, ts6, pub4, pub6, docker_nets = sys.argv[1:7]
ok = True
def net(v):
    return ipaddress.ip_network(v, strict=True)
vpn = [net(x) for x in (ts4, ts6) if x]
public = [(net(x), "PUBLIC_NETWORK_SUBNET") for x in (pub4, pub6) if x]
docker = [(net(s), n) for s, n in json.loads(docker_nets)]
for token in ranges.split():
    try:
        r = net(token)
    except ValueError:
        print(f"ERROR: TRUSTED_RANGES: '{token}' is not a network in CIDR form (192.168.10.0/24, 2001:db8:10::/64).")
        ok = False; continue
    for v in vpn:
        if r.version == v.version and r.overlaps(v):
            print(f"ERROR: TRUSTED_RANGES: '{token}' overlaps the VPN range {v} — a LAN range never contains the VPN;")
            print("       the policy that admits both is access-trusted-vpn.")
            ok = False
    for d, name in public + docker:
        if r.version == d.version and r.overlaps(d):
            print(f"ERROR: TRUSTED_RANGES: '{token}' overlaps the Docker network {d} ({name}) — every container on it")
            print("       would pass access-trusted. A trusted range is a network of clients, never one of containers.")
            ok = False
sys.exit(0 if ok else 1)
PYEOF2
  [ -n "${docker_checked}" ] || echo "NOTICE: TRUSTED_RANGES was not compared with the Docker daemon's networks (Docker did not answer here)."
}

# The published ports (DEC-075.3, step 7): render.sh writes them into
# config/published-ports.yml, one block per family, from TRAEFIK_BIND_V4 and
# TRAEFIK_BIND_V6. The compose files have to apply that file — docker-compose.yml
# publishes nothing itself — and the rendered file has to name the bindings
# .env names. An IPv6 binding without network-dual-stack.yml is the published-
# family check's ERROR below.
published_bindings
if [ -z "${TRAEFIK_BIND_V4+set}" ]; then
  echo "ERROR: TRAEFIK_BIND_V4 is not set. It has no default any more: TRAEFIK_BIND_V4=0.0.0.0 keeps"
  echo "       IPv4 ingress on every address, an empty TRAEFIK_BIND_V4= publishes no IPv4."
  echo "       scripts/migrate-traefik-env.sh --all adds 0.0.0.0 (CHANGELOG, Migration)."
  exit 1
fi
compose_list=":${COMPOSE_FILE:-}:"
for f in ${COMPOSE_ARGS[@]+"${COMPOSE_ARGS[@]}"}; do [ "${f}" = "--compose-file" ] || compose_list="${compose_list}${f##*/}:"; done
if [ -n "${COMPOSE_FILE:-}" ] || [ "${#COMPOSE_ARGS[@]}" -gt 0 ]; then
  case "${compose_list}" in
    *published-ports.yml:*) ;;
    *)
      echo "ERROR: the compose files do not apply config/published-ports.yml — docker-compose.yml publishes"
      echo "       no port itself, so Traefik would answer nothing. Add it to COMPOSE_FILE (or -f);"
      echo "       scripts/migrate-traefik-env.sh --all does (CHANGELOG, Migration)."
      exit 1 ;;
  esac
fi
if [ -z "${BIND_V4_EFFECTIVE}" ] && [ -z "${BIND_V6_EFFECTIVE}" ]; then
  echo "NOTICE: TRAEFIK_BIND_V4 and TRAEFIK_BIND_V6 are both empty — Traefik publishes no port."
fi
if [ -f "${ROOT_DIR}/config/published-ports.yml" ]; then
  rendered_ports="$(grep -E '^      - "' "${ROOT_DIR}/config/published-ports.yml" | sed -E 's/^      - "(.*):[0-9]+:[0-9]+\/(tcp|udp)"$/\1/' | sort -u | tr '\n' ' ' || true)"
  wanted_ports="$(printf '%s\n' "${BIND_V4_EFFECTIVE}" "${BIND_V6_EFFECTIVE}" | grep . | sort -u | tr '\n' ' ' || true)"
  if [ "${rendered_ports}" != "${wanted_ports}" ]; then
    echo "ERROR: config/published-ports.yml binds [${rendered_ports}] but .env says [${wanted_ports}] — run render.sh."
    exit 1
  fi
fi

# Edge networks (DEC-075). EDGE_NETWORKS names the network of every installed
# stack; render.sh writes config/edge-networks.yml from it. The rendered file has
# to match the list, and — when Docker answers — every running container that
# Traefik routes (traefik.enable=true) has to label a network Traefik joined: a
# stack on a network Traefik is not on is unreachable, and the log says nothing.
# A listed network Traefik has not joined yet is PENDING until the next
# `docker compose up -d`; a labelled network that is not listed is an ERROR.
if [ -z "${EDGE_NETWORKS+set}" ]; then
  echo "ERROR: EDGE_NETWORKS is not set in .env — the edge network of every installed stack, quoted"
  echo "       and space-separated; empty means every stack is on the shared network."
  echo "       scripts/migrate-traefik-env.sh --all adds the line (docs/edge-networks.md)."
  exit 1
fi
edge_pending=0
{
  for edge in ${EDGE_NETWORKS}; do
    printf '%s' "${edge}" | grep -qE '^[A-Za-z0-9][A-Za-z0-9_.-]*$' \
      || { echo "ERROR: EDGE_NETWORKS: '${edge}' is not a Docker network name."; exit 1; }
    case "${edge}" in "${PUBLIC_NETWORK}"|"${SOCKET_PROXY_NETWORK}"|"${CROWDSEC_SECURITY_NETWORK}")
      echo "ERROR: EDGE_NETWORKS: '${edge}' is a network this stack already defines; the shared network is not listed."; exit 1 ;;
    esac
  done
  if [ -f "${ROOT_DIR}/config/edge-networks.yml" ]; then
    # an empty list renders no network line: grep then exits 1, which set -e must not see
    rendered_edges="$(grep -E '^  [A-Za-z0-9][A-Za-z0-9_.-]*:$' "${ROOT_DIR}/config/edge-networks.yml" | grep -v '^  traefik:$' | sed 's/^  //; s/:$//' | sort | tr '\n' ' ' || true)"
    wanted_edges="$(printf '%s\n' ${EDGE_NETWORKS} | grep . | sort | tr '\n' ' ' || true)"
    if [ "${rendered_edges}" != "${wanted_edges}" ]; then
      echo "ERROR: config/edge-networks.yml lists [${rendered_edges}] but EDGE_NETWORKS says [${wanted_edges}] — run render.sh."
      exit 1
    fi
  fi
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    traefik_nets=" $(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "${TRAEFIK_CONTAINER_NAME}" 2>/dev/null || true)"
    if [ "${traefik_nets}" != " " ]; then
      while IFS=' ' read -r cname labelled; do
        [ -n "${cname}" ] || continue
        [ "${cname}" = "${TRAEFIK_CONTAINER_NAME}" ] && continue
        case "${traefik_nets}" in *" ${labelled} "*) continue ;; esac
        case " ${PUBLIC_NETWORK} ${EDGE_NETWORKS} " in
          *" ${labelled} "*)
            echo "PENDING: ${cname} labels traefik.docker.network=${labelled}, which Traefik has not joined yet —"
            echo "         'docker compose up -d' here recreates Traefik with it."
            edge_pending=1 ;;
          *)
            echo "ERROR: ${cname} labels traefik.docker.network=${labelled}, a network Traefik does not join and"
            echo "       EDGE_NETWORKS does not list — the stack is unreachable and the log says nothing. Add it to"
            echo "       EDGE_NETWORKS, render.sh, 'docker compose up -d' here (docs/edge-networks.md)."
            exit 1 ;;
        esac
      done < <(docker ps -q --filter label=traefik.enable=true | xargs -r docker inspect -f '{{.Name}} {{index .Config.Labels "traefik.docker.network"}}' 2>/dev/null | sed 's|^/||')
    else
      echo "NOTICE: ${TRAEFIK_CONTAINER_NAME} is not running — the routed containers' networks were not compared with Traefik's."
    fi
  else
    echo "NOTICE: the routed containers' networks were not compared with Traefik's (Docker did not answer here)."
  fi
}
if [ "${edge_pending}" -eq 1 ] && [ "${STRICT}" -eq 1 ]; then
  echo "ERROR (--strict): a routed container labels an edge network Traefik has not joined — recreate Traefik first."
  exit 1
fi

if [ -n "${TRAEFIK_BIND_V4:-}" ] && ! printf '%s' "${TRAEFIK_BIND_V4}" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
  echo "ERROR: TRAEFIK_BIND_V4 must be an IPv4 address such as 0.0.0.0 (got '${TRAEFIK_BIND_V4}')."
  echo "       IPv6 is bound by network-dual-stack.yml on TRAEFIK_BIND_V6."
  exit 1
fi
if [ -n "${TRAEFIK_BIND_V6:-}" ] && ! printf '%s' "${TRAEFIK_BIND_V6}" | grep -qE '^\[[0-9A-Fa-f:.]+\]$'; then
  echo "ERROR: TRAEFIK_BIND_V6 must be a bracketed IPv6 address such as [::] (got '${TRAEFIK_BIND_V6}')."
  exit 1
fi

# The trusted proxy ranges render.sh reads: every line must be a range.
CF_LIST="${ROOT_DIR}/ops/cloudflare-ips.txt"
if [ ! -f "${CF_LIST}" ]; then
  echo "ERROR: ${CF_LIST} not found — render.sh needs it for forwardedHeaders.trustedIPs."
  exit 1
fi
cf_ranges=0
while IFS= read -r range; do
  range="${range%%#*}"
  range="$(printf '%s' "${range}" | tr -d '[:space:]')"
  [ -n "${range}" ] || continue
  if ! printf '%s' "${range}" | grep -qE '^[0-9A-Fa-f:.]+/[0-9]{1,3}$'; then
    echo "ERROR: ${CF_LIST}: '${range}' is not an IPv4 or IPv6 range."
    exit 1
  fi
  cf_ranges=$((cf_ranges + 1))
done < "${CF_LIST}"
if [ "${cf_ranges}" -eq 0 ]; then
  echo "ERROR: ${CF_LIST} carries no range."
  exit 1
fi

# Who may set the client address. render.sh applies it; this refuses a value
# it does not know and, after a render, a config/ that disagrees with .env or
# with the ranges file. The shape of the rendered list decides whether it
# trusts anyone (render.sh carries the same function); comment lines inside
# the list, as every release up to v0.9.4 rendered them, are skipped; only the
# key directly under forwardedHeaders: counts; a flow list on the key line is
# read too. rendered_ranges prints the entries by value — quotes, a trailing
# comment and a carriage return from a hand edit stripped — so the comparison
# with the ranges file speaks of the list, not of the editor.
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
rendered_ranges() {  # <traefik.yml>: the entries of that list, one per line
  awk -v q="'" '/^[[:space:]]*(#|$)/ { next }
       /^[[:space:]]*trustedIPs:[^*]*$/ && prev ~ /^[[:space:]]*forwardedHeaders:[[:space:]]*$/ {
         rest = $0; sub(/^[[:space:]]*trustedIPs:[[:space:]]*/, "", rest); sub(/^&[^[:space:]]+[[:space:]]*/, "", rest)
         if (rest ~ /^\[/) {
           sub(/[[:space:]]*#.*$/, "", rest); gsub(/[][" \t\r]/, "", rest); gsub(q, "", rest)
           n = split(rest, a, ","); for (i = 1; i <= n; i++) if (a[i] != "") print a[i]
           exit
         }
         t = 1; next
       }
       t { if ($0 !~ /^[[:space:]]*-[[:space:]]/) exit
           sub(/^[[:space:]]*-[[:space:]]*/, ""); sub(/[[:space:]]*#.*$/, ""); gsub(/["\r[:space:]]/, ""); gsub(q, "")
           if ($0 != "") print; next }
       { prev = $0 }' "$1"
}
proxy_declared=""
[ -n "${TRAEFIK_FORWARDED_PROXY:-}" ] && proxy_declared=yes

# HSTS_MAX_AGE is optional (render.sh defaults it to two years) but, when set,
# a number of seconds; TLS_DEFAULT_OPTION one of the three profiles, old or new name.
if [ -n "${HSTS_MAX_AGE:-}" ] && ! printf '%s' "${HSTS_MAX_AGE}" | grep -qE '^[0-9]+$'; then
  echo "ERROR: HSTS_MAX_AGE must be a number of seconds (got '${HSTS_MAX_AGE}')."
  exit 1
fi
case "${TLS_DEFAULT_OPTION:-}" in
  tls-compatible|tls-standard|tls-strict) ;;
  tls-basic|tls-aplus|tls-modern)
    echo "ERROR: TLS_DEFAULT_OPTION=${TLS_DEFAULT_OPTION} is a name from before the middleware model —"
    echo "       scripts/migrate-traefik-env.sh core/traefik rewrites .env (tls-compatible / tls-standard / tls-strict)."
    exit 1 ;;
  *) echo "ERROR: TLS_DEFAULT_OPTION must be tls-compatible, tls-standard or tls-strict (got '${TLS_DEFAULT_OPTION:-}')."; exit 1 ;;
esac
TRAEFIK_FORWARDED_PROXY="$(printf '%s' "${TRAEFIK_FORWARDED_PROXY:-none}" | tr '[:upper:]' '[:lower:]')"
case "${TRAEFIK_FORWARDED_PROXY}" in
  none|cloudflare) ;;
  *) echo "ERROR: TRAEFIK_FORWARDED_PROXY must be none or cloudflare (got '${TRAEFIK_FORWARDED_PROXY}')."; exit 1 ;;
esac

# CrowdSec reverse-proxy remediation switch. render.sh applies it; this checks
# that what .env says is complete and that config/ agrees with it.
switch_declared="${CROWDSEC_BOUNCER_ENABLED+yes}"
CROWDSEC_BOUNCER_ENABLED="$(printf '%s' "${CROWDSEC_BOUNCER_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${CROWDSEC_BOUNCER_ENABLED}" in
  true|false) ;;
  *) echo "ERROR: CROWDSEC_BOUNCER_ENABLED must be true or false (got '${CROWDSEC_BOUNCER_ENABLED}')."; exit 1 ;;
esac
CROWDSEC_APPSEC_ENABLED="$(printf '%s' "${CROWDSEC_APPSEC_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${CROWDSEC_APPSEC_ENABLED}" in
  true|false) ;;
  *) echo "ERROR: CROWDSEC_APPSEC_ENABLED must be true or false (got '${CROWDSEC_APPSEC_ENABLED}')."; exit 1 ;;
esac
if [ "${CROWDSEC_APPSEC_ENABLED}" = true ] && [ "${CROWDSEC_BOUNCER_ENABLED}" != true ]; then
  echo "ERROR: CROWDSEC_APPSEC_ENABLED=true needs CROWDSEC_BOUNCER_ENABLED=true — AppSec inspection runs inside the bouncer plugin."
  exit 1
fi
if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
  if [ -z "${CROWDSEC_BOUNCER_KEY:-}" ]; then
    echo "ERROR: CROWDSEC_BOUNCER_ENABLED=true but CROWDSEC_BOUNCER_KEY is empty."
    echo "       Generate one on the engine: docker exec crowdsec cscli bouncers add traefik-bouncer"
    exit 1
  fi
  version="${CROWDSEC_BOUNCER_PLUGIN_VERSION:-v1.7.1}"
  if ! printf '%s' "${version}" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: CROWDSEC_BOUNCER_PLUGIN_VERSION must be a release tag like v1.7.1 (got '${version}')."
    echo "       Releases: https://github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin/releases"
    exit 1
  fi
fi

# Authentik forward-auth switch: same checks as CrowdSec's — a value other than
# true/false is refused, and with the switch on the address has to be a URL.
auth_switch_declared="${AUTHENTIK_FORWARD_AUTH_ENABLED+yes}"
AUTHENTIK_FORWARD_AUTH_ENABLED="$(printf '%s' "${AUTHENTIK_FORWARD_AUTH_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
case "${AUTHENTIK_FORWARD_AUTH_ENABLED}" in
  true|false) ;;
  *) echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED must be true or false (got '${AUTHENTIK_FORWARD_AUTH_ENABLED}')."; exit 1 ;;
esac
if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = true ]; then
  auth_address="${AUTHENTIK_FORWARD_AUTH_ADDRESS:-http://authentik-server:9000/outpost.goauthentik.io/auth/traefik}"
  if ! printf '%s' "${auth_address}" | grep -qE '^https?://[^[:space:]]+$'; then
    echo "ERROR: AUTHENTIK_FORWARD_AUTH_ADDRESS must be an http:// or https:// URL (got '${auth_address}')."
    echo "       The default is the embedded outpost of core/authentik on this host:"
    echo "       http://authentik-server:9000/outpost.goauthentik.io/auth/traefik"
    exit 1
  fi
fi

# Warn about sentinel values (not a hard fail – HTTP-01 users don't need this)
if [ "${CF_DNS_API_TOKEN:-}" = "__REPLACE_ME__" ]; then
  echo "WARNING: CF_DNS_API_TOKEN is still set to __REPLACE_ME__. DNS-01 (wildcard certs) will fail."
fi

# Dashboard certificate strategy.
# The dashboard follows the same rule as application routers: a wildcard that
# covers its hostname makes a per-router resolver unnecessary. Coverage is a
# string relationship between two independent variables, not an assumption --
# *.example.com matches exactly one label, so traefik.admin.example.com and a
# dashboard on a different domain are NOT covered.
dashboard_covered_by_wildcard() {
  local host="$1" wild="${2:-}" label
  [ -n "$wild" ] || return 1
  [ "$host" = "$wild" ] && return 0          # apex, carried by the cert's main domain
  label="${host%".$wild"}"
  [ "$label" = "$host" ] && return 1         # different domain entirely
  [ -n "$label" ] || return 1
  [ "${label#*.}" = "$label" ]               # exactly one label below the wildcard
}

if dashboard_covered_by_wildcard "${TRAEFIK_DASHBOARD_HOST}" "${ACME_WILDCARD_DOMAIN:-}"; then
  if [ -n "${TRAEFIK_DASHBOARD_CERT_RESOLVER:-}" ]; then
    echo "WARNING: *.${ACME_WILDCARD_DOMAIN} already covers ${TRAEFIK_DASHBOARD_HOST}, and TRAEFIK_DASHBOARD_CERT_RESOLVER is set."
    echo "         Traefik will request a second certificate for that hostname, publishing it in Certificate Transparency logs."
    echo "         Leave the variable empty to serve the wildcard instead."
  fi
elif [ -z "${TRAEFIK_DASHBOARD_CERT_RESOLVER:-}" ]; then
  echo "SELECT A CERTIFICATE STRATEGY — neither is configured for ${TRAEFIK_DASHBOARD_HOST}."
  echo
  echo "  Wildcard    set ACME_WILDCARD_DOMAIN to the parent domain of that host,"
  echo "              and leave TRAEFIK_DASHBOARD_CERT_RESOLVER empty."
  echo "  Per-domain  set TRAEFIK_DASHBOARD_CERT_RESOLVER to a resolver name:"
  echo "              ${ACME_RESOLVER_DNS}  DNS-01, no public port needed"
  echo "              ${ACME_RESOLVER_HTTP}  HTTP-01, needs public TCP 80"
  echo "              ${ACME_RESOLVER_TLS}  TLS-ALPN-01, needs public TCP 443 and no TLS"
  echo "              terminator in front (a CDN proxy in front breaks it)."
  echo
  echo "  Both are supported. The shipped .env.example picks neither on purpose, so"
  echo "  the choice is made rather than inherited. Until one is set, Traefik would"
  echo "  answer HTTPS for that host with its self-signed default certificate."
  echo "  See core/traefik/README.md -> Certificate strategy."
  exit 1
fi

# Runtime files (after render)
if [ -f "${ROOT_DIR}/config/traefik.yml" ]; then
  # Ensure no unsubstituted variable remains — in the files render.sh writes,
  # and only those: config/traefik.yml, config/haproxy.cfg.template,
  # config/dynamic/*.yml and, in cloudflare mode, config/host/cloudflare-ranges.nft.
  # config/host/ also holds the copies scripts/host-files.sh renders — the
  # watchdog script and its env file carry shell variables on purpose — and
  # config/logrotate/ is tracked, not rendered; neither is envsubst output, so a
  # `${…}` there is not a render error (a whole-directory search failed on a
  # host with rendered host files, 2026-10-23).
  rendered_files() {
    printf '%s\n' "${ROOT_DIR}/config/traefik.yml" "${ROOT_DIR}/config/haproxy.cfg.template"
    if [ -f "${ROOT_DIR}/config/host/cloudflare-ranges.nft" ]; then
      printf '%s\n' "${ROOT_DIR}/config/host/cloudflare-ranges.nft"
    fi
    find "${ROOT_DIR}/config/dynamic" -maxdepth 1 -name '*.yml' 2>/dev/null | sort
  }
  unresolved="$(rendered_files | while IFS= read -r f; do
    [ -f "${f}" ] || continue
    grep -n '\${[A-Za-z_][A-Za-z0-9_]*}' "${f}" /dev/null || true
  done)"
  if [ -n "${unresolved}" ]; then
    echo "ERROR: Unresolved variables found in the files render.sh wrote:"
    echo "${unresolved}"
    exit 1
  fi

  # Before any file is named: a configuration that trusts a list while .env
  # does not say who may set the client address is the migration case, and
  # its message has to be the first thing the operator reads — not a missing
  # dynamic file from a later release (render.sh refuses for the same reason).
  if [ -z "${proxy_declared}" ] && rendered_trusts_ranges "${ROOT_DIR}/config/traefik.yml"; then
    echo "ERROR: config/traefik.yml trusts Cloudflare's ranges but TRAEFIK_FORWARDED_PROXY is not set in .env."
    echo "       Set it to cloudflare if Cloudflare proxies this host's records, to none if not, then run render.sh."
    exit 1
  fi

  # Every file render.sh writes unconditionally has to exist; the two
  # conditional ones have to exist exactly when their switch is set.
  test -f "${ROOT_DIR}/config/haproxy.cfg.template" \
    || { echo "Missing config/haproxy.cfg.template (run render.sh) — docker-compose.yml mounts it"; exit 1; }
  for f in integrations.yml tls-profiles.yml routers-system.yml redirects.yml servers-transports.yml model.yml; do
    test -f "${ROOT_DIR}/config/dynamic/${f}" || { echo "Missing config/dynamic/${f} (run render.sh)"; exit 1; }
  done
  # The names the middleware model retired must be gone from config/dynamic:
  # a file from a render before the model, or a hand-kept copy, defines
  # middlewares no router may name and, for compress, a second definition.
  for f in access.yml security-blocks.yml security-chains.yml; do
    if [ -f "${ROOT_DIR}/config/dynamic/${f}" ]; then
      echo "ERROR: config/dynamic/${f} is from before the middleware model — run render.sh, which removes it."
      exit 1
    fi
  done
  retired_names="$(grep -hoE '^    (acc-[a-z-]+|access-lan(-vpn)?|sec-[a-z0-9-]+|hdr-[a-z-]+|rl-[a-z-]+|permissions-policy|csp-enforce|crowdsec-(basic|appsec)|tls-(basic|aplus|modern)):' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null | sed 's/[[:space:]:]//g' | sort -u | tr '\n' ' ' || true)"
  if [ -n "${retired_names% }" ]; then
    echo "ERROR: config/dynamic defines names the middleware model retired: ${retired_names}"
    echo "       The templates no longer render them — bash ops/scripts/reset-templates.sh, then render.sh."
    exit 1
  fi

  # The model's header profiles each begin with the HSTS base — a router with
  # headers-none still commits its host name to HTTPS. Checked on the
  # rendered file: the line after `headers-<profile>:` + `chain:` +
  # `middlewares:` must be `- hsts-base`.
  for prof in headers-standard headers-application-owned headers-none; do
    first="$(awk -v p="    ${prof}:" '$0 == p { f = 1; next } f && /^[[:space:]]*- / { print; exit }' "${ROOT_DIR}/config/dynamic/model.yml" | tr -d ' ')"
    if [ "${first}" != "-hsts-base" ]; then
      echo "ERROR: config/dynamic/model.yml: ${prof} does not start with hsts-base (found '${first}') — run render.sh; a profile without the HSTS base is not a valid profile."
      exit 1
    fi
  done
  grep -qE '^[[:space:]]*default: \*tls_(compatible|standard|strict)$' "${ROOT_DIR}/config/dynamic/tls-profiles.yml" \
    || { echo "ERROR: config/dynamic/tls-profiles.yml carries no default TLS option built from TLS_DEFAULT_OPTION — run render.sh."; exit 1; }
  if [ -n "${ACME_WILDCARD_DOMAIN:-}" ]; then
    test -f "${ROOT_DIR}/config/dynamic/acme-wildcard.yml" \
      || { echo "Missing config/dynamic/acme-wildcard.yml although ACME_WILDCARD_DOMAIN is set (run render.sh)"; exit 1; }
  elif [ -f "${ROOT_DIR}/config/dynamic/acme-wildcard.yml" ]; then
    echo "WARNING: config/dynamic/acme-wildcard.yml exists but ACME_WILDCARD_DOMAIN is empty —"
    echo "         a wildcard router from an earlier render is still in place. Remove the file"
    echo "         (bash ops/scripts/reset-templates.sh, then render.sh) if the wildcard is no longer wanted."
  fi

  # The rendered state has to match the switch. Both directions are errors: the
  # integration present while the switch is off is the drift render.sh refuses
  # to paper over, and the switch on without the rendered halves means render.sh
  # has not run since the switch was set.
  rendered_plugin=false; grep -qsE '^experimental:' "${ROOT_DIR}/config/traefik.yml" && rendered_plugin=true
  rendered_mw=false; grep -qsE '^[[:space:]]*(crowdsec-(basic|appsec)|threat-crowdsec(-appsec)?):' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null && rendered_mw=true
  if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
    if [ "${rendered_plugin}" != true ] || [ ! -f "${ROOT_DIR}/config/dynamic/crowdsec.yml" ]; then
      echo "ERROR: CROWDSEC_BOUNCER_ENABLED=true but config/ does not carry the integration — run render.sh."
      exit 1
    fi
  else
    if [ "${rendered_plugin}" = true ] || [ "${rendered_mw}" = true ]; then
      if [ -z "${switch_declared}" ]; then
        echo "ERROR: config/ carries the CrowdSec integration but CROWDSEC_BOUNCER_ENABLED is not set in .env."
        echo "       Set it to true to keep the integration (plus CROWDSEC_BOUNCER_PLUGIN_VERSION and"
        echo "       CROWDSEC_BOUNCER_KEY), or to false to remove it, then run render.sh."
      else
        echo "ERROR: CROWDSEC_BOUNCER_ENABLED=false but config/ still carries the integration — run render.sh."
      fi
      exit 1
    fi
  fi

  # The entrypoint list has to match the switches as well: the threat
  # position exactly when the bouncer is on, its AppSec variant exactly when
  # that switch is on, compression always — in that order. A configuration
  # rendered before the middleware model carries no list and is refused the
  # same way: render.sh, then recreate the container.
  ep_list="$(sed -n '/^      middlewares:/,/^[^ ]/p' "${ROOT_DIR}/config/traefik.yml" | grep -E '^        - ' | sed 's/^        - //' || true)"
  expected_list="compress@file"
  if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
    expected_list="$(printf 'threat-crowdsec%s@file\ncompress@file' "$([ "${CROWDSEC_APPSEC_ENABLED}" = true ] && echo -appsec)")"
  fi
  if [ "${ep_list}" != "${expected_list}" ]; then
    echo "ERROR: the entrypoint middlewares in config/traefik.yml (websecure) are:"
    printf '%s\n' "${ep_list:-(none)}" | sed 's/^/         /'
    echo "       expected from CROWDSEC_BOUNCER_ENABLED=${CROWDSEC_BOUNCER_ENABLED}, CROWDSEC_APPSEC_ENABLED=${CROWDSEC_APPSEC_ENABLED}:"
    printf '%s\n' "${expected_list}" | sed 's/^/         /'
    echo "       Run render.sh, then recreate the traefik container — the list is static configuration."
    exit 1
  fi

  # One definition per name across config/dynamic: the file provider merges
  # every file into one namespace, and a second definition of a name — a file
  # rendered by an earlier template set and left behind, say — makes Traefik
  # refuse both and disable every router that names it.
  dupes="$(grep -hE '^    [A-Za-z0-9_-]+:[[:space:]]*$' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null | sed 's/[[:space:]]//g; s/:$//' | sort | uniq -d | tr '\n' ' ' || true)"
  if [ -n "${dupes% }" ]; then
    echo "ERROR: defined in more than one file under config/dynamic: ${dupes}"
    echo "       A file from an earlier render is still there — bash ops/scripts/reset-templates.sh, then render.sh."
    exit 1
  fi

  # The trusted senders, both directions: the rendered entrypoints carry a
  # list exactly when the switch says cloudflare, that list is the ranges file
  # as it is now, the CrowdSec middlewares carry the same list exactly then,
  # and no middleware names a header the bouncer would read from any sender.
  rendered_trusts_cf=false
  rendered_trusts_ranges "${ROOT_DIR}/config/traefik.yml" && rendered_trusts_cf=true
  if grep -qsE '^[[:space:]]*forwardedHeadersCustomName:' "${ROOT_DIR}/config/dynamic/crowdsec.yml" 2>/dev/null; then
    echo "ERROR: config/dynamic/crowdsec.yml sets forwardedHeadersCustomName — the bouncer would read that header"
    echo "       from any sender, Traefik deletes only X-Forwarded-*. The templates never set it; run render.sh."
    exit 1
  fi
  if [ "${TRAEFIK_FORWARDED_PROXY}" = cloudflare ]; then
    if [ "${rendered_trusts_cf}" != true ]; then
      echo "ERROR: TRAEFIK_FORWARDED_PROXY=cloudflare but config/traefik.yml trusts no Cloudflare range — run render.sh."
      exit 1
    fi
    if [ "$(rendered_ranges "${ROOT_DIR}/config/traefik.yml" | sort)" != "$(grep -vE '^[[:space:]]*(#|$)' "${CF_LIST}" | sed 's/#.*//; s/[[:space:]]//g' | sort)" ]; then
      echo "ERROR: the list in config/traefik.yml differs from ops/cloudflare-ips.txt — the ranges file changed"
      echo "       since the last render, or the block was edited by hand — run render.sh, then recreate the traefik container."
      exit 1
    fi
    if [ -f "${ROOT_DIR}/config/dynamic/crowdsec.yml" ] && ! grep -qsE '^[[:space:]]*forwardedHeadersTrustedIPs:' "${ROOT_DIR}/config/dynamic/crowdsec.yml"; then
      echo "ERROR: TRAEFIK_FORWARDED_PROXY=cloudflare but config/dynamic/crowdsec.yml carries no trusted-proxy list — run render.sh."
      exit 1
    fi
    test -f "${ROOT_DIR}/config/host/cloudflare-ranges.nft" || { echo "Missing config/host/cloudflare-ranges.nft (run render.sh)"; exit 1; }
  elif [ "${rendered_trusts_cf}" = true ]; then
    # the undeclared case was refused above, before the file checks
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/traefik.yml still trusts Cloudflare's ranges — run render.sh."
    exit 1
  elif grep -qsE '^[[:space:]]*forwardedHeadersTrustedIPs:' "${ROOT_DIR}/config/dynamic/crowdsec.yml" 2>/dev/null; then
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/dynamic/crowdsec.yml carries a trusted-proxy list — run render.sh."
    exit 1
  elif [ -f "${ROOT_DIR}/config/host/cloudflare-ranges.nft" ]; then
    echo "ERROR: TRAEFIK_FORWARDED_PROXY=none but config/host/cloudflare-ranges.nft exists — run render.sh, and remove the installed copy from the host firewall."
    exit 1
  fi

  # The Authentik middleware, both directions, like the CrowdSec integration.
  rendered_auth=false
  grep -qsE '^[[:space:]]*(auth-authentik|sec-authentik):' "${ROOT_DIR}"/config/dynamic/*.yml 2>/dev/null && rendered_auth=true
  if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = true ]; then
    if [ "${rendered_auth}" != true ] || [ ! -f "${ROOT_DIR}/config/dynamic/authentik.yml" ]; then
      echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED=true but config/dynamic carries no forward-auth middleware — run render.sh."
      exit 1
    fi
  elif [ "${rendered_auth}" = true ]; then
    if [ -z "${auth_switch_declared}" ]; then
      echo "ERROR: config/dynamic carries the Authentik forward-auth middleware but AUTHENTIK_FORWARD_AUTH_ENABLED is not set in .env."
      echo "       Set it to true to keep the middleware (plus AUTHENTIK_FORWARD_AUTH_ADDRESS), or to false to remove it, then run render.sh."
    else
      echo "ERROR: AUTHENTIK_FORWARD_AUTH_ENABLED=false but config/dynamic still carries the forward-auth middleware — run render.sh."
    fi
    exit 1
  fi

  # CrowdSec bouncer key. envsubst turns an unset CROWDSEC_BOUNCER_KEY into an
  # empty string, so a bouncer that cannot authenticate renders without a word of
  # complaint. The key is required only where a CrowdSec middleware was actually
  # rendered — the default-off blueprint must validate without one.
  #
  # The grep is a pre-filter, not the decision: it keeps a default-off install
  # free of any Python dependency. When it matches, the rendered YAML is parsed
  # and that parse decides.
  if grep -rqE '^[[:space:]]*(crowdsec-(basic|appsec)|threat-crowdsec(-appsec)?):' "${ROOT_DIR}/config/dynamic" 2>/dev/null; then
    CROWDSEC_CHECK="${ROOT_DIR}/../../scripts/ci/check-crowdsec-config.py"
    if [ -f "${CROWDSEC_CHECK}" ] && command -v python3 >/dev/null 2>&1; then
      python3 "${CROWDSEC_CHECK}" --rendered "${ROOT_DIR}/config" || exit 1
    else
      echo "ERROR: a CrowdSec middleware is enabled in the rendered config, but the"
      echo "       bouncer key check could not run. It needs python3 with PyYAML and"
      echo "       scripts/ci/check-crowdsec-config.py. Install them, or confirm by hand"
      echo "       that crowdsecLapiKey is not empty before starting Traefik."
      exit 1
    fi
  fi
fi

# ---------------------------------------------------------------------------
# The exposure profile and its layers (DEC-078). Derived from the bindings and
# the trusted proxy — what the configuration intends, never what the internet
# reaches; that is measured by scripts/exposure-test.sh from another machine
# and recorded in config/exposure-verified, which --strict requires for a
# public binding. The mandatory invariants are the checks above; every layer
# below is present or named with the risk its absence leaves. Nothing optional
# is an error by its absence.
# ---------------------------------------------------------------------------
published_bindings
bind_v4_effective="${BIND_V4_EFFECTIVE}"
bind_v6_effective="${BIND_V6_EFFECTIVE}"
EXPOSURE_PROFILE="$(exposure_profile "${bind_v4_effective}" "${bind_v6_effective}" "${TRAEFIK_FORWARDED_PROXY}")"
open_items=0
echo ""
echo "Exposure profile: ${EXPOSURE_PROFILE} — derived from TRAEFIK_BIND_V4=${bind_v4_effective}, TRAEFIK_BIND_V6=${bind_v6_effective:-not published}, TRAEFIK_FORWARDED_PROXY=${TRAEFIK_FORWARDED_PROXY}."
echo "  What the internet reaches is measured by scripts/exposure-test.sh from another machine, not here."
if [ "${EXPOSURE_PROFILE}" = proxied ] && [ "$(address_class "${bind_v4_effective}")" != public ] && [ "$(address_class "${bind_v6_effective}")" != public ]; then
  : # unreachable: proxied needs a public binding by construction
fi
echo "  Layers for this profile (mandatory invariants are the checks above):"
ingress_nft="${ROOT_DIR}/config/host/ingress.nft"
if [ -f "${ingress_nft}" ]; then
  if [ -r /etc/nftables.d/ingress.nft ]; then
    if cmp -s "${ingress_nft}" /etc/nftables.d/ingress.nft; then
      echo "    host firewall      installed — /etc/nftables.d/ingress.nft matches the rendered ruleset (loaded? nft list table inet blueprint_ingress)"
    else
      echo "    host firewall      differs — /etc/nftables.d/ingress.nft is not the rendered ruleset: scripts/host-files.sh (docs/host-firewall.md)"
    fi
  else
    case "${EXPOSURE_PROFILE}" in
      direct)  risk="every published port answers the internet unfiltered and the VPN's IPv6 range is not spoof-protected" ;;
      proxied) risk="a direct client that knows the origin bypasses Cloudflare, and the VPN's IPv6 range is not spoof-protected" ;;
      *)       risk="no host-level gate in front of the bindings — acceptable where an upstream firewall is the gate" ;;
    esac
    echo "    host firewall      not installed (recommended) — config/host/ingress.nft is rendered; residual risk: ${risk}"
  fi
else
  echo "    host firewall      not rendered — run render.sh"
fi
if [ "${CROWDSEC_BOUNCER_ENABLED}" = true ]; then
  echo "    crowdsec           present — the entrypoint bouncer (AppSec: ${CROWDSEC_APPSEC_ENABLED})"
else
  echo "    crowdsec           absent (recommended) — residual risk: no detection or remediation at the entrypoint; access policies and logins stand alone"
fi
if [ "${AUTHENTIK_FORWARD_AUTH_ENABLED}" = true ]; then
  echo "    forward-auth       present — auth-authentik@file is rendered; the stacks' posture lines say where it is used"
else
  echo "    forward-auth       absent (optional) — residual risk: an application with a weak login has no gate in front; the posture lines name each (auth posture)"
fi
if [ "${EXPOSURE_PROFILE}" = proxied ]; then
  echo "    cloudflare origin  not verifiable here — Authenticated Origin Pulls or a tunnel on Cloudflare's side; without one the host firewall above is what keeps a direct client out"
fi
echo "    management         the ruleset admits the host's services from the VPN ranges only, by key; the second, ingress-independent path (console, second interface) is yours to keep — not checkable here"
marker_file="${ROOT_DIR}/config/exposure-verified"
if [ "${EXPOSURE_PROFILE}" = private ]; then
  echo "    exposure test      not required — nothing is published to a public address"
elif [ -f "${marker_file}" ] && grep -q '^EXPOSURE_MARKER ' "${marker_file}"; then
  marker_line="$(grep '^EXPOSURE_MARKER ' "${marker_file}" | tail -1)"
  marker_profile="$(printf '%s' "${marker_line}" | sed -n 's/.* profile=\([a-z]*\).*/\1/p')"
  marker_date="$(printf '%s' "${marker_line}" | sed -n 's/.* date=\([^ ]*\).*/\1/p')"
  marker_target="$(printf '%s' "${marker_line}" | sed -n 's/.* target=\([^ ]*\).*/\1/p')"
  if [ "${marker_profile}" != "${EXPOSURE_PROFILE}" ]; then
    echo "ERROR: config/exposure-verified records profile '${marker_profile}', the configuration derives '${EXPOSURE_PROFILE}' —"
    echo "       run scripts/exposure-test.sh ${marker_target:-<host>} ${EXPOSURE_PROFILE} from another machine and store its marker."
    exit 1
  fi
  echo "    exposure test      recorded ${marker_date} against ${marker_target} (profile ${marker_profile}) — repeat it after a change of bindings or firewall"
else
  echo "PENDING: exposure test — a public binding needs the measurement from another machine:"
  echo "         bash scripts/exposure-test.sh <this host's address> ${EXPOSURE_PROFILE}   then store its marker line in config/exposure-verified"
  open_items=1
fi
echo ""

# Published address families: IPv6 only where the client address survives the
# way to the container — the effective Compose model, the Docker daemon's
# settings under dual-stack, and the running container. The checker explains
# each finding; see its header for the rules.
case "${DOCKER_DAEMON_CHECK:-}" in
  ''|manual) ;;
  *) echo "ERROR: DOCKER_DAEMON_CHECK must be empty or manual (got '${DOCKER_DAEMON_CHECK}')."; exit 1 ;;
esac
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is needed to check which addresses Traefik is published on."
  exit 1
fi
# docker-compose.yml pins the published ports to the public network with
# gw_priority, which Compose knows since 2.33.1 (docs.docker.com, Compose file
# reference) and the Engine since 28.0. An older Compose refuses the file with
# "additional properties not allowed"; say so before that happens.
if command -v docker >/dev/null 2>&1; then
  compose_version="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
  if [ -n "${compose_version}" ] && ! printf '%s\n%s\n' "2.33.1" "${compose_version}" | sort -t. -k1,1n -k2,2n -k3,3n -c 2>/dev/null; then
    echo "ERROR: Docker Compose ${compose_version} is older than 2.33.1, the first release that knows"
    echo "       gw_priority, which docker-compose.yml uses to pin the published ports to the public"
    echo "       network. Update Compose (docker-compose-plugin) before starting Traefik."
    exit 1
  fi
fi
# Before the first render, the files COMPOSE_FILE names under config/ do not
# exist yet, and the published-address checks have no model to read. They are
# reported as not run — never as passed — and run after render.sh. Only in that
# state: once config/traefik.yml exists, with -f, or when a file outside config/
# is missing, a missing compose file stays the checker's ERROR.
not_rendered=""
if [ "${#COMPOSE_ARGS[@]}" -eq 0 ] && [ ! -f "${ROOT_DIR}/config/traefik.yml" ]; then
  other_missing=""
  IFS="${COMPOSE_PATH_SEPARATOR:-:}" read -r -a listed_files <<< "${COMPOSE_FILE:-}"
  for f in ${listed_files[@]+"${listed_files[@]}"}; do
    [ -f "${ROOT_DIR}/${f}" ] && continue
    case "${f}" in
      config/*) not_rendered="${not_rendered} ${f}" ;;
      *) other_missing=1 ;;
    esac
  done
  [ -n "${other_missing}" ] && not_rendered=""
fi
family_rc=0
if [ -n "${not_rendered}" ]; then
  echo "NOT VERIFIED: not rendered yet (${not_rendered# }) — the published-address checks run after render.sh."
  family_rc=3
else
  python3 "${ROOT_DIR}/ops/scripts/check-published-family.py" \
    --project-dir "${ROOT_DIR}" \
    ${COMPOSE_ARGS[@]+"${COMPOSE_ARGS[@]}"} \
    --public-network "${PUBLIC_NETWORK}" \
    --container "${TRAEFIK_CONTAINER_NAME}" \
    --daemon-check "${DOCKER_DAEMON_CHECK:-}" || family_rc=$?
fi
case "${family_rc}" in
  0)
    if [ "${open_items}" -ne 0 ]; then
      echo ""
      echo "VALID, SECURITY NOT CONFIRMED: the exposure test above is open. Run it from another"
      echo "machine, store the marker, then run validate.sh --strict."
      [ "${STRICT}" -eq 1 ] && exit 1
      exit 0
    fi ;;
  3)
    # PENDING or NOT VERIFIED: the configuration is valid and the update that
    # resolves it must not be blocked — but this is not a security OK.
    echo ""
    echo "VALID, SECURITY NOT CONFIRMED: the items above are open. After"
    echo "'docker compose up -d', run validate.sh --strict, with the same -f files"
    echo "as the deployment, to confirm them."
    [ "${STRICT}" -eq 1 ] && exit 1
    exit 0 ;;
  *) exit 1 ;;
esac

echo "OK."
