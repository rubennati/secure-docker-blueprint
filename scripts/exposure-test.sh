#!/usr/bin/env bash
# ==========================================================
# Exposure test — run from OUTSIDE the host (DEC-078.3)
# ==========================================================
# validate.sh derives what the configuration intends to expose; only a request
# from another machine measures what the internet reaches. This script makes
# those requests and, when they match the profile, prints the marker line that
# core/traefik/ops/scripts/validate.sh --strict requires for a public binding.
#
# Usage:
#   bash scripts/exposure-test.sh <host> <direct|proxied|private>
#
#   <host>   the host's own address, or a name that resolves to it. Behind
#            Cloudflare give the origin address, never the proxied name — the
#            name resolves to Cloudflare's edge, which answers for everyone.
#   profile  what validate.sh printed on the host ("Exposure profile: …").
#
# What is expected of each profile, from a machine that is not on the VPN:
#   direct    80 and 443 answer on every address family the host has
#   proxied   80 and 443 do not answer — the host firewall admits Cloudflare,
#             the VPN and the trusted ranges alone
#   private   80 and 443 do not answer
#   every     the ports that must never answer the internet stay closed: Traefik's
#   profile   API (8080), the Docker API (2375, 2376), and a sample of backend
#             ports that are published nowhere (3306, 5432, 6379, 8025, 11434)
#
# SSH (22) is reported, never judged: the management plane is the VPN, and a
# port that answers the internet is a fact for the operator to weigh.
#
# On success the last line is the marker. Store it on the host:
#   printf '%s\n' '<the marker line>' > core/traefik/config/exposure-verified
#
# Needs curl. Exit 0 when the profile holds, 1 when a probe contradicts it,
# 2 on usage errors.
# ==========================================================
set -u

host="${1:-}"; profile="${2:-}"
case "${profile}" in direct|proxied|private) ;; *) echo "usage: $0 <host> <direct|proxied|private>"; exit 2 ;; esac
[ -n "${host}" ] || { echo "usage: $0 <host> <direct|proxied|private>"; exit 2; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is needed."; exit 2; }

TIMEOUT="${EXPOSURE_TIMEOUT:-5}"

# probe <family 4|6> <port>: answers | closed | no-address
probe() {
  local fam="$1" port="$2" rc
  curl -s -"${fam}" --connect-timeout "${TIMEOUT}" --max-time "${TIMEOUT}" -o /dev/null "telnet://${host}:${port}" </dev/null >/dev/null 2>&1
  rc=$?
  case "${rc}" in
    0|48|56) echo answers ;;       # connected (telnet: closed by peer, recv failure after connect)
    6) echo no-address ;;          # the name has no address of this family
    *) echo closed ;;              # refused or timed out
  esac
}

failed=0
say() { printf '  %-22s %-4s %s\n' "$1" "$2" "$3"; }
fail() { say "$1" "$2" "$3 — contradicts the profile"; failed=1; }

echo "Exposure test against ${host} for profile '${profile}' from $(hostname) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
for fam in 4 6; do
  for port in 80 443; do
    r="$(probe "${fam}" "${port}")"
    case "${profile}:${r}" in
      *:no-address) say "tcp/${port}" "v${fam}" "no address of this family" ;;
      direct:answers)  say "tcp/${port}" "v${fam}" "answers (expected: a direct profile is published)" ;;
      direct:closed)   fail "tcp/${port}" "v${fam}" "does not answer" ;;
      *:answers)       fail "tcp/${port}" "v${fam}" "answers the internet" ;;
      *:closed)        say "tcp/${port}" "v${fam}" "does not answer (expected)" ;;
    esac
  done
done
for port in 8080 2375 2376 3306 5432 6379 8025 11434; do
  for fam in 4 6; do
    r="$(probe "${fam}" "${port}")"
    case "${r}" in
      answers) fail "tcp/${port}" "v${fam}" "answers — a port that must never be published" ;;
      closed) say "tcp/${port}" "v${fam}" "closed" ;;
      *) ;;
    esac
  done
done
for fam in 4 6; do
  r="$(probe "${fam}" 22)"
  case "${r}" in
    answers) say "tcp/22" "v${fam}" "answers the internet — SSH is reachable outside the VPN (reported, not judged)" ;;
    closed) say "tcp/22" "v${fam}" "closed to the internet" ;;
    *) ;;
  esac
done
echo ""
if [ "${failed}" -ne 0 ]; then
  echo "FAILED: the host does not expose what the profile '${profile}' says. Fix the host firewall or the"
  echo "        bindings, then test again. No marker."
  exit 1
fi
marker="EXPOSURE_MARKER date=$(date -u +%Y-%m-%dT%H:%M:%SZ) target=${host} profile=${profile} result=ok"
echo "OK: the host exposes what the profile says. Store the marker on the host, in core/traefik:"
echo "    printf '%s\\n' '${marker}' > config/exposure-verified"
echo "${marker}"
