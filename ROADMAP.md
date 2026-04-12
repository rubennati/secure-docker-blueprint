# Roadmap

## Planned

### CrowdSec – Intrusion Detection & Prevention

Two-layer security setup for the entire stack:

**Layer 1: Traefik Plugin (required)**
- CrowdSec Security Engine as detection layer (analyzes Traefik logs, SSH logs, system logs)
- Traefik Bouncer Plugin as HTTP enforcement point (blocks malicious requests before they reach containers)
- Protects against: bot traffic, brute force, aggressive scans, CVE probes, suspicious HTTP patterns
- Optional AppSec / WAF rules

**Layer 2: Firewall Bouncer (strongly recommended)**
- Host-level IP blocking via nftables
- Protects: SSH, SMTP, database ports, direct host access, global IP blocking
- CrowdSec recommends combining WAF bouncer + firewall bouncer for web-facing hosts

**Architecture:**
```
Internet
   ↓
Traefik + CrowdSec Plugin    ← HTTP enforcement
   ↓
Docker Services
   ↓
Host nftables                 ← IP-level enforcement
   ↓
CrowdSec Engine               ← Detection (logs → decisions)
```

**Components:**
- Security Engine — collects logs, produces decisions (ban, captcha, challenge)
- Traefik Plugin — queries engine per request, blocks if denied
- Firewall Bouncer — syncs decisions to nftables/iptables rules

Target location: `core/crowdsec/`

---

## Evaluating

### Admin Path Protection via Traefik

Restrict admin/backend URLs to specific access policies while keeping the public frontend open. Uses Traefik's `PathPrefix` routing with separate middleware chains.

**Examples:**
- WordPress `/wp-admin` and `/wp-login.php` → `acc-tailscale` or Authentik Forward-Auth
- Paperless entire UI → `acc-tailscale` (already internal-only)
- Ghost `/ghost` admin panel → `acc-tailscale`

**Approach:** Two Traefik routers per app — one for public paths (`acc-public`, `sec-2`) and one for admin paths (`acc-tailscale`, `sec-4` or Authentik Forward-Auth). Configurable via `.env` variables.

### Mutual TLS (mTLS) – Certificate-Based Access

Client certificate authentication as an additional access layer. Only devices with a trusted client certificate can connect — stronger than IP allowlists or passwords.

**Use cases:**
- API endpoints that only specific servers should reach
- Admin panels with hardware-bound authentication
- Zero-trust access without VPN dependency

**Approach:** Traefik TLS option with `clientAuth` requiring certificates signed by a custom CA. The `core/acme-certs` tool could be extended to also generate client certificates.

---

## Ideas

_Future possibilities — not yet evaluated._
