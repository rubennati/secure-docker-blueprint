# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/4km3/dnsmasq
- **dnsmasq docs:** https://thekelleys.org.uk/dnsmasq/doc.html
- **Based on version:** 2.90
- **Last checked:** 2026-04-14

## What we changed and why

| Change | Reason |
|--------|--------|
| Template-based config | Reproducible, env-driven, no manual editing |
| `cap_drop: ALL` + `cap_add: NET_BIND_SERVICE` | Minimal privileges for port 53 |
| `no-new-privileges` | Security hardening |
| `network_mode: host` | DNS needs direct interface binding |
| Wildcard zones via .env | Easy per-environment configuration |

## Upgrade checklist

1. Check [4km3/dnsmasq tags](https://hub.docker.com/r/4km3/dnsmasq/tags)
2. Bump `APP_TAG` in `.env`
3. `docker compose pull` → `docker compose up -d`
4. Verify: `nslookup example.com 127.0.0.1`
