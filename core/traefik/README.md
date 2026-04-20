# Traefik Reverse Proxy

Security-focused edge gateway for Docker-first servers.
Secure defaults, composable policies, fast incident response.

## Prerequisites

- `docker` + `docker compose`
- `envsubst` (package: `gettext-base` on Debian/Ubuntu)

## Setup

```bash
# 1. Create and edit your environment file
cp .env.example .env
```

Edit `.env` — at minimum change these:

| Variable | What to set |
|----------|-------------|
| `ACME_EMAIL` | Your real email for Let's Encrypt |
| `TRAEFIK_DASHBOARD_HOST` | FQDN for the Traefik dashboard (e.g. `traefik.yourdomain.com`) |
| `CF_DNS_API_TOKEN` | Cloudflare API token (Zone:Read + DNS:Edit) — only needed for DNS-01 |
| `ACME_WILDCARD_DOMAIN` | Uncomment and set if you want a wildcard certificate (optional) |
| `TAILSCALE_CIDR` | Your Tailscale/VPN CIDR (default: `100.64.0.0/10`) |

```bash
# 2. Validate environment variables
bash ops/scripts/validate.sh

# 3. Render templates (.tmpl -> config files)
bash ops/scripts/render.sh

# 4. Validate rendered output (checks for unresolved variables)
bash ops/scripts/validate.sh

# 5. Start
docker compose up -d

# 6. Verify
docker compose ps
# Dashboard should be reachable at https://<TRAEFIK_DASHBOARD_HOST>
# (only from Tailscale/VPN by default)
```

## Structure

```
.env.example                          # All configurable variables
docker-compose.yml                    # Docker Socket Proxy + Traefik
ops/
  templates/
    traefik.yml.tmpl                  # Static Traefik config
    haproxy.cfg.template.tmpl         # Socket proxy ACL config
    dynamic/
      access.yml.tmpl                 # Access policies (public / tailscale)
      security-blocks.yml.tmpl        # Security building blocks (headers, ratelimits, etc.)
      security-chains.yml.tmpl        # Policy presets (sec-0 to sec-5 + embed variants)
      integrations.yml.tmpl           # CrowdSec + Authentik (optional)
      tls-profiles.yml.tmpl           # TLS option profiles
      routers-system.yml.tmpl         # Dashboard router
      redirects.yml.tmpl              # Redirects (empty by default)
      acme-wildcard.yml.tmpl          # Wildcard cert router (optional)
  scripts/
    validate.sh                       # Check .env + rendered config
    render.sh                         # envsubst all .tmpl files -> config/
    reset-templates.sh                # Delete rendered files
config/                               # Generated output (gitignored)
```

Traefik does not substitute `${VARS}` in YAML. All `.tmpl` files are rendered via `envsubst` into `config/`.

## Security System

Three files, three layers — from quick presets to full customization:

| File | What it contains |
|------|-----------------|
| `security-blocks.yml` | Building blocks (headers, rate limits, compression, CSP) |
| `security-chains.yml` | Presets: sec-0 to sec-5 + embed variants |
| `integrations.yml` | CrowdSec + Authentik (optional, separate) |

### Quick Start: Policy Presets

Every router gets **two** middlewares — one for access, one for security:

```yaml
middlewares:
  - acc-public@file, sec-2@file       # Public site, standard hardening
  - acc-tailscale@file, sec-4@file    # Admin tool, VPN + strict
  - acc-public@file, sec-2e@file      # Public site, iframe-friendly
```

### Access

| Middleware | Who gets through |
|-----------|-----------------|
| `acc-public` | Everyone (no restriction) |
| `acc-local` | LAN only (RFC1918 + IPv6 ULA) |
| `acc-tailscale` | Tailscale/VPN only (IPv4 + IPv6) |
| `acc-private` | LAN + Tailscale combined |
| `acc-deny` | Nobody (emergency kill switch) |

### Security Levels

Each level builds on the previous one. `e` = embed/iframe-friendly (SAMEORIGIN instead of DENY).

| Level | What it includes | Recommended for |
|-------|-----------------|-----------------|
| `sec-0` | Nothing | Debug, naked proxy |
| `sec-1` | Basic headers + compress | Internal tools, monitoring |
| `sec-1e` | Like sec-1, iframe-friendly | Internal tools embedded in other apps |
| **`sec-2`** | **+ soft rate limit** | **Standard for most apps** (recommended default) |
| `sec-2e` | Like sec-2, iframe-friendly | OnlyOffice, editors embedded in other apps |
| `sec-3` | + strict headers + permissions-policy | Public-facing apps, hardened |
| `sec-3e` | Like sec-3, iframe-friendly | Vaultwarden, apps needing SAMEORIGIN |
| `sec-4` | + hard rate limit | Sensitive apps, login pages, admin panels |
| `sec-5` | + CSP enforce | Maximum — only for CSP-tested apps (e.g. Whoami) |

### Examples: Which level for which app?

| App | Level | Why |
|-----|-------|-----|
| Whoami | `sec-5` | Static page, no external resources → perfect for CSP enforce |
| Traefik Dashboard | `sec-4` + `acc-tailscale` | Sensitive admin UI, VPN-only, hard rate limit |
| Vaultwarden | `sec-3e` + `acc-tailscale` | Password manager: strict but needs SAMEORIGIN for browser extension |
| Nextcloud | `sec-3` + `acc-public` | Public-facing, hardened headers |
| WordPress / Ghost | `sec-2` + `acc-public` | CMS with inline scripts, standard protection |
| OnlyOffice | `sec-2e` | Must be embeddable in iframes by other apps |
| Paperless | `sec-3` + `acc-tailscale` | Internal tool, hardened, VPN-only |

### Pro Mode: Custom Combinations

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

Available building blocks (defined in `security-blocks.yml`):

| Block | What it does |
|-------|-------------|
| `hdr-basic` | HSTS, nosniff, frameDeny |
| `hdr-basic-embed` | HSTS, nosniff, SAMEORIGIN |
| `hdr-strict` | + HSTS preload, referrer-policy, CSP report-only |
| `hdr-strict-embed` | + HSTS preload, same-origin referrer, CSP report-only |
| `rl-soft` | 100 avg / 50 burst |
| `rl-hard` | 20 avg / 40 burst |
| `compress` | gzip compression |
| `permissions-policy` | Blocks camera, mic, geolocation, payment, USB, gyroscope |
| `csp-enforce` | Enforcing CSP (may break apps with external scripts) |

## TLS Profiles

| Profile | Min Version | Notes |
|---------|------------|-------|
| `tls-basic` | TLS 1.2 | Compatible, no cipher restriction |
| `tls-aplus` | TLS 1.2 | Strict cipher suite, curve preferences |
| `tls-modern` | TLS 1.3 | TLS 1.3 only |

Set the default in `.env` via `TLS_DEFAULT_OPTION`. Override per-router in `tls.options`.

## ACME Resolvers

| Resolver | Challenge | Use case |
|----------|-----------|----------|
| `cloudflare-dns` | DNS-01 | Wildcard certs, private servers (no port 80 needed) |
| `httpResolver` | HTTP-01 | Standard certs, no Cloudflare dependency |

## Certificate strategy — wildcard vs. per-domain

Two working modes. Pick one for the instance.

### Path A — Wildcard (`*.example.com`)

One certificate covers every subdomain. Requires DNS at Cloudflare (or any provider the Traefik DNS-01 challenge supports).

**Setup:**

1. In `core/traefik/.env` set:
   ```env
   ACME_WILDCARD_DOMAIN=example.com
   CF_DNS_API_TOKEN=<real-token-with-Zone:Read-+-DNS:Edit>
   ```
2. Run `bash ops/scripts/render.sh` (generates `acme-wildcard.yml`)
3. `docker compose up -d`

**Apps:** leave the `tls.certresolver` label commented out in every `docker-compose.yml`. Traefik serves the wildcard for any subdomain via SNI.

### Path B — Per-domain (one cert per subdomain)

Each app requests its own cert. Works with any resolver, no wildcard setup.

**Setup:**

1. In `core/traefik/.env` leave `ACME_WILDCARD_DOMAIN` **unset** (or commented out)
2. Choose resolver per app via `APP_TRAEFIK_CERT_RESOLVER` in that app's `.env`:
   - `cloudflare-dns` for DNS-01 (no port 80 exposure needed)
   - `httpResolver` for HTTP-01 (port 80 must be public)
3. **Uncomment the `tls.certresolver` label** in each app's `docker-compose.yml`:
   ```yaml
   - "traefik.http.routers.${COMPOSE_PROJECT_NAME}.tls.certresolver=${APP_TRAEFIK_CERT_RESOLVER}"
   ```

### Hybrid

Both modes coexist. A router can request its own cert (uncommented `certresolver` label) even while a wildcard exists for the parent domain.

### Verify after setup

```bash
# Did Traefik receive a cert?
docker compose exec traefik cat /etc/traefik/acme/acme.json | \
  jq '.[] | .Certificates[]?.domain // "no certs yet"'

# Dashboard reachable over HTTPS?
curl -I https://<TRAEFIK_DASHBOARD_HOST>

# What do the logs say about ACME / cert issuance?
docker compose logs traefik 2>&1 | grep -iE "acme|cert|challenge" | tail -20
```

If `acme.json` is empty or the dashboard returns 404 before TLS: check
`docker compose logs traefik | grep -i error` — most issues surface as file-provider
errors or auth failures against Cloudflare.

## CrowdSec Bouncer Plugin (optional)

Blocks malicious IPs and inspects HTTP requests before they reach your apps.
CrowdSec detects threats (brute force, CVE probes, crawling), the bouncer enforces the bans at Traefik level.

### What it provides

| Feature | What it does |
|---------|-------------|
| **IP blocking** | Bans IPs flagged by CrowdSec scenarios (probing, brute force, sensitive files) |
| **Community blocklist** | Shared threat intelligence from the CrowdSec network |
| **AppSec / WAF** | Inspects request bodies for SQL injection, XSS, path traversal |
| **Stream mode** | Polls CrowdSec every 60s, caches decisions locally (no per-request latency) |

### How to enable

Step-by-step — all changes are in templates, rendered via `render.sh`.

```bash
# -----------------------------------------------
# Step 1: CrowdSec Engine must be running
# -----------------------------------------------
cd /path/to/secure-docker-blueprint/core/crowdsec
docker compose ps   # should show "healthy"

# -----------------------------------------------
# Step 2: Generate a bouncer API key
# -----------------------------------------------
docker exec crowdsec cscli bouncers add traefik-bouncer
# Save the output key — it cannot be retrieved later!

# -----------------------------------------------
# Step 3: Add the key to Traefik .env
# -----------------------------------------------
cd /path/to/secure-docker-blueprint/core/traefik
nano .env
# Add or uncomment:
#   CROWDSEC_BOUNCER_KEY=CmuiLn30RFNQkm+phT3Jc4u1ij5DZBA7MUvl1IG+zUE

# -----------------------------------------------
# Step 4: Enable the plugin in static config
# -----------------------------------------------
nano ops/templates/traefik.yml.tmpl
# Uncomment the experimental.plugins section:
#   experimental:
#     plugins:
#       bouncer:
#         moduleName: "github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin"
#         version: "v1.4.5"

# -----------------------------------------------
# Step 5: Enable the middleware in dynamic config
# -----------------------------------------------
nano ops/templates/dynamic/integrations.yml.tmpl
# Uncomment the sec-crowdsec block (the full plugin section)

# -----------------------------------------------
# Step 6: Render and restart
# -----------------------------------------------
./ops/scripts/render.sh
docker compose restart traefik
# Restart needed because the plugin is in static config.
# After this, middleware changes are hot-reloaded.

# -----------------------------------------------
# Step 7: Add to routers
# -----------------------------------------------
# Add sec-crowdsec@file to any router's middleware list.
# Example in an app's docker-compose.yml labels:
#   traefik.http.routers.myapp.middlewares=sec-crowdsec@file,acc-public@file,sec-2@file
#
# Or in config/dynamic/routers-system.yml for the dashboard:
#   middlewares:
#     - sec-crowdsec@file
#     - acc-tailscale@file
#     - sec-4@file
```

### How to disable

```bash
# Option A: Remove from specific routers only
# Remove "sec-crowdsec@file" from the router's middleware list.
# Hot-reloaded — no restart needed.

# Option B: Disable completely
# Comment out sec-crowdsec in integrations.yml.tmpl
# Re-render: ./ops/scripts/render.sh
# Hot-reloaded — no restart needed (plugin stays loaded but unused).

# Option C: Remove plugin entirely
# Comment out experimental.plugins in traefik.yml.tmpl
# Comment out sec-crowdsec in integrations.yml.tmpl
# Re-render + restart: ./ops/scripts/render.sh && docker compose restart traefik
```

### Minimum vs recommended config

| Setting | Minimum | Recommended |
|---------|---------|-------------|
| `crowdsecMode` | `stream` | `stream` |
| `crowdsecAppsecEnabled` | `false` | `true` (WAF protection) |
| `crowdsecAppsecFailureBlock` | `false` | `true` (block if WAF errors) |
| `crowdsecAppsecUnreachableBlock` | `false` | `true` (block if WAF unreachable) |

Minimum = IP blocking only (no WAF). Recommended = IP blocking + WAF.

### Geo-blocking

CrowdSec can block traffic by country. This is not part of the bouncer plugin — it runs inside the CrowdSec engine as a scenario.

```bash
# 1. Install the GeoIP enrichment collection
docker exec crowdsec cscli collections install crowdsecurity/geoloc-enrich

# 2. Create a custom scenario or use community scenarios
#    that filter on evt.Enriched.GeoLite2.Country.IsoCode
#    Example: ban all IPs from country "XX" after 1 request

# 3. Restart CrowdSec to load the new collection
cd /path/to/secure-docker-blueprint/core/crowdsec
docker compose restart
```

Bans from geo-blocking flow through the same LAPI — the bouncer picks them up automatically. No Traefik changes needed.

### Verify

```bash
# Check if plugin is loaded
docker compose logs traefik | grep -i crowdsec

# Check bouncer connection from CrowdSec side
docker exec crowdsec cscli bouncers list

# Test: ban an IP and verify it's blocked
docker exec crowdsec cscli decisions add --ip 1.2.3.4 --duration 1h --reason "test"
curl -H "X-Forwarded-For: 1.2.3.4" https://your-app.example.com
# Should return 403 Forbidden

# Clean up test ban
docker exec crowdsec cscli decisions delete --ip 1.2.3.4
```

### Troubleshooting

| Problem | Check |
|---------|-------|
| Plugin not loading | `docker compose logs traefik` — look for plugin errors. Did you uncomment `experimental.plugins`? |
| 403 for legitimate IPs | `docker exec crowdsec cscli decisions list` — check if the IP is banned. Remove with `cscli decisions delete --ip X.X.X.X` |
| WAF blocking valid requests | Set `crowdsecAppsecEnabled: false` temporarily. Check CrowdSec logs for false positives |
| Bouncer not connecting | `docker exec crowdsec cscli bouncers list` — check last heartbeat. Verify both containers are on `proxy-public` network |
| High latency | Verify `crowdsecMode: stream` (not `live`). Stream mode has no per-request overhead |

## Incident Quickmoves

**Lock admin service to VPN only:**
Change the router's middleware from `acc-public@file` to `acc-tailscale@file`.

**Scanner/abuse hitting a service:**
Escalate security from `sec-2@file` to `sec-4@file` (hard rate limit).

**Certificate problem:**
Switch the router's `certResolver` between `cloudflare-dns` and `httpResolver`.

All changes are in `config/dynamic/*.yml` — Traefik picks them up automatically (file watcher is enabled).

## Reset

Delete all rendered config files (templates stay untouched):

```bash
bash ops/scripts/reset-templates.sh
```
