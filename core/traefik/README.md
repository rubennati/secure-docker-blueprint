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
      security.yml.tmpl               # Security middleware chains
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

## Policies (2 Axes)

Every router gets **two** middlewares — one for access, one for security:

```yaml
middlewares:
  - acc-public@file, sec-2@file       # Public site, standard hardening
  - acc-tailscale@file, sec-4@file    # Admin tool, VPN + strict
```

### Access

| Middleware | Effect |
|-----------|--------|
| `acc-public` | No restriction (pass-through) |
| `acc-tailscale` | IP allowlist: Tailscale/VPN CIDR only |

### Security

| Level | Middleware | What it does |
|-------|-----------|-------------|
| 0 | `sec-0` | Nothing (debug/naked) |
| 1 | `sec-1` | Basic security headers (HSTS, XSS filter, nosniff, frameDeny) |
| 2 | `sec-2` | Soft rate limit + basic headers + compression |
| 3 | `sec-3` | Soft rate limit + extended headers (HSTS preload, referrer policy, CSP report-only) + compression |
| 4 | `sec-4` | Hard rate limit + extended headers + compression |

## Opt-in Hardening

Two additional middlewares that are **not** part of any chain. Add them per-router where the app can handle it:

| Middleware | Effect |
|-----------|--------|
| `sec-permissions-policy` | Blocks browser APIs: camera, mic, geolocation, payment, USB, gyroscope |
| `sec-csp-enforce` | Enforcing Content Security Policy (may break apps that load external scripts) |

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
cd /path/to/docker-ops-blueprint/core/crowdsec
docker compose ps   # should show "healthy"

# -----------------------------------------------
# Step 2: Generate a bouncer API key
# -----------------------------------------------
docker exec crowdsec cscli bouncers add traefik-bouncer
# Save the output key — it cannot be retrieved later!

# -----------------------------------------------
# Step 3: Add the key to Traefik .env
# -----------------------------------------------
cd /path/to/docker-ops-blueprint/core/traefik
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
nano ops/templates/dynamic/security.yml.tmpl
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
# Comment out sec-crowdsec in security.yml.tmpl
# Re-render: ./ops/scripts/render.sh
# Hot-reloaded — no restart needed (plugin stays loaded but unused).

# Option C: Remove plugin entirely
# Comment out experimental.plugins in traefik.yml.tmpl
# Comment out sec-crowdsec in security.yml.tmpl
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
cd /path/to/docker-ops-blueprint/core/crowdsec
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
