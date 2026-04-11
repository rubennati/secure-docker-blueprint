# Docker Ops Blueprint

**Modular, security-hardened Docker Compose setups for self-hosted infrastructure.**

Production-ready configurations for 14+ services — with standardized patterns, Docker Secrets, Traefik routing, and network isolation out of the box.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## Features

- **Docker Secrets** — passwords and tokens never in environment variables
- **Socket Proxy** — no direct Docker socket access on app containers
- **Network Isolation** — databases and backends in isolated networks, no internet exposure
- **Pinned Versions** — every image uses an explicit version tag, never `:latest`
- **Consistent Structure** — every service follows the same compose and env patterns
- **Template-based Config** — Traefik and dnsmasq configs rendered via `envsubst`
- **Modular** — use any combination of services, each works independently
- **Zero Hardcoded Values** — everything configurable via `.env`

## What's Included

### Core Infrastructure

| Service | Description |
|---------|-------------|
| [Traefik](core/traefik/) | Reverse proxy with Socket Proxy, 5 security levels, 3 TLS profiles, access policies |
| [Authentik](core/authentik/) | SSO / Identity Provider for centralized authentication (OpenID Connect) |
| [OnlyOffice](core/onlyoffice/) | Document editing server for Seafile, Nextcloud, etc. |
| [dnsmasq](core/dnsmasq/) | DNS forwarder with wildcard zones for Tailscale / split-DNS setups |
| [acme-certs](core/acme-certs/) | Certificate tool (acme.sh) for devices without Traefik (NAS, routers) |
| [Whoami](core/whoami/) | Traefik debug service to verify routing, TLS, and middlewares |

### Applications

| Service | Stack | Description |
|---------|-------|-------------|
| [Vaultwarden](apps/vaultwarden/) | App + MariaDB | Bitwarden-compatible password manager |
| [Ghost](apps/ghost/) | App + MySQL | Blog / CMS with SMTP |
| [Paperless-ngx](apps/paperless-ngx/) | App + Postgres + Redis + Gotenberg + Tika | Document management with OCR, optional Authentik SSO |
| [Seafile](apps/seafile/) | App + MariaDB + Memcached + optional components | File sync & share with SeaDoc, notifications, thumbnails |
| [WordPress](apps/wordpress/) | App + MariaDB | Classic CMS |
| [Cal.com](apps/calcom/) | App + Postgres | Scheduling and calendar booking |
| [Invoice Ninja](apps/invoiceninja/) | App + Nginx + MySQL | Invoicing and billing |
| [Portainer](apps/portainer/) | App + Socket Proxy | Docker management UI |
| [Dockhand](apps/dockhand/) | App + Postgres + Socket Proxy | Docker management with Git-based stacks |
| [Hawser](apps/hawser/) | App + Socket Proxy | Remote Docker agent for Dockhand |

## Quick Start

```bash
# Clone
git clone https://github.com/your-user/docker-ops-blueprint.git
cd docker-ops-blueprint

# 1. Start Traefik (required for all apps)
cd core/traefik
cp .env.example .env              # Edit: domain, email, DNS provider
./ops/scripts/render.sh           # Render config templates
docker compose up -d

# 2. Add an app (e.g. Vaultwarden)
cd ../../apps/vaultwarden
cp .env.example .env              # Edit: domain, security level

mkdir -p secrets
openssl rand -base64 32 > secrets/db_pwd.txt
openssl rand -base64 32 > secrets/db_root_pwd.txt

docker compose up -d
```

Every app follows the same workflow: copy `.env.example` → create secrets → `docker compose up -d`.

## Security Model

Every service in this blueprint enforces:

| Rule | How |
|------|-----|
| No privilege escalation | `no-new-privileges:true` on every container |
| Secrets not in env vars | Docker Secrets with `_FILE` pattern or custom entrypoint |
| No direct socket access | Socket Proxy with granular API filtering |
| Network isolation | Internal networks for databases and backend services |
| Read-only filesystem | Where the image supports it |
| Minimal capabilities | `cap_drop: ALL` where possible |

Three patterns for secret handling:

| Scenario | Pattern |
|----------|---------|
| Image supports `_FILE` env vars | `POSTGRES_PASSWORD_FILE: /run/secrets/...` |
| Image doesn't support `_FILE` | Custom entrypoint reads secret at runtime |
| Secret embedded in JSON config | Env var in `.env` (gitignored) |

## Project Structure

```
docker-ops-blueprint/
│
├── core/                        # Infrastructure (always needed)
│   ├── traefik/                 #   Reverse proxy + socket proxy
│   ├── authentik/               #   SSO / Identity provider
│   ├── onlyoffice/              #   Document editing
│   ├── dnsmasq/                 #   DNS forwarder/cache
│   ├── acme-certs/              #   Certificate tool (acme.sh)
│   └── whoami/                  #   Debug service
│
├── apps/                        # Applications (pick what you need)
│   ├── vaultwarden/
│   ├── ghost/
│   ├── paperless-ngx/
│   ├── seafile/
│   ├── wordpress/
│   ├── calcom/
│   ├── invoiceninja/
│   ├── portainer/
│   ├── dockhand/
│   └── hawser/
│
├── docs/
│   ├── standards/               # Conventions and patterns
│   └── templates/               # Starter template for new apps
│
└── scripts/
    └── overview.sh              # Dashboard of all services
```

### Per-App Layout

Every app follows the same structure:

```
apps/example/
├── docker-compose.yml           # Standardized block order
├── .env.example                 # All variables with placeholders
├── config/                      # Config files (committed)
├── secrets/                     # Secret files (gitignored)
└── volumes/                     # Persistent data (gitignored)
```

## Conventions

All services follow documented standards. See [docs/standards/](docs/standards/):

- **[Naming Conventions](docs/standards/naming-conventions.md)** — containers, env vars, networks, volumes, file structure
- **[Traefik Labels](docs/standards/traefik-labels.md)** — routing pattern, security levels, TLS profiles
- **[Security Baseline](docs/standards/security-baseline.md)** — required hardening, secret patterns, socket proxy rules
- **[Networking](docs/standards/networking.md)** — network types, isolation rules, special cases

## Adding a New App

```bash
cp -r docs/templates apps/my-new-app
cd apps/my-new-app
# Edit docker-compose.yml and .env.example following the standards
```

See [docs/templates/README.md](docs/templates/README.md) for details.

## Dashboard

Quick overview of all configured services:

```bash
./scripts/overview.sh
```

## Requirements

- **Docker** 24.0+ with Compose v2
- **Linux** host (tested on Debian 12/13)
- **Domain** with a DNS provider supported by Traefik (e.g. Cloudflare)
- **Optional:** Tailscale for `acc-tailscale` access policies

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features, services under evaluation, and future ideas.

## Contributing

Contributions are welcome. Please follow the [conventions](docs/standards/) when adding new services or modifying existing ones.

## License

[Apache License 2.0](LICENSE)
