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
#      that logs its queries records every destination. It sees names an
#      allowlist would never have guessed.
#   2. Dropped packets. A call to a literal address skips DNS entirely. An
#      nftables rule that logs and drops the subnet's egress catches those.
#
# The resolver forwards rather than blackholes. Answering 0.0.0.0 would also
# record the attempt, but it takes the stack's own outbound with it — Invoice
# Ninja would stop sending mail. Observing does not require blocking, and a
# stack that keeps working is one that keeps making the calls worth seeing.
#
# The packet rule does drop, so add it only where that is acceptable.
#
# Preconditions, both checked on a host where they were absent:
#   - nftables on the host, for the packet half. Without it, run the DNS half
#     alone; it is the more informative of the two anyway.
#   - the ability to restart the stack, because the resolver is reached through
#     a `dns:` entry and Docker resolves that at container start.
# Root is not needed. Reading /proc/net/nf_conntrack instead would need it, and
# it would not help: a snapshot of open connections misses a daily or 48-hourly
# call by construction. Only a recording over time answers this.
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
  # nftables is optional. Without it the DNS half still runs, and it is the
  # half that names destinations — the packet rule only adds calls made to a
  # literal address. Failing here would withhold the useful observation over
  # the absence of the lesser one.
  HAVE_NFT=1
  command -v nft >/dev/null || HAVE_NFT=0
  mkdir -p "$STATE_DIR"

  # A resolver that writes down every query and then answers it normally.
  docker rm -f "egress-probe-dns-$SAFE" >/dev/null 2>&1 || true
  # Attach it to the stack's own egress network, so the containers can reach it.
  NET=$(docker compose -f "$STACK/docker-compose.yml" ps -q 2>/dev/null | head -1 \
        | xargs -r docker inspect --format \
          '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' \
        | grep -m1 -v internal || true)
  [ -n "$NET" ] || die "no running container to read a network from — start the stack first"

  UPSTREAM=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)
  [ -n "$UPSTREAM" ] || die "no nameserver in /etc/resolv.conf to forward to"

  docker run -d --name "egress-probe-dns-$SAFE" \
    --restart unless-stopped \
    --network "$NET" \
    -v "$STATE_DIR:/log" \
    4km3/dnsmasq:2.90-r3 \
    --keep-in-foreground --log-facility=/log/"$SAFE".dns.log \
    --log-queries --no-resolv --server="$UPSTREAM" >/dev/null

  DNS_IP=$(docker inspect "egress-probe-dns-$SAFE" \
    --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
  [ -n "$DNS_IP" ] || die "could not read the resolver's address"

  cat <<EOF

  Resolver up at $DNS_IP, logging to $LOG

  Point the stack at it without touching the tracked compose file — write an
  overlay and bring the service back up with both:

      cat > $STATE_DIR/$SAFE.probe.yml <<YAML
      services:
        app:
          dns:
            - $DNS_IP
      YAML

      docker compose -f $STACK/docker-compose.yml \
                     -f $STATE_DIR/$SAFE.probe.yml up -d app

  Docker keeps its own resolver at 127.0.0.11 and forwards outward to this one,
  so container names still resolve and the stack keeps working. Every external
  name it asks for is written to the log.

  Read the log through the container — dnsmasq writes it as root:

      docker exec egress-probe-dns-$SAFE cat /log/$SAFE.dns.log

  Once the containers are up, run this script again with 'start' to add the
  packet rule — the subnet does not exist until they do.

EOF

  if [ "$HAVE_NFT" -eq 0 ]; then
    echo "  nftables is not installed — the DNS half above is armed and is the"
    echo "  half that names destinations. Calls made to a literal address will"
    echo "  not be recorded."
    exit 0
  fi

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
  if docker ps --format '{{.Names}}' | grep -qx "egress-probe-dns-$SAFE"; then
    docker exec "egress-probe-dns-$SAFE" \
      grep -oE 'query\[[A-Z]+\] [^ ]+' "/log/$SAFE.dns.log" 2>/dev/null \
      | awk '{print $2}' | sort | uniq -c | sort -rn | head -40 \
      || echo "  (none yet)"
  else
    echo "  resolver egress-probe-dns-$SAFE is not running — was 'start' run?"
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
