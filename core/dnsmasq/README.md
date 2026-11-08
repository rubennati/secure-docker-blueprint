# dnsmasq

Lightweight DNS forwarder and cache for internal and Tailscale-based environments.

Project, source, licence and origin: [`UPSTREAM.md`](UPSTREAM.md).

## What it does

- Resolves wildcard DNS zones (`*.test.lab.example.com` → `100.100.100.10`)
- Caches upstream DNS queries (Cloudflare, Quad9)
- Serves static host records
- Listens only on specified interfaces (localhost + Tailscale)

## How it works

1. Template in `ops/templates/dnsmasq.conf.tmpl` with `${VARIABLE}` placeholders
2. `ops/scripts/render.sh` reads `.env` and generates `config/dnsmasq.conf`
3. Container mounts the rendered config read-only

## Setup

```bash
# 1. Copy and configure
cp .env.example .env
nano .env  # Set interfaces, wildcard zones, upstream DNS

# 2. Add static records (optional)
nano config/records.hosts

# 3. Render config from template
./ops/scripts/render.sh

# 4. Start
docker compose up -d
docker compose logs -f
```

## Adding Wildcard Zones

In `.env`, one slot per zone (`_1` … `_9`), with an address per family:

```env
DNS_WILDCARD_1_DOMAIN=test.lab.example.com
DNS_WILDCARD_1_IP=100.100.100.10
DNS_WILDCARD_1_IP6=fd7a:115c:a1e0::10
```

**Split DNS for a VPN needs both `A` and `AAAA`.** With only the `A` answer, a client that
prefers IPv6 asks the upstream resolver for `AAAA`, receives the host's public address and
leaves the tunnel — the VPN-only router then refuses it with 403. Measured on the lab host; [`core/traefik/docs/host-firewall.md`](../traefik/docs/host-firewall.md)
describes the path. Set `_IP6` to the host's tailnet IPv6 address whenever the host has
one. An empty slot renders no line (`address=/zone/` without an address would answer
NXDOMAIN for the whole zone), and `render.sh` prints a note for a zone without IPv6.

Check both answers after a render:

```bash
dig +short A    anything.test.lab.example.com @127.0.0.1
dig +short AAAA anything.test.lab.example.com @127.0.0.1
```

After changing `.env`, re-render and restart:

```bash
./ops/scripts/render.sh
docker compose restart
```

## Adding Static Records

Edit `config/records.hosts`:

```text
100.100.100.10    mynas.lab.example.com
100.100.100.20    printer.lab.example.com
```

Reload without restart (SIGHUP):

```bash
docker exec dnsmasq kill -HUP 1
```

This re-reads `records.hosts` and clears the DNS cache. No downtime.

## Verify

```bash
# Query a wildcard domain
nslookup anything.test.lab.example.com 127.0.0.1

# Query a static record
nslookup mynas.lab.example.com 127.0.0.1

# Check upstream forwarding
nslookup google.com 127.0.0.1
```

## Reloading vs Restarting

| Change | How to apply |
|---|---|
| `config/records.hosts` | `docker exec dnsmasq kill -HUP 1` (no downtime) |
| DNS cache clear | `docker exec dnsmasq kill -HUP 1` |
| `.env` + wildcard zones | `./ops/scripts/render.sh` then `docker compose restart` |
| Upstream DNS, interfaces | `./ops/scripts/render.sh` then `docker compose restart` |

## Important Notes

- **`network_mode: host`** — dnsmasq binds directly to host interfaces, no Docker networking
- **No Traefik** — this IS the DNS layer, it doesn't go through a reverse proxy
- **Interfaces** — only listens on configured interfaces (`lo`, `tailscale0`), not all
- **Config is rendered** — don't edit `config/dnsmasq.conf` directly, edit the template

## IPv6

dnsmasq supports IPv6 natively. Upstream DNS works for both families; a wildcard zone
answers `AAAA` only when its `_IP6` slot is set (above).

In `config/records.hosts`:

```text
fd7a:115c:a1e0::10    mynas.lab.example.com
100.100.100.10         mynas.lab.example.com
```

Test:

```bash
nslookup -type=AAAA google.com 127.0.0.1
```

## Backup

| | |
|---|---|
| **Database** | None. |
| **State** | None on the host — `config/dnsmasq.conf` and `config/records.hosts` are mounted read-only and versioned in git |
| **Reproducible** | everything |
| **Quiescing** | Not applicable. |

Nothing to back up. This stack is configuration only, and that configuration is
in the repository. Restoring means checking out the repository and starting the
container.

Worth noting for the wider restore plan: while this container is down, name
resolution for the internal zones is down with it. Bring it up early rather than
last.

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upstream reference, upgrade checklist
