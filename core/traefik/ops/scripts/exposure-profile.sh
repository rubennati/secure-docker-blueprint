# Sourced by render.sh and validate.sh — the exposure profile DEC-078 derives.
#
# The profile says what the configuration intends to expose; it is never a
# measurement. What is reachable is measured from outside the host by
# scripts/exposure-test.sh and recorded in config/exposure-verified.
#
#   direct    a public binding, no trusted proxy: the internet reaches Traefik
#   proxied   a public binding behind Cloudflare (TRAEFIK_FORWARDED_PROXY=cloudflare)
#   private   every binding is a loopback, LAN, VPN or link-local address — or
#             nothing is published
#
# address_class <address>: public | private | none. The address is an IPv4
# literal or a bracketed IPv6 literal, as the bind variables hold them.
address_class() {
  local a="$1"
  [ -n "${a}" ] || { echo none; return; }
  case "${a}" in
    0.0.0.0|'[::]') echo public ;;
    127.*|10.*|192.168.*|169.254.*) echo private ;;
    172.1[6-9].*|172.2[0-9].*|172.3[01].*) echo private ;;
    100.6[4-9].*|100.[7-9][0-9].*|100.1[01][0-9].*|100.12[0-7].*) echo private ;;
    '[::1]'|'['[fF][cdCD]*|'['[fF][eE][89abAB]*) echo private ;;
    *) echo public ;;
  esac
}

# exposure_profile <bind v4> <bind v6> <forwarded proxy>
exposure_profile() {
  local v4 v6
  v4="$(address_class "$1")"; v6="$(address_class "$2")"
  if [ "${v4}" = public ] || [ "${v6}" = public ]; then
    [ "$3" = cloudflare ] && echo proxied || echo direct
  else
    echo private
  fi
}

# effective_bind_v6 <compose files...>: the IPv6 binding Compose would publish —
# TRAEFIK_BIND_V6 or its default when network-dual-stack.yml is applied, empty
# otherwise (docker-compose.yml alone publishes IPv4 only).
effective_bind_v6() {
  local f
  for f in "$@"; do
    case "${f}" in *network-dual-stack.yml*) printf '%s' "${TRAEFIK_BIND_V6:-[::]}"; return ;; esac
  done
  printf ''
}
