# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/dockurr/dnsmasq — built from https://github.com/dockur/dnsmasq
- **Previous image:** https://hub.docker.com/r/4km3/dnsmasq — retired 2026-09-13, see Version / tag notes
- **dnsmasq docs:** https://thekelleys.org.uk/dnsmasq/doc.html
- **License:** GPL-2.0 or GPL-3.0, at your discretion
- **Decision facts checked:** 2026-09-21
- **Origin:** UK · Simon Kelley · non-EU
- **Domain:** Infrastructure
- **Role:** DNS forwarder with wildcard zones for split-DNS setups
- **Based on version:** `2.93` (image changed — see Version / tag notes)
- **Last checked:** 2026-04-14

## What we changed and why

| Change | Reason |
|--------|--------|
| Template-based config | Reproducible, env-driven, no manual editing |
| `cap_drop: ALL` + `cap_add: NET_BIND_SERVICE` | Minimal privileges for port 53 |
| `no-new-privileges` | Security hardening |
| `network_mode: host` | DNS needs direct interface binding |
| Wildcard zones via .env | Easy per-environment configuration |

## Version / tag notes

- **The image changed on 2026-09-13, from `4km3/dnsmasq` to `dockurr/dnsmasq`.** `4km3/dnsmasq`
  last published on 2025-11-18 and its repository's last commit is from the same day, so
  it still ships dnsmasq 2.90-r3. Six dnsmasq CVEs were published in 2026 —
  CVE-2026-2291 (heap overflow in `extract_name()`, DNS cache poisoning), CVE-2026-4890
  (infinite loop in DNSSEC validation, DoS), CVE-2026-4892 (heap out-of-bounds write in
  the DHCPv6 implementation, local code execution as root), CVE-2026-4893 (source-check
  bypass via RFC 7871 client-subnet), CVE-2026-5172 (out-of-bounds read in
  `extract_addresses()`) — and Alpine shipped the fixes in dnsmasq 2.91-r1 on 2026-05-14.
  An image that stopped building does not receive them.
- `dockurr/dnsmasq:2.93` builds on current Alpine and reads the same two paths this stack
  already mounts: `/etc/dnsmasq.conf` and `/etc/dnsmasq.d/`. The bind mount replaces the
  image's own template, so its `DNS1` / `DNS2` environment defaults do not apply —
  upstream servers come from the rendered `dnsmasq.conf`.
- **Not exercised on a host.** The image swap is a desk change. Before relying on it,
  confirm the container starts, answers a wildcard lookup and caches:
  `dig @<host> test.<your wildcard zone>`. Rolling back means setting the image back to
  `4km3/dnsmasq:2.90-r3`, which reinstates the unpatched version.

## Upgrade checklist

1. Check [dockurr/dnsmasq tags](https://hub.docker.com/r/dockurr/dnsmasq/tags)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Verify: `nslookup example.com 127.0.0.1`
