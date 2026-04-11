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
