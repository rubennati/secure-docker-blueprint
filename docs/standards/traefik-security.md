# Traefik Security Architecture

Defines the security middleware system: building blocks, policy chains, access control, TLS profiles, and integrations.

For Traefik label patterns, see [Traefik Labels](traefik-labels.md).
For general container security, see [Security Baseline](security-baseline.md).

---

## Overview

Security is split into four independent config files in `core/traefik/ops/templates/dynamic/`:

| File | What it contains |
|------|-----------------|
| `access.yml` | Access policies — who can reach a service |
| `security-blocks.yml` | Building blocks — headers, rate limits, compression, CSP |
| `security-chains.yml` | Policy presets — sec-0 to sec-5 + embed variants |
| `integrations.yml` | CrowdSec + Authentik — optional, external services |

All files are rendered from `.tmpl` templates via `render.sh`. Traefik watches the `config/dynamic/` directory and hot-reloads changes (no restart needed for dynamic config).

---

## Access Policies (`access.yml`)

Controls WHO can reach a service. Pick one per router.

| Policy | Who gets through |
|--------|-----------------|
| `acc-public` | Everyone (no restriction) |
| `acc-local` | LAN only (RFC1918 + IPv6 ULA) |
| `acc-tailscale` | Tailscale/VPN only (IPv4 + IPv6) |
| `acc-private` | LAN + Tailscale combined |
| `acc-deny` | Nobody (emergency kill switch) |

All policies support IPv4 + IPv6. Configured via `.env`:

```env
TAILSCALE_CIDR_V4=100.64.0.0/10
TAILSCALE_CIDR_V6=fd7a:115c:a1e0::/48
LOCAL_CIDR_V4=192.168.0.0/16,10.0.0.0/8,172.16.0.0/12
LOCAL_CIDR_V6=fc00::/7
```

---

## Security Building Blocks (`security-blocks.yml`)

Modular middleware components. Used by the sec-* chains, or individually for custom combinations.

### Headers

| Block | What it sets |
|-------|-------------|
| `hdr-basic` | HSTS (2 years), nosniff, frameDeny |
| `hdr-basic-embed` | Like hdr-basic, SAMEORIGIN instead of frameDeny |
| `hdr-strict` | + HSTS preload, subdomains, referrer-policy, CSP report-only, Vary |
| `hdr-strict-embed` | Like hdr-strict, SAMEORIGIN + same-origin referrer |

### Rate Limiting

| Block | Limits |
|-------|--------|
| `rl-soft` | 100 requests/s average, 50 burst |
| `rl-hard` | 20 requests/s average, 40 burst |

### Extras

| Block | What it does |
|-------|-------------|
| `compress` | gzip compression |
| `permissions-policy` | Blocks camera, mic, geolocation, payment, USB, gyroscope |
| `csp-enforce` | Enforcing Content Security Policy (may break apps with external scripts) |

### Design Decisions

**browserXssFilter removed from all blocks.** `X-XSS-Protection: 1; mode=block` is deprecated — Chrome removed the XSS Auditor in 2019, Firefox and Safari ignore it. OWASP recommends not setting it. Removing it also resolved the Vaultwarden conflict (needed `browserXssFilter: false`).

**Embed variants use SAMEORIGIN + same-origin referrer.** The `e` variants replace `frameDeny: true` (X-Frame-Options: DENY) with `customFrameOptionsValue: SAMEORIGIN`. Embed variants also use `referrerPolicy: same-origin` (stricter) — embedded apps should not leak referrer to the parent frame.

---

## Policy Chains (`security-chains.yml`)

Presets that combine building blocks. Each level builds on the previous — higher = stricter. `e` suffix = iframe-friendly.

| Level | Building Blocks | Recommended for |
|-------|----------------|-----------------|
| `sec-0` | — | Debug, naked proxy |
| `sec-1` | hdr-basic, compress | Internal tools, monitoring |
| `sec-1e` | hdr-basic-embed, compress | Internal tools embedded in other apps |
| **`sec-2`** | **hdr-basic, rl-soft, compress** | **Standard for most apps (recommended default)** |
| `sec-2e` | hdr-basic-embed, rl-soft, compress | Standard + iframe-friendly |
| `sec-3` | hdr-strict, rl-soft, compress, permissions-policy | Public-facing, hardened |
| `sec-3e` | hdr-strict-embed, rl-soft, compress, permissions-policy | Public-facing + iframe-friendly |
| `sec-4` | hdr-strict, rl-hard, compress, permissions-policy | Sensitive apps, login pages, admin panels |
| `sec-5` | hdr-strict, rl-hard, compress, permissions-policy, csp-enforce | Maximum — only for CSP-tested apps |

### Changes vs. Previous System

| What | Before | After |
|------|--------|-------|
| Compression | From sec-2 | From sec-1 (performance belongs everywhere) |
| Permissions-Policy | Separate opt-in | Included from sec-3 |
| CSP enforce | Separate opt-in | sec-5 |
| Embed variants | Not available | sec-1e through sec-3e |
| browserXssFilter | In all headers | Removed (deprecated) |
| File structure | Single security.yml | Split into blocks + chains + integrations |

### App Assignment

| App | Level | Why |
|-----|-------|-----|
| Whoami | `sec-5` | Static page, no external resources → perfect for CSP enforce |
| Traefik Dashboard | `sec-4` + `acc-tailscale` | Sensitive admin UI, VPN-only |
| Dockhand | `sec-4` + `acc-tailscale` | Admin tool, VPN-only |
| Portainer | `sec-4` + `acc-tailscale` | Admin tool, VPN-only |
| Vaultwarden | `sec-3e` + `acc-tailscale` | Password manager: strict + SAMEORIGIN (TODO: after live test) |
| OnlyOffice | `sec-2e` | Must be embeddable in iframes |
| Nextcloud | `sec-3` + `acc-public` | Public-facing, hardened |
| Paperless | `sec-3` + `acc-tailscale` | Hardened, VPN-only |
| Seafile Pro | `sec-3` | Public-facing |
| Authentik | `sec-3` | Auth provider, should be hardened |
| Invoice Ninja | `sec-2` | Standard web app |
| WordPress / Ghost | `sec-2` | CMS with inline scripts |
| CalCom | `sec-2` | Scheduling tool |

---

## Pro Mode: Custom Combinations

For apps that don't fit any preset, combine building blocks directly:

```yaml
# Example: strict headers with embed + hard rate limit + CrowdSec
middlewares:
  - acc-tailscale@file
  - hdr-strict-embed@file
  - rl-hard@file
  - compress@file
  - sec-crowdsec@file
```

All building blocks are standalone middlewares — use them individually or with sec-* chains.

---

## Integrations (`integrations.yml`)

External services that plug into Traefik as middleware. Each is independent and optional.

| Integration | Type | What it does |
|-------------|------|-------------|
| `sec-crowdsec` | Traefik plugin | Blocks IPs flagged by CrowdSec + WAF inspection |
| `sec-authentik` | Forward auth | SSO authentication via Authentik |

Both are commented out by default. See the [Traefik README](../../core/traefik/README.md) for step-by-step enable/disable instructions.

---

## TLS Profiles (`tls-profiles.yml`)

| Profile | Min TLS | Use case |
|---------|---------|----------|
| `tls-basic` | 1.2 | Maximum compatibility (older clients) |
| `tls-aplus` | 1.2 | SSL Labs A+ (strict ciphers, X25519 preferred) |
| `tls-modern` | 1.3 | Current browsers only (strictest) |

Recommendation: `tls-aplus` for most services. Use `tls-modern` for password managers and admin panels. Use `tls-basic` only when older clients must connect.

---

## Incident Response

| Action | How |
|--------|-----|
| Block a service immediately | Change `acc-*` to `acc-deny@file` in the router |
| Lock to VPN only | Change `acc-public` to `acc-tailscale@file` |
| Escalate rate limiting | Change `sec-2@file` to `sec-4@file` |
| Block an IP via CrowdSec | `docker exec crowdsec cscli decisions add --ip X.X.X.X --duration 24h --reason "incident"` |
| Switch certificate resolver | Change `certResolver` between `cloudflare-dns` and `httpResolver` |

All changes in `config/dynamic/*.yml` are hot-reloaded by Traefik — no restart needed.
