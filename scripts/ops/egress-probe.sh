#!/usr/bin/env bash
# Record every outbound destination a stack attempts.
#
# The telemetry findings in docs/sovereignty/data-egress.md were read from
# source. That establishes a call exists; it cannot establish that no other one
# does. This is what settles the second half.
#
# Method: two observations, because either alone has a blind spot.
#
#   1. DNS. Anything reaching a host by name resolves it first, so a resolver
#      that logs its queries records the intent even when the connection is
#      then refused. It sees names an allowlist would never have guessed.
#   2. Dropped packets. A call to a literal address skips DNS entirely. An
#      nftables rule that logs and drops the subnet's egress catches those.
#
# Neither is a firewall for production use — the point is to watch, not to
# protect. Run it against a stack you can break.
#
# Usage:
#   scripts/ops/egress-probe.sh start <stack-dir>   # arm the probe, start the stack
#   scripts/ops/egress-probe.sh read  <stack-dir>   # what has been attempted so far
#   scripts/ops/egress-probe.sh stop  <stack-dir>   # tear the probe down
#
# Run for at least 48 hours. Some checks are daily, and Uptime Kuma's is every
# 48 — a short observation reports a clean result that only means nobody looked
# long enough.

set -euo pipefail

STACK="${2:-}"
STATE_DIR="/var/tmp/egress-probe"
CHAIN="egress_probe"

die() { printf '  %s\n' "$*" >&2; exit 1; }

[ -n "$STACK" ] || die "usage: $0 {start|read|stop} <stack-dir>"
[ -d "$STACK" ] || die "no such directory: $STACK"

command -v docker >/dev/null || die "docker not found"
PROJECT=$(basename "$STACK")
SAFE=${PROJECT//[^a-zA-Z0-9_]/_}
LOG="$STATE_DIR/$SAFE.dns.log"

subnet_of() {
  # Every network the stack's containers are attached to, as CIDR.
  docker compose -f "$STACK/docker-compose.yml" ps -q 2>/dev/null \
    | while read -r c; do
        [ -n "$c" ] || continue
        docker inspect "$c" --format \
          '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{"\n"}}{{end}}'
      done | sort -u | while read -r n; do
        [ -n "$n" ] || continue
        docker network inspect "$n" --format \
          '{{range .IPAM.Config}}{{.Subnet}}{{"\n"}}{{end}}'
      done | sort -u
}

case "${1:-}" in

start)
  command -v nft >/dev/null || die "nftables not found — install nftables"
  mkdir -p "$STATE_DIR"

  # A resolver that writes every query it is asked, and answers nothing else.
  docker rm -f "egress-probe-dns-$SAFE" >/dev/null 2>&1 || true
  docker run -d --name "egress-probe-dns-$SAFE" \
    --restart unless-stopped \
    -v "$STATE_DIR:/log" \
    4km3/dnsmasq:2.90-r0 \
    --keep-in-foreground --log-facility=/log/"$SAFE".dns.log \
    --log-queries --no-resolv --address=/#/0.0.0.0 >/dev/null

  DNS_IP=$(docker inspect "egress-probe-dns-$SAFE" \
    --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
  [ -n "$DNS_IP" ] || die "could not read the resolver's address"

  cat <<EOF

  Resolver up at $DNS_IP, logging to $LOG

  Point the stack at it and start it — add to every service in
  $STACK/docker-compose.yml:

      dns:
        - $DNS_IP

  Then: docker compose -f $STACK/docker-compose.yml up -d

  Every name the stack tries to resolve is answered with 0.0.0.0 and written to
  the log. Nothing reaches the internet, and the attempt is recorded either way.

  Once the containers are up, run this script again with 'start' to add the
  packet rule — the subnet does not exist until they do.

EOF

  SUBNETS=$(subnet_of || true)
  if [ -z "$SUBNETS" ]; then
    echo "  (no running containers yet — rerun after 'up -d' to arm the packet rule)"
    exit 0
  fi

  nft list table inet "$CHAIN" >/dev/null 2>&1 || nft add table inet "$CHAIN"
  nft flush table inet "$CHAIN"
  nft add chain inet "$CHAIN" forward \
    '{ type filter hook forward priority -1 ; policy accept ; }'
  while read -r cidr; do
    [ -n "$cidr" ] || continue
    # Log and drop anything leaving the subnet for a non-private destination.
    nft add rule inet "$CHAIN" forward ip saddr "$cidr" \
      ip daddr != { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 } \
      log prefix '"egress-probe: "' drop
    echo "  packet rule armed for $cidr"
  done <<<"$SUBNETS"
  ;;

read)
  echo
  echo "  ── names the stack tried to resolve ──"
  if [ -f "$LOG" ]; then
    grep -oE 'query\[[A-Z]+\] [^ ]+' "$LOG" 2>/dev/null \
      | awk '{print $2}' | sort | uniq -c | sort -rn | head -40 \
      || echo "  (none yet)"
  else
    echo "  no log at $LOG — was 'start' run?"
  fi

  echo
  echo "  ── packets dropped on their way out (literal addresses) ──"
  journalctl -k --since "48 hours ago" 2>/dev/null \
    | grep -oE 'egress-probe: .*DST=[0-9.]+' \
    | grep -oE 'DST=[0-9.]+' | sort | uniq -c | sort -rn | head -20 \
    || echo "  (none, or journald is unavailable)"
  echo
  echo "  A name here is an attempt, not proof it would have succeeded."
  echo "  Absence after less than 48 h means nobody watched long enough."
  echo
  ;;

stop)
  docker rm -f "egress-probe-dns-$SAFE" >/dev/null 2>&1 || true
  nft delete table inet "$CHAIN" >/dev/null 2>&1 || true
  echo "  probe removed. The log stays at $LOG"
  echo "  Remember to take the dns: block back out of the compose file."
  ;;

*)
  die "usage: $0 {start|read|stop} <stack-dir>"
  ;;
esac
