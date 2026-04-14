# dnsmasq

Lightweight DNS forwarder and cache for internal and Tailscale-based environments.

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

In `.env`:
```env
DNS_WILDCARD_1_DOMAIN=test.lab.example.com
DNS_WILDCARD_1_IP=100.100.100.10
```

After changing `.env`, re-render and restart:
```bash
./ops/scripts/render.sh
docker compose restart
```

## Adding Static Records

Edit `config/records.hosts`:
```
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

dnsmasq supports IPv6 natively. Upstream DNS and wildcard zones work for both A and AAAA records.

In `config/records.hosts`:
```
fd7a:115c:a1e0::10    mynas.lab.example.com
100.100.100.10         mynas.lab.example.com
```

Test:
```bash
nslookup -type=AAAA google.com 127.0.0.1
```

## Details

- [UPSTREAM.md](UPSTREAM.md) — Upstream reference, upgrade checklist
