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
| `TAILSCALE_CIDR_V4` | Your Tailscale IPv4 CIDR (default: `100.64.0.0/10`) |
| `TAILSCALE_CIDR_V6` | Your Tailscale IPv6 CIDR (default: `fd7a:115c:a1e0::/48`) |

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

```text
.env.example                          # All configurable variables
docker-compose.yml                    # Docker Socket Proxy + Traefik
network-dual-stack.yml                # Optional overlay: IPv4+IPv6 on proxy-public
docs/
  ipv6-dual-stack.md                  # IPv4-only vs. dual-stack — concepts, migration, troubleshooting
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

## IPv4-only vs. Dual-Stack Networking

`proxy-public` (the network Traefik and every routed app share) is **IPv4-only by default** — zero change for existing installs. Tailscale always hands out an IPv6 address to every client; if a Tailscale client connects over IPv6 while `proxy-public` is IPv4-only, Traefik loses the real client IP (access logs show `ClientHost=172.x.x.x`, the Docker gateway, instead of the real Tailscale address) and `acc-tailscale`'s `ipAllowList` blocks it. See [`docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`](../../docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md) for the original incident.

Cloudflare-fronted public traffic is unaffected either way — real client IPs there come from `forwardedHeaders.trustedIPs` (Cloudflare's published ranges, configured in `traefik.yml.tmpl`), not from the network's IP family.

**Recommended for new deployments — dual-stack from day one:**

```bash
# .env: uncomment and set
#   PUBLIC_NETWORK_SUBNET_V4=172.30.0.0/16
#   PUBLIC_NETWORK_SUBNET_V6=<your own ULA prefix>/64
#   COMPOSE_FILE=docker-compose.yml:network-dual-stack.yml
# Docker daemon prerequisites first — see docs/ipv6-dual-stack.md

docker compose up -d

# Verify it actually applied — EnableIPv6 must be true. This command
# only CREATES a dual-stack network; if proxy-public already existed
# (e.g. you're re-running this against a live deployment instead of a
# fresh one), Compose reuses the existing network as-is and does NOT
# error — so always check this rather than assuming the command above
# succeeded silently:
docker network inspect "$(grep ^PUBLIC_NETWORK= .env | cut -d= -f2)" \
  --format 'EnableIPv6={{.EnableIPv6}}'
```

**This command only works for a fresh `proxy-public` that doesn't exist yet.** Migrating an existing IPv4-only install needs a parallel network + tested cutover, not an in-place edit — Docker cannot add IPv6 to a network that already exists without recreating it, and Compose will not warn you if you try. Full explanation (why the public network needs IPv6 but `app-internal` doesn't, why this isn't solved with `network_mode: host`), Docker daemon prerequisites with backup/rollback, the migration guide, and troubleshooting commands: **[`docs/ipv6-dual-stack.md`](docs/ipv6-dual-stack.md)**.

**Setting `COMPOSE_FILE` in `.env` (above) is not optional convenience — set it.** Once the dual-stack network exists, any later `docker compose` command run *without* the overlay (e.g. someone runs `docker compose up -d --force-recreate traefik` and forgets the `-f` flag) makes Compose see only the IPv4-only network definition from `docker-compose.yml`. Compose then tries to remove and recreate the network to match — which fails loudly if other containers are still attached to it (`network proxy-public has active endpoints`, and Traefik ends up stopped until you redo the command correctly), or can silently revert the network to IPv4-only if nothing else happens to be attached. `COMPOSE_FILE` in `.env` means every future command in this directory includes the overlay automatically, with no flag to forget.

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
| `acc-local` | LAN only — `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `fc00::/7` (hardcoded RFC1918 + ULA) |
| `acc-tailscale` | Tailscale/VPN only — `TAILSCALE_CIDR_V4` + `TAILSCALE_CIDR_V6` from `.env` |
| `acc-private` | LAN + Tailscale combined |
| `acc-deny` | Nobody (emergency kill switch) |

> **Note:** `acc-local` and `acc-private` use hardcoded RFC1918 ranges (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`) + IPv6 ULA (`fc00::/7`). These are universal constants and cannot be set via `.env` — `envsubst` would render a comma-separated string as a single YAML entry, which Traefik cannot parse. Only the Tailscale CIDRs are configurable via `.env`.

### Security Levels

Each level builds on the previous one. `e` = `SAMEORIGIN` instead of `DENY`: the app may frame its own pages, but a different subdomain is a different origin, so `e` does not let one stack embed another. See [Choosing the level for an app](../../docs/standards/traefik-security.md#choosing-the-level-for-an-app).

| Level | What it includes | Recommended for |
|-------|-----------------|-----------------|
| `sec-0` | Nothing | Debug, naked proxy |
| `sec-1` | Basic headers + compress | Internal tools, monitoring |
| `sec-1e` | Like sec-1, iframe-friendly | Internal tools embedded in other apps |
| **`sec-2`** | **+ soft rate limit** | **Standard for most apps** (recommended default) |
| `sec-2e` | Like sec-2, iframe-friendly | OnlyOffice, editors embedded in other apps |
| `sec-2-spa` | sec-1 + SPA rate limit | VPN-only SPA, basic headers |
| `sec-3` | + strict headers + permissions-policy | Public-facing apps, hardened |
| `sec-3e` | Like sec-3, iframe-friendly | Vaultwarden, apps needing SAMEORIGIN |
| `sec-3-spa` | sec-3 + SPA rate limit instead of soft | VPN-only SPA, hardened — e.g. Dockhand, n8n, NocoDB |
| `sec-4` | + hard rate limit | Sensitive apps, login pages, admin panels |
| `sec-5` | + CSP enforce | Maximum — only for CSP-tested apps (e.g. Whoami) |

> **SPA variants** (`sec-*-spa`): SPA frameworks (SvelteKit, React, Vue) load 50–100 JS chunks on initial page load. `rl-soft` and `rl-hard` throttle this burst with 429s. `rl-spa` allows the initial burst and applies rate limiting thereafter. Use `sec-*-spa` only for VPN-gated apps — `rl-spa` is more permissive than `rl-soft`.
>
> Note: `sec-4-spa` does not exist — it would be identical to `sec-3-spa` (both replace the rate limiter with `rl-spa`, the only difference between sec-3 and sec-4 is `rl-soft` vs `rl-hard`).

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
| Dockhand / n8n / NocoDB | `sec-3-spa` + `acc-tailscale` | VPN-only SPA — hard/soft rate limit causes 429 on initial chunk burst |

### Pro Mode: Custom Combinations

For apps that don't fit any preset, combine building blocks directly:

```yaml
# Example: strict headers with embed + hard rate limit + CrowdSec
middlewares:
  - crowdsec-basic@file
  - acc-tailscale@file
  - hdr-strict-embed@file
  - rl-hard@file
  - compress@file
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
| `rl-spa` | High burst allowance for SPA initial load |
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

| Resolver | Challenge | Needs reachable | Wildcards | Use case |
|----------|-----------|-----------------|-----------|----------|
| `cloudflare-dns` | DNS-01 | nothing inbound | yes | Wildcard certs, and any host with no public port at all |
| `httpResolver` | HTTP-01 | TCP 80 | no | Standard certs, no Cloudflare account needed |
| `tlsResolver` | TLS-ALPN-01 | TCP 443 | no | One public port for everything — no port 80 forward, no DNS credentials |

All three are defined in the rendered configuration. A resolver that no router
names issues nothing, so defining one costs nothing; the choice is made per
router, through `APP_TRAEFIK_CERT_RESOLVER` (or `TRAEFIK_DASHBOARD_CERT_RESOLVER`).

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

**Dashboard:** leave `TRAEFIK_DASHBOARD_CERT_RESOLVER` empty. It follows the same rule as the apps — `render.sh` omits the router's `certResolver` and Traefik serves the wildcard. A resolver set here requests a second certificate and publishes the dashboard hostname in Certificate Transparency logs; `validate.sh` warns when both are set.

`*.example.com` matches exactly one label: `traefik.example.com` is covered, `traefik.admin.example.com` is not. `validate.sh` checks the actual relationship between `TRAEFIK_DASHBOARD_HOST` and `ACME_WILDCARD_DOMAIN`, and refuses a configuration where neither a covering wildcard nor a resolver exists.

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

4. Set `TRAEFIK_DASHBOARD_CERT_RESOLVER` — without a wildcard the dashboard needs its own certificate.

### Path C — Per-domain over port 443 only (TLS-ALPN-01)

The same per-domain shape as Path B, with the challenge answered on 443 instead
of 80. Let's Encrypt opens a TLS connection, asks for the ALPN protocol
`acme-tls/1`, and Traefik serves the challenge certificate on the connection it
is already listening on. Nothing else is forwarded, and no DNS credentials exist
anywhere in the deployment.

This is the path for a firewall that forwards one port:

```text
Internet ──TCP 443──▶ firewall ──TCP 443──▶ this host ──▶ Traefik
                                                            ├── TLS-ALPN-01 → certificate
                                                            └── router → application
```

**Setup:**

1. In `core/traefik/.env` leave `ACME_WILDCARD_DOMAIN` **unset**
2. Per app: `APP_TRAEFIK_CERT_RESOLVER=tlsResolver` in that app's `.env`, and
   uncomment the `tls.certresolver` label in its `docker-compose.yml`
3. `TRAEFIK_DASHBOARD_CERT_RESOLVER=tlsResolver` if the dashboard is published

**Three conditions, and all three are outside this repository:**

- **TCP 443 reachable from the internet.** UDP 443 is HTTP/3 and plays no part in
  the challenge — a firewall that forwards only TCP is enough.
- **Nothing may terminate TLS in front of Traefik.** A CDN or load balancer in
  front answers the handshake itself and does not forward the ALPN protocol;
  issuance then fails with `cannot negotiate ALPN protocol "acme-tls/1"`. This
  rules the path out behind **Cloudflare's proxy (orange cloud)** — which
  `apps/caldiy/docs/cloudflare.md` recommends for that stack. Use DNS-01 there,
  or set the record to DNS-only. HTTP-01 is unaffected by proxy status; this is
  the one resolver that is not.
- **No wildcards.** Let's Encrypt issues those over DNS-01 alone. A deployment
  that wants `*.example.com` needs `cloudflare-dns` no matter which ports are open.

**On a host already running wildcard mode, this resolver will not visibly do
anything for a hostname the wildcard already covers.** Traefik matches an
incoming SNI against every certificate already in its store, independent of
which resolver is named on the router; if the wildcard already covers the
hostname, that match wins and no request ever reaches `tlsResolver`'s ACME
provider. Verified on a live host on 2026-09-15: the resolver loaded without
error and the router carried it correctly, and `acme.json` still held nothing
under `tlsResolver` after the restart, because `*.dob.qode.at` already covered
the test hostname. To actually see this resolver issue something, point it at
a hostname the wildcard does not cover.

**Port 80 becomes optional on this path.** Publishing it is still the default,
because the `web` entrypoint redirects HTTP to HTTPS and a visitor who types a
bare hostname lands on `http://`. Dropping the forward at the firewall keeps that
redirect working for anyone already inside; removing `"${TRAEFIK_HTTP_PORT}:80/tcp"`
from `docker-compose.yml` removes it entirely, and those visitors get a connection
refused instead of a redirect.

### Migrating an existing wildcard deployment

Before this rule existed, the dashboard always carried a resolver, so a wildcard
deployment also holds a separate certificate for its dashboard hostname. Emptying
`TRAEFIK_DASHBOARD_CERT_RESOLVER` and re-rendering stops **new** requests for it.
It does not remove the one already stored:

- Traefik loads every certificate in `acme.json` into its certificate store at
  startup, whether or not a router references it, and keeps renewing it based on
  expiry alone. The stored dashboard certificate therefore stays live and keeps
  being served for that hostname.
- Traefik documents no command, API or procedure for retiring a single stored
  certificate, so there is no supported way to remove it selectively.
- Certificate Transparency logs are append-only. A hostname already published
  stays published, whatever happens to the certificate.

The change is therefore forward-looking. A new installation issues no separate
dashboard certificate; an existing one stops requesting further ones. Neither the
stored certificate nor the transparency entry it already produced can be undone by
configuration — changing the dashboard hostname does not retire either, it only
means the new name is served by the wildcard.

### Hybrid

Both modes coexist. A router can request its own cert (uncommented `certresolver` label) even while a wildcard exists for the parent domain.

### Verify after setup

```bash
# Which certificate is actually served for a hostname? This is the check that
# catches a missing resolver: CN=TRAEFIK DEFAULT CERT means nothing matched.
openssl s_client -connect <hostname>:443 -servername <hostname> 2>/dev/null | \
  openssl x509 -noout -subject -issuer -dates
# Wildcard mode, dashboard included: subject=CN=example.com, SAN *.example.com
# Per-domain mode:                   subject=CN=<hostname>

# Which certificates does Traefik hold? Domain metadata only.
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

One switch in `.env`. The templates are not edited — `render.sh` reads
`CROWDSEC_BOUNCER_ENABLED` and emits the plugin block into `config/traefik.yml`
and the middleware file `config/dynamic/crowdsec.yml`, or neither.

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
# Step 3: Set the switch in Traefik's .env
# -----------------------------------------------
cd /path/to/secure-docker-blueprint/core/traefik
nano .env
#   CROWDSEC_BOUNCER_ENABLED=true
#   CROWDSEC_BOUNCER_PLUGIN_VERSION=v1.7.1      # a release the running Traefik loads
#   CROWDSEC_BOUNCER_KEY=<key-from-step-2>

# -----------------------------------------------
# Step 4: Render, validate, restart
# -----------------------------------------------
./ops/scripts/render.sh
./ops/scripts/validate.sh
docker compose up -d --force-recreate traefik
# The plugin block is static configuration, read at startup — a restart is
# required. validate.sh refuses the switch without a key, a plugin version
# that is not a release tag, and a config/ that does not match the switch.

# -----------------------------------------------
# Step 5: Attach it to routers (start with whoami only)
# -----------------------------------------------
# A rendered middleware protects nothing on its own. Read
# core/crowdsec/docs/profiles.md and run the whoami-first validation, then
# put crowdsec-basic@file FIRST on a router — in the application's .env:
#   APP_TRAEFIK_THREAT=crowdsec-basic@file,
# (the trailing comma is part of the value — docs/standards/traefik-labels.md)
#
# Or in config/dynamic/routers-system.yml for the dashboard:
#   middlewares:
#     - crowdsec-basic@file
#     - acc-tailscale@file
#     - sec-4@file
```

What the rendered result looks like, and what each half does:

| Half | File | Rendered when | Takes effect |
|---|---|---|---|
| Plugin declaration (`experimental.plugins.bouncer`) | `config/traefik.yml` | switch on | Traefik restart — static configuration |
| `crowdsec-basic`, `crowdsec-appsec` middlewares | `config/dynamic/crowdsec.yml` | switch on; the file is removed when off | hot reload |
| Router attachment | the application's labels | never by the switch — per app via `APP_TRAEFIK_THREAT` | recreate that app |

### How to disable

```bash
# Option A: Detach from specific routers only
# Remove crowdsec-basic@file from that router's middleware list
# (APP_TRAEFIK_THREAT= in the app's .env, recreate the app). Hot-reloaded.
# The plugin stays loaded and the middleware stays defined but unused.

# Option B: Switch the integration off
# First detach it from EVERY router — a router that names a middleware which
# no longer exists is disabled by Traefik, not left unprotected.
# Then, in .env:  CROWDSEC_BOUNCER_ENABLED=false
./ops/scripts/render.sh          # announces the removal and drops config/dynamic/crowdsec.yml
./ops/scripts/validate.sh
docker compose up -d --force-recreate traefik   # the plugin block is static config
```

### Migrating an installation that enabled the integration before the switch

Before the switch, the README had the operator uncomment blocks in two tracked
templates and render. Both templates are in git, so the next `git pull` or
checkout put the comments back — and the next `render.sh` then wrote a
`config/` without the plugin and without the middlewares while the running
container still had both. `render.sh` now refuses exactly that state:

```text
ERROR: config/ carries the CrowdSec integration ... but CROWDSEC_BOUNCER_ENABLED is not set in .env.
```

To carry the installation over:

```bash
# 1. Read what config/ currently has — this is what Traefik is running with
grep -nE 'version:' config/traefik.yml                     # the plugin version
grep -nE 'crowdsecLapiKey' config/dynamic/*.yml            # the key in use

# 2. Put both into .env, alongside the switch
#   CROWDSEC_BOUNCER_ENABLED=true
#   CROWDSEC_BOUNCER_PLUGIN_VERSION=<the version from step 1>
#   CROWDSEC_BOUNCER_KEY=<the key from step 1>

# 3. Render into a copy first and diff — the middlewares move from
#    integrations.yml into crowdsec.yml; the plugin block stays where it was
cp -r config /tmp/traefik-config-before
./ops/scripts/render.sh
diff -r /tmp/traefik-config-before config

# 4. If traefik.yml changed only in comments, no restart is needed: the file
#    provider hot-reloads the dynamic directory. If the plugin version changed,
#    restart. validate.sh confirms config/ and .env agree.
./ops/scripts/validate.sh
```

If the templates themselves were edited on that host, `git status` shows them
modified; `git checkout -- ops/templates` restores them. The state now lives in
`.env`, which is not tracked.

### Minimum vs recommended config

| Setting | Minimum | Recommended |
|---------|---------|-------------|
| `crowdsecMode` | `stream` | `stream` |
| `crowdsecAppsecEnabled` | `false` | `true` (WAF protection) |

Minimum = IP blocking only (no WAF). Recommended = IP blocking + WAF.

**The two fail-closed flags are not a recommended default.** This table used to
list `crowdsecAppsecFailureBlock` and `crowdsecAppsecUnreachableBlock` as
`true` under Recommended.
[`core/crowdsec/docs/appsec.md`](../crowdsec/docs/appsec.md#enabling-appsec-safely) is the
owner of that guidance and says the opposite: if AppSec is unreachable at the
moment Traefik evaluates a request and `crowdsecAppsecUnreachableBlock` is `true`,
every request returns 403 — the Traefik dashboard and every service behind the
proxy included. Both flags belong at the end of the incremental progression
documented there, after AppSec has run long enough for its false-positive rate to
be known, and not before.

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
| Plugin not loading | `docker compose logs traefik` — look for plugin errors. Is `CROWDSEC_BOUNCER_ENABLED=true` in `.env`, was `render.sh` run since, and was Traefik recreated afterwards? `grep -n experimental config/traefik.yml` shows whether the block was rendered |
| 403 for legitimate IPs | `docker exec crowdsec cscli decisions list` — check if the IP is banned. Remove with `cscli decisions delete --ip X.X.X.X` |
| WAF blocking valid requests | Set `crowdsecAppsecEnabled: false` temporarily. Check CrowdSec logs for false positives |
| Bouncer not connecting | `docker exec crowdsec cscli bouncers list` — check last heartbeat. Verify both containers are on the `crowdsec-security` network |
| High latency | Verify `crowdsecMode: stream` (not `live`). Stream mode has no per-request overhead |

## Incident Quickmoves

**Lock admin service to VPN only:**
Change the router's middleware from `acc-public@file` to `acc-tailscale@file`.

**Scanner/abuse hitting a service:**
Escalate security from `sec-2@file` to `sec-4@file` (hard rate limit).

**Certificate problem:**
Switch the router's `certResolver` between `cloudflare-dns` and `httpResolver`.

All changes are in `config/dynamic/*.yml` — Traefik picks them up automatically (file watcher is enabled).

## Logging & Logrotate

Traefik writes two log files into `volumes/logs/` (bind-mounted from the host):

| File | What it contains |
|------|-----------------|
| `traefik.log` | Startup, config reload, TLS, errors |
| `access.log` | HTTP requests answered with `200-599`, one JSON object per line |

### What the access log contains, and what it costs

`traefik.yml` filters on `statusCodes: 200-599`. That is wider than the error-only
filter it is easy to assume, and it is deliberate — CrowdSec parses this file, and
a scenario about successful activity cannot fire on a log that holds only errors.

What it means in practice:

| | |
|---|---|
| **Included** | every request answered `2xx`, `3xx`, `4xx` and `5xx`. The range is inclusive at both ends, so `300-399` is inside it — a backend's `302` login redirect or a `304` reaches the log like any other response |
| **Excluded** | `1xx` |
| **The global redirect is still missing** | the HTTP-to-HTTPS redirect on the `web` entrypoint writes no access log line at all, so no scenario can match on it. That is not the status filter — widening or narrowing the range does not bring it back |
| **Volume** | one line per successful request rather than per failed one. On a busy host that is orders of magnitude more, which is why logrotate below is not optional |
| **Query strings appear** | the request URI is logged whole. Anything an application accepts as a query parameter — a share token, a search term, an id — lands in this file and in every backup that includes it |
| **Not logged** | request bodies, cookies and `Authorization` headers. Traefik does not record them by default and nothing here turns that on |

Narrowing to `400-599` is a supported choice if the volume or the query strings
matter more than detection breadth. CrowdSec's shipped scenarios are built around
4xx and 5xx patterns — probing, sensitive file access, path traversal, CVE scans —
and keep working either way. What a narrower filter removes is the ability to write
a scenario about authenticated activity, or about a backend's redirect behaviour,
later.

**`docker compose logs traefik` shows nothing — this is expected.** Both files above are configured via `log.filePath` / `accessLog.filePath` in `traefik.yml`, so Traefik writes to files, not stdout. Read the logs directly instead:

```bash
docker exec traefik-core cat /var/log/traefik/traefik.log
docker exec traefik-core cat /var/log/traefik/access.log
# or from the host:
cat volumes/logs/traefik.log
```

`access.log` is buffered (`TRAEFIK_ACCESSLOG_BUFFER`, default 100 entries) — recent requests may not appear until the buffer flushes. `traefik.log` is not affected by this buffer and is the one to check first for startup/ACME/TLS issues.

Docker does **not** rotate bind-mount files. Without logrotate, `access.log` grows unboundedly on busy servers.

### Activate logrotate (one-time, on the host)

```bash
# Replace path with your actual deployment path
sudo sed 's|/path/to/secure-docker-blueprint|/srv/docker|g' \
  /srv/docker/core/traefik/config/logrotate/traefik \
  | sudo tee /etc/logrotate.d/traefik

# Verify
cat /etc/logrotate.d/traefik

# Dry-run to confirm it works
sudo logrotate -d /etc/logrotate.d/traefik
```

The config rotates daily, keeps 7 days and compresses with gzip. Both logs are
copied out and truncated in place (`copytruncate`); no signal is sent to the
container:

| Choice | Why |
|---|---|
| No `docker kill --signal=USR1` | Docker treats any `docker kill`, whatever the signal, as a stop by hand and cancels the restart policy until the next start. After a rotation that sent `USR1`, an OOM kill left Traefik down with every route. Measured on 2026-09-22 (Docker 29.8.1) |
| No rename for `traefik.log` | Traefik 3 announces "Closing and re-opening log files for rotation" on `USR1` and reopens the access log only; the main log descriptor stays on the renamed file. Measured on v3.7.13 on 2026-09-14 |
| `copytruncate` is safe | Traefik opens both files `O_APPEND` and continues at the new end. Lines written between the copy and the truncate are lost |

Earlier shapes of this file each had a failure: until 2026-09-14 one
rename-and-signal stanza for both logs left `traefik.log` empty after the first
rotation (`TROUBLESHOOTING.md` §8.3); until 2026-09-22 the signal for the access
log switched off the restart policy (§8.4). Both sections have the repair.

> **Note:** logrotate runs on the host, not inside the container. This is the correct approach for bind-mounted Docker log files — it is standard practice for any containerized app that writes logs to a host volume.

## Reset

Delete all rendered config files (templates stay untouched):

```bash
bash ops/scripts/reset-templates.sh
```

## Watchdog (optional)

Not installed by default. `ops/scripts/traefik-watchdog.sh` restarts this
container after it has been reported unhealthy for several consecutive
checks in a row, and only once per confirmed episode — see
[`core/host-watchdog/README.md`](../host-watchdog/README.md) for the shared
model, the reasoning, and why this is judged acceptable for Traefik
specifically (it holds no state) and not a general pattern.

## Backup

| | |
|---|---|
| **Database** | None. |
| **State** | `./volumes/letsencrypt` — `acme.json`, holding the ACME account key and every issued certificate |
| **Reproducible** | `./volumes/logs` · `./volumes/plugins-storage` — plugins are re-downloaded on start |
| **Quiescing** | Not needed. `acme.json` is rewritten atomically on issuance and renewal. |

No database hook. This stack is `source_directories` only, and the static and
dynamic configuration under `config/` is versioned in git rather than backed up
from the host.

**`acme.json` contains private keys.** It is the one file in this repository that
combines "small enough to overlook" with "grants the ability to impersonate every
host it covers". Two consequences for the backup plan:

- The archive containing it deserves the same protection as a secret store. It is
  not merely configuration.
- Its file mode is `600` and Traefik refuses to start if that is widened. A
  restore that flattens permissions produces a proxy that will not come up, which
  during an incident reads as a much larger failure than it is.

Certificates can be reissued, so this is recoverable. But reissuing during an
outage means DNS or HTTP validation has to work while the proxy is down.

**Restore order:** early. Nothing else in the deployment is reachable until the
proxy is up.
