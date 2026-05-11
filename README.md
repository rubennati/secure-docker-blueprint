<div align="center">

# Secure Docker Blueprint

**Modular, security-hardened Docker Compose setups for self-hosted infrastructure.**

Hardened configurations for 40+ services — standardized security baseline, Docker Secrets, Traefik routing, CrowdSec integration, and network isolation out of the box.

[![CI](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.5.1-blue)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-pre--1.0-yellow)](ROADMAP.md)

</div>

> **Pre-1.0** — structure is stable and core services are ready to use, but paths, env variables, and defaults can still change before v1.0. See [ROADMAP.md](ROADMAP.md) for the v1.0 criteria.

---

## Features

- **Docker Secrets** — passwords and tokens via `_FILE` pattern or custom entrypoint; documented deviations where upstream support is missing
- **Socket Proxy** — no direct Docker socket access on app containers
- **Network Isolation** — databases and backends in isolated networks, no internet exposure
- **Pinned Versions** — every image uses an explicit version tag, never `:latest`
- **Consistent Structure** — every service follows the same compose and env patterns
- **Template-based Config** — Traefik and dnsmasq configs rendered via `envsubst`
- **Modular** — use any combination of services, each works independently
- **Zero Hardcoded Values** — everything configurable via `.env`

## What's Included

### Core Infrastructure

| Service | Status | Description |
|---------|--------|-------------|
| [Traefik](core/traefik/) | ✅ | Reverse proxy with Socket Proxy, 5 security levels, 3 TLS profiles, access policies |
| [Authentik](core/authentik/) | ✅ | SSO / Identity Provider for centralized authentication (Forward-Auth, OAuth2 / OIDC / SAML) |
| [OnlyOffice](core/onlyoffice/) | ✅ | Document editing server for Seafile, Nextcloud, etc. |
| [dnsmasq](core/dnsmasq/) | ✅ | DNS forwarder with wildcard zones for Tailscale / split-DNS setups |
| [acme-certs](core/acme-certs/) | ✅ | Certificate tool (acme.sh) for devices without Traefik (NAS, routers) |
| [CrowdSec](core/crowdsec/) | ✅ | Intrusion detection engine + Traefik bouncer plugin — log analysis, threat decisions, L7 blocking |
| [Whoami](core/whoami/) | ✅ | Traefik debug service to verify routing, TLS, and middlewares |
| [Dockhand](core/dockhand/) | ✅ | Docker management with Git-based stacks |
| [Portainer](core/portainer/) | ✅ | Docker management UI |
| [Hawser](core/hawser/) | ✅ | Remote Docker agent for Dockhand |
| [Portainer Agent](core/portainer-agent/) | ✅ | Remote Docker agent for Portainer (multi-host) |

Planned in `core/`: Keycloak (alternative / heavier IAM next to Authentik).

### Repository layout

Five top-level areas, each with a clear mandate. Per-category READMEs (`core/README.md`, `business/README.md`, `monitoring/README.md`, `backup/README.md`) describe what belongs where and why.

| Directory | Scope |
|---|---|
| [`core/`](core/) | Infrastructure shared by everything — Traefik, CrowdSec, identity providers (Authentik + Keycloak planned), OnlyOffice, certs |
| [`apps/`](apps/) | General-purpose self-hosted apps — equally useful for private homelab or a company |
| [`business/`](business/) | Apps that only make sense in a company context — invoicing, helpdesk, newsletter, compliance |
| [`monitoring/`](monitoring/) | Ops observability — uptime, metrics, content-change watching, disk SMART |
| [`backup/`](backup/) | Ops backup — Kopia / Bareos / UrBackup, structurally separate because of privileged access + remote targets |

### Applications

The blueprint takes a **choice-matrix** approach: where several tools compete (dashboards, photo galleries, wikis, form builders), multiple options are included so you can test and pick what fits.

**Status:** ✅ Ready · 🚧 Draft · 📋 Planned

#### Dashboards & launchers

| App | Stack | Status | Description |
|---|---|---|---|
| [Dashy](apps/dashy/) | Single container | ✅ | Homelab dashboard, YAML-configured |
| [Heimdall](apps/heimdall/) | Single container (LSIO) | ✅ | App-launcher with widget support |
| [Homarr](apps/homarr/) | Single container | ✅ | Modern dashboard with rich integrations |
| [Homepage](apps/homepage/) | Single container | ✅ | File-based YAML dashboard (gethomepage) |

#### Publishing & knowledge

| App | Stack | Status | Description |
|---|---|---|---|
| [Ghost](apps/ghost/) | App + MySQL | ✅ | Blog / CMS with SMTP + optional ActivityPub (Fediverse) |
| [WordPress](apps/wordpress/) | App + MariaDB | ✅ | Classic CMS, hardened (mu-plugin + test-script) |
| [BookStack](apps/bookstack/) | App (LSIO) + MariaDB | ✅ | Wiki / knowledge base (Laravel) |

#### Photo galleries

Five options — test and pick what fits your workflow.

| App | Stack | Status | Description |
|---|---|---|---|
| [Immich](apps/immich/) | Server + ML + Postgres (pgvectors) + Valkey | ✅ | AI-powered photo backup with mobile apps |
| [LibrePhotos](apps/librephotos/) | Nginx + Django+ML + React + pgautoupgrade | ✅ | Google-Photos-like (OwnPhotos fork) |
| [Lychee](apps/lycheeorg/) | App (Laravel) + MariaDB + Redis | ✅ | Clean, fast gallery |
| [PhotoPrism](apps/photoprism/) | App (Go+TensorFlow) + MariaDB | ✅ | AI classification + WebDAV |
| [Photoview](apps/photoview/) | App (Go+GraphQL) + MariaDB | ✅ | RAW processing + face recognition |

#### Scheduling & booking

Three 1:1-booking apps as a choice-matrix (pick one), plus a planned group-polling tool for a different axis.

| App | Stack | Status | When to use |
|---|---|---|---|
| [Cal.diy](apps/caldiy/) | Next.js + Postgres + Redis | ✅ | MIT community edition of Cal.com (community fork, personal use). |
| [Easy!Appointments](apps/easyappointments/) | PHP + MariaDB | ✅ | Lightweight PHP alternative, established 2013, GPL-3.0. |

Planned: **Rallly** (group scheduling polls — Doodle alternative, complementary not competing with the 1:1 bookers above).

#### Productivity & personal

| App | Stack | Status | Description |
|---|---|---|---|
| [Monica](apps/monicahq/) | App (Laravel) + MariaDB | ✅ | Personal CRM for relationships |
| [NocoDB](apps/nocodb/) | Single container + SQLite | ✅ | No-code database / spreadsheet UI (Airtable alternative) |
| [OpnForm](apps/opnform/) | API (Laravel) + UI (Nuxt) + Postgres + Redis | ✅ | Self-hosted form builder (Typeform alternative) |
| [n8n](apps/n8n/) | Single container + SQLite | ✅ | Visual workflow automation (Zapier alternative) |

> **Cloud-free data-collection chain:** `OpnForm → n8n → NocoDB` — forms collect, n8n transforms, NocoDB stores + presents. All three on `proxy-public`, addressable as `http://<app>-app:<port>` for internal calls.

#### File sync & documents

| App | Stack | Status | Description |
|---|---|---|---|
| [Nextcloud](apps/nextcloud/) | App + MariaDB + Redis + Nginx + Cron | ✅ | File sync, collaboration, optional OnlyOffice |
| [Paperless-ngx](apps/paperless-ngx/) | App + Postgres + Redis + Gotenberg + Tika | ✅ | Document management with OCR, optional Authentik SSO |
| [Seafile](apps/seafile/) | App + MariaDB + Memcached + optional components | ✅ | File sync & share (community edition) |
| [Seafile Pro](apps/seafile-pro/) | App + MariaDB + Memcached + SeaDoc + ClamAV + SeaSearch | ✅ | File sync & share (pro edition) |

#### Identity & security

| App | Stack | Status | Description |
|---|---|---|---|
| [Vaultwarden](apps/vaultwarden/) | App + MariaDB | ✅ | Bitwarden-compatible password manager |

Planned (apps/): Headscale (self-hosted Tailscale control server), PrivateBin, SnapPass.

#### Networking

| App | Stack | Status | Description |
|---|---|---|---|
| [UniFi Network App](apps/unifi/) | Controller (LSIO) + MongoDB 4.4 | 🚧 | Ubiquiti UniFi device controller |

#### Developer & admin tools

| App | Stack | Status | Description |
|---|---|---|---|
| [Adminer](apps/adminer/) | Single container | ✅ | Database administration UI (connects to other apps' DBs) |
| [IT-Tools](apps/it-tools/) | Single container | ✅ | Collection of IT / developer utilities (JSON, hash, regex, etc.) |

Docker-management tools (Dockhand / Portainer / Hawser) moved to [`core/`](core/) — they're infrastructure, not apps.

Planned (apps/): Wiki.js, Outline, Formbricks, HeyForm, Shlink.

### Business apps

See [`business/README.md`](business/README.md) for the full category README + rollout phases.

| App | Function | Status | Description |
|---|---|---|---|
| [OpenProject CE](business/openproject/) | Project management | ✅ | Full PM — Gantt, kanban, work packages, time tracking. CE = local accounts only, no SSO. |
| [Vikunja](business/vikunja/) | Task management | ✅ | Kanban, lists, Gantt — Trello / Planner alternative. Authentik OIDC live-tested, SSO-only. |
| [Invoice Ninja](business/invoiceninja/) | Billing | ✅ | Invoicing, quotes, client portal |
| [Dolibarr](business/dolibarr/) | ERP / CRM | ✅ | Accounting, projects, HR, inventory |
| [Kimai](business/kimai/) | Time tracking | ✅ | Per-project/customer hours → Invoice Ninja |
| [Listmonk](business/listmonk/) | Newsletter | ✅ | Mailing list + transactional mail |
| [Matomo](business/matomo/) | Web analytics | ✅ | GDPR-compliant, full-featured (Google Analytics alternative) |
| [Zammad](business/zammad/) | Helpdesk | ✅ | Full 7-service helpdesk / ticketing / SLA |
| [OpenSign](business/opensign/) | E-signatures | ✅ | DocuSign alternative, eIDAS-capable |

Planned: Ackee, Plausible CE, Live Helper Chat, Eramba GRC.

### Monitoring

See [`monitoring/README.md`](monitoring/README.md) for the full category README.

| App | Axis | Status | Description |
|---|---|---|---|
| [Uptime Kuma](monitoring/uptime-kuma/) | Uptime (UI) | ✅ | Click-config uptime monitor, 90+ notification integrations |
| [Gatus](monitoring/gatus/) | Uptime (YAML) | 🚧 | Config-as-code health checks with Prometheus export |
| [Beszel](monitoring/beszel/) | Host metrics (hub) | ✅ | Lightweight hub + local agent for CPU / RAM / disk / docker stats |
| [Beszel Agent](monitoring/beszel-agent/) | Host metrics (remote agent) | ✅ | Standalone agent for additional hosts; pairs with Beszel hub |
| [changedetection.io](monitoring/changedetection/) | Content watcher | 🚧 | Page diff + notification (restock / price / ToS) |
| [Healthchecks](monitoring/healthchecks/) | Cron / scheduled-job | ✅ | Dead-man's switch for backups / cron / scheduled tasks |

Planned: Statping, ciao, Checkmate, Zabbix, Grafana + Prometheus, Scrutiny.

### Backup

See [`backup/README.md`](backup/README.md) for tool choices and the per-app isolation principle.

Planned: Kopia, Borgmatic, Bareos, UrBackup.

## Quick Start

```bash
# Clone
git clone https://github.com/your-user/secure-docker-blueprint.git
cd secure-docker-blueprint

# 1. Start Traefik (required for all apps)
cd core/traefik
cp .env.example .env              # Edit: domain, email, DNS provider
./ops/scripts/render.sh           # Render config templates
docker compose up -d

# 2. Add an app (e.g. Vaultwarden)
cd ../../apps/vaultwarden
cp .env.example .env              # Edit: domain, security level

mkdir -p .secrets
openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt
openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt

docker compose up -d
```

Every app follows the same workflow: copy `.env.example` → create secrets → `docker compose up -d`.

## Security Model

Every service in this blueprint enforces:

| Rule | How |
|------|-----|
| No privilege escalation | `no-new-privileges:true` on every container |
| Secrets isolated | Docker Secrets (`_FILE` or custom entrypoint); deviations documented per app |
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
secure-docker-blueprint/
│
├── core/                        # Infrastructure (always needed)
│   ├── traefik/                 #   Reverse proxy + socket proxy
│   ├── authentik/               #   SSO / Identity provider
│   ├── crowdsec/                #   Intrusion detection + Traefik bouncer
│   ├── onlyoffice/              #   Document editing server
│   ├── dnsmasq/                 #   DNS forwarder / split-DNS
│   ├── acme-certs/              #   Certificate tool (acme.sh)
│   ├── whoami/                  #   Traefik debug service
│   ├── dockhand/                #   Docker management (Git-based stacks)
│   ├── hawser/                  #   Remote Docker agent for Dockhand
│   ├── portainer/               #   Docker management UI
│   └── portainer-agent/         #   Remote Docker agent for Portainer
│
├── apps/                        # General-purpose apps (homelab + company)
│   ├── dashy/  heimdall/  homarr/  homepage/
│   ├── ghost/  wordpress/  bookstack/
│   ├── immich/  paperless-ngx/  nextcloud/  seafile/  seafile-pro/
│   ├── vaultwarden/
│   ├── nocodb/  n8n/  opnform/  monicahq/
│   ├── caldiy/  easyappointments/
│   ├── adminer/  it-tools/  unifi/
│   └── ...
│
├── business/                    # Company-only apps
│   ├── openproject/  vikunja/
│   ├── invoiceninja/  dolibarr/  kimai/
│   ├── listmonk/  matomo/  zammad/  opensign/
│   └── ...
│
├── monitoring/                  # Ops observability
│   ├── uptime-kuma/  gatus/  beszel/  changedetection/  healthchecks/
│   └── ...
│
├── backup/                      # Backup tooling
│
├── docs/
│   ├── standards/               # Conventions and patterns
│   ├── bugfixes/                # Per-incident root-cause docs
│   ├── audits/                  # Consistency & maintenance audit logs
│   └── templates/               # Starter template for new apps
│
└── scripts/
    └── overview.sh              # Dashboard of all running services
```

### Per-App Layout

Every app follows the same structure:

```
apps/example/
├── docker-compose.yml           # Standardized block order
├── .env.example                 # All variables with placeholders
├── config/                      # Config files (committed)
├── .secrets/                    # Secret files (gitignored)
└── volumes/                     # Persistent data (gitignored)
```

## Conventions

All services follow documented standards. See [docs/standards/](docs/standards/):

- **[Compose Structure](docs/standards/compose-structure.md)** — block order, rules, common patterns
- **[Env Structure](docs/standards/env-structure.md)** — section order, variable rules, checklist
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
