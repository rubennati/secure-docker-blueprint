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

_Services and tools being evaluated for inclusion._

---

## Ideas

_Future possibilities — not yet evaluated._
