<div align="center">

# Secure Docker Blueprint

**Modular, security-hardened Docker Compose setups for self-hosted infrastructure.**

Hardened configurations for 40+ services — standardized security baseline, Docker Secrets, Traefik routing, CrowdSec integration, and network isolation out of the box.

[![CI](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/ci.yml)
[![Trivy](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml/badge.svg)](https://github.com/rubennati/secure-docker-blueprint/actions/workflows/trivy.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rubennati/secure-docker-blueprint/badge)](https://scorecard.dev/viewer/?uri=github.com/rubennati/secure-docker-blueprint)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13091/badge)](https://www.bestpractices.dev/projects/13091)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.6.0-blue)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-pre--1.0-yellow)](ROADMAP.md)

</div>

> **Pre-1.0** — structure is stable and core services are ready to use, but paths, env variables, and defaults can still change before v1.0. See [ROADMAP.md](ROADMAP.md) for the v1.0 criteria.
Quick Navigation: [Features](#features) · [Installation](#installation) · [Core Infrastructure](#core-infrastructure) · [Applications](#applications) · [Business apps](#business-apps) · [Monitoring](#monitoring) · [Backup](#backup)

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

## Installation

This reaches a working Traefik with TLS, which every app routes through. The app
itself is installed from its own README — the steps differ per stack, and that
README is the procedure. Check [Requirements](#requirements) first; `envsubst` is
needed before the first command.

```bash
git clone https://github.com/rubennati/secure-docker-blueprint.git
cd secure-docker-blueprint
```

### 1. Traefik

```bash
cd core/traefik
cp .env.example .env
```

Set at least `ACME_EMAIL`, `TRAEFIK_DASHBOARD_HOST` and the DNS provider token
for your certificate resolver — `CF_DNS_API_TOKEN` ships as `__REPLACE_ME__` and
DNS-01 fails until it holds a real token.
[`core/traefik/README.md`](core/traefik/README.md#setup) lists every variable and
what it controls.

```bash
bash ops/scripts/validate.sh    # required variables present
bash ops/scripts/render.sh      # .tmpl → config files
bash ops/scripts/validate.sh    # nothing left unresolved
docker compose up -d
docker compose ps               # traefik and the socket proxy report healthy
```

The dashboard answers at `https://<TRAEFIK_DASHBOARD_HOST>`, reachable from the
VPN only by default. If it does not answer, or an app later returns 403 or 404,
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) lists the symptom, its cause and the
fix.

### 2. An app

Every stack shares the same shape — copy `.env.example`, set the values it names,
create the secrets it lists, `docker compose up -d` — but which values, which
secrets and in what order is per stack, and some steps have to happen before the
first start. Vaultwarden needs working SMTP configured before an account can be
created; Nextcloud installs itself unattended from the admin credentials.

Start from the stack's own README: [Vaultwarden](apps/vaultwarden/README.md) ·
[Nextcloud](apps/nextcloud/README.md) · or any entry in
[What's Included](#whats-included).

## Security Model

Some of these hold for every service, the rest are applied where the image runs
under them. [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md)
is the binding version; `scripts/ci/check-baseline.py` enforces the required
rules on every pull request.

| Rule | Scope | How |
|------|-------|-----|
| No privilege escalation | required | `no-new-privileges:true` on every service; each exception carries a written justification |
| Secrets isolated | required | Docker Secrets (`_FILE` or custom entrypoint), never in `environment:`; deviations documented per app |
| No direct socket access | required | Socket Proxy with granular API filtering |
| Network isolation | required | Databases and backends on internal networks, never published to the host |
| Read-only filesystem | where supported | `read_only: true` plus tmpfs for the paths the image writes |
| Minimal capabilities | where supported | `cap_drop: ALL`, with `cap_add` only for what the image needs |

Three patterns for secret handling:

| Scenario | Pattern |
|----------|---------|
| Image supports `_FILE` env vars | `POSTGRES_PASSWORD_FILE: /run/secrets/...` |
| Image doesn't support `_FILE` | Custom entrypoint reads secret at runtime |
| Secret embedded in JSON config | Env var in `.env` (gitignored) |

## Requirements

- **Docker** 24.0+ with Compose v2
- **Linux** host (tested on Debian 12/13)
- **`envsubst`** — package `gettext-base` on Debian/Ubuntu; Traefik's config is rendered from templates and `render.sh` stops without it
- **Domain** with a DNS provider supported by Traefik (e.g. Cloudflare)
- **Optional:** Tailscale for `acc-tailscale` access policies

## What's Included

`core/` and `apps/` are documented per service — the tables below are their
overview, and each row links to the stack that carries the full procedure.
`business/`, `monitoring/` and `backup/` additionally have a category README with
the choice guidance for that category.

### Core Infrastructure

| Service | Description |
|---------|-------------|
| [Traefik](core/traefik/) | Reverse proxy with Socket Proxy, 5 security levels, 3 TLS profiles, access policies |
| [Authentik](core/authentik/) | SSO / Identity Provider for centralized authentication (Forward-Auth, OAuth2 / OIDC / SAML) |
| [OnlyOffice](core/onlyoffice/) | Document editing server for Seafile, Nextcloud, etc. |
| [Euro-Office](core/euro-office/) | EU-governed OnlyOffice fork (Nextcloud/IONOS/XWiki/Proton) — drop-in document server |
| [Collabora](core/collabora/) | Lightweight LibreOffice-based office server (~1 GB) — leaner alternative to OnlyOffice/Euro-Office |
| [dnsmasq](core/dnsmasq/) | DNS forwarder with wildcard zones for Tailscale / split-DNS setups |
| [acme-certs](core/acme-certs/) | Certificate tool (acme.sh) for devices without Traefik (NAS, routers) |
| [CrowdSec](core/crowdsec/) | Intrusion detection engine + Traefik bouncer plugin — log analysis, threat decisions, L7 blocking |
| [Whoami](core/whoami/) | Traefik debug service to verify routing, TLS, and middlewares |
| [Dockhand](core/dockhand/) | Docker management with Git-based stacks |
| [Portainer](core/portainer/) | Docker management UI |
| [Hawser](core/hawser/) | Remote Docker agent for Dockhand |
| [Portainer Agent](core/portainer-agent/) | Remote Docker agent for Portainer (multi-host) |
| [Infisical](core/infisical/) | Central secret manager (self-hosted) — one place for all servers'/apps' secrets. VPN-only |

Planned in `core/`: Keycloak (alternative / heavier IAM next to Authentik).

### Applications

The blueprint takes a **choice-matrix** approach: where several tools compete (dashboards, photo galleries, wikis, form builders), multiple options are included so you can test and pick what fits.

What has been established about each stack — verified against which version and when, whether a restore was performed — is in [`LIFECYCLE.md`](LIFECYCLE.md), generated from the repository.

#### Dashboards & launchers

| App | Stack | Description |
|---|---|---|
| [Dashy](apps/dashy/) | Single container | Homelab dashboard, YAML-configured |
| [Heimdall](apps/heimdall/) | Single container (LSIO) | App-launcher with widget support |
| [Homarr](apps/homarr/) | Single container | Modern dashboard with rich integrations |
| [Homepage](apps/homepage/) | Single container | File-based YAML dashboard (gethomepage) |

#### Publishing & knowledge

| App | Stack | Description |
|---|---|---|
| [Ghost](apps/ghost/) | App + MySQL | Blog / CMS with SMTP + optional ActivityPub (Fediverse) |
| [WordPress](apps/wordpress/) | App + MariaDB | Classic CMS, hardened (mu-plugin + test-script) |
| [BookStack](apps/bookstack/) | App (LSIO) + MariaDB | Wiki / knowledge base (Laravel) |

#### Photo galleries

Five options — test and pick what fits your workflow.

| App | Stack | Description |
|---|---|---|
| [Immich](apps/immich/) | Server + ML + Postgres (pgvectors) + Valkey | AI-powered photo backup with mobile apps |
| [LibrePhotos](apps/librephotos/) | Nginx + Django+ML + React + pgautoupgrade | Google-Photos-like (OwnPhotos fork) |
| [Lychee](apps/lycheeorg/) | App (Laravel) + MariaDB + Redis | Clean, fast gallery |
| [PhotoPrism](apps/photoprism/) | App (Go+TensorFlow) + MariaDB | AI classification + WebDAV |
| [Photoview](apps/photoview/) | App (Go+GraphQL) + MariaDB | RAW processing + face recognition |

#### Scheduling & booking

Three 1:1-booking apps as a choice-matrix (pick one), plus a planned group-polling tool for a different axis.

| App | Stack | When to use |
|---|---|---|
| [Cal.diy](apps/caldiy/) | Next.js + Postgres + Redis | MIT community edition of Cal.com (community fork, personal use). |
| [Easy!Appointments](apps/easyappointments/) | PHP + MariaDB | Lightweight PHP alternative, established 2013, GPL-3.0. |

Planned: **Rallly** (group scheduling polls — Doodle alternative, complementary not competing with the 1:1 bookers above).

#### Productivity & personal

| App | Stack | Description |
|---|---|---|
| [Monica](apps/monicahq/) | App (Laravel) + MariaDB | Personal CRM for relationships |
| [NocoDB](apps/nocodb/) | Single container + SQLite | No-code database / spreadsheet UI (Airtable alternative) |
| [OpnForm](apps/opnform/) | API (Laravel) + UI (Nuxt) + Postgres + Redis | Self-hosted form builder (Typeform alternative) |
| [n8n](apps/n8n/) | Single container + SQLite | Visual workflow automation (Zapier alternative) |

> **Cloud-free data-collection chain:** `OpnForm → n8n → NocoDB` — forms collect, n8n transforms, NocoDB stores + presents. All three on `proxy-public`, addressable as `http://<app>-app:<port>` for internal calls.

#### File sync & documents

| App | Stack | Description |
|---|---|---|
| [Nextcloud](apps/nextcloud/) | App + MariaDB + Redis + Nginx + Cron | File sync, collaboration, optional OnlyOffice |
| [Paperless-ngx](apps/paperless-ngx/) | App + Postgres + Redis + Gotenberg + Tika | Document management with OCR, optional Authentik SSO |
| [Seafile](apps/seafile/) | App + MariaDB + Memcached + optional components | File sync & share (community edition) |
| [Seafile Pro](apps/seafile-pro/) | App + MariaDB + Memcached + SeaDoc + ClamAV + SeaSearch | File sync & share (pro edition) |

#### Identity & security

| App | Stack | Description |
|---|---|---|
| [Vaultwarden](apps/vaultwarden/) | App + MariaDB | Bitwarden-compatible password manager |

Planned (apps/): Headscale (self-hosted Tailscale control server), PrivateBin, SnapPass.

#### Networking

| App | Stack | Description |
|---|---|---|
| [UniFi Network App](apps/unifi/) | Controller (LSIO) + MongoDB 4.4 | Ubiquiti UniFi device controller |

#### Developer & admin tools

| App | Stack | Description |
|---|---|---|
| [Adminer](apps/adminer/) | Single container | Database administration UI (connects to other apps' DBs) |
| [IT-Tools](apps/it-tools/) | Single container | Collection of IT / developer utilities (JSON, hash, regex, etc.) |

Docker-management tools (Dockhand / Portainer / Hawser) moved to [`core/`](core/) — they're infrastructure, not apps.

Planned (apps/): Wiki.js, Outline, Formbricks, HeyForm, Shlink.

### Business apps

See [`business/README.md`](business/README.md) for the full category README + rollout phases.

| App | Function | Description |
|---|---|---|
| [OpenProject CE](business/openproject/) | Project management | Full PM — Gantt, kanban, work packages, time tracking. CE = local accounts only, no SSO. |
| [Vikunja](business/vikunja/) | Task management | Kanban, lists, Gantt — Trello / Planner alternative. Authentik OIDC verified, SSO-only. |
| [Invoice Ninja](business/invoiceninja/) | Billing | Invoicing, quotes, client portal. Credentials moved into Docker Secrets; not yet exercised on a host |
| [Dolibarr](business/dolibarr/) | ERP / CRM | Accounting, projects, HR, inventory |
| [Kimai](business/kimai/) | Time tracking | Per-project/customer hours → Invoice Ninja |
| [Listmonk](business/listmonk/) | Newsletter | Mailing list + transactional mail |
| [Matomo](business/matomo/) | Web analytics | GDPR-compliant, full-featured (Google Analytics alternative) |
| [Zammad](business/zammad/) | Helpdesk | Full 7-service helpdesk / ticketing / SLA |
| [OpenSign](business/opensign/) | E-signatures | DocuSign alternative, eIDAS-capable |
| [Documenso](business/documenso/) | E-signatures | DocuSign alternative (Remix + Postgres, local signing cert) |

Planned: Ackee, Plausible CE, Live Helper Chat, Eramba GRC.

### Monitoring

See [`monitoring/README.md`](monitoring/README.md) for the full category README.

| App | Axis | Description |
|---|---|---|
| [Uptime Kuma](monitoring/uptime-kuma/) | Uptime (UI) | Click-config uptime monitor, 90+ notification integrations |
| [Gatus](monitoring/gatus/) | Uptime (YAML) | Config-as-code health checks with Prometheus export |
| [Beszel](monitoring/beszel/) | Host metrics (hub) | Lightweight hub + local agent for CPU / RAM / disk / docker stats |
| [Beszel Agent](monitoring/beszel-agent/) | Host metrics (remote agent) | Standalone agent for additional hosts; pairs with Beszel hub |
| [changedetection.io](monitoring/changedetection/) | Content watcher | Page diff + notification (restock / price / ToS) |
| [Healthchecks](monitoring/healthchecks/) | Cron / scheduled-job | Dead-man's switch for backups / cron / scheduled tasks |
| [ntfy](monitoring/ntfy/) | Notification receiver | Self-hosted push to phone and desktop; belongs on a different host than the services above |

Planned: Statping, ciao, Checkmate, Zabbix, Grafana + Prometheus, Scrutiny, Gotify.

### Backup

Backup runs in two directions — this host outward, and your own devices inward. See [`backup/README.md`](backup/README.md) for the layer model, the host-agent rationale, and what append-only protection actually buys.

| Tool | Direction | Description |
|---|---|---|
| [Borgmatic](backup/borgmatic/) | This host → off-site | Deduplicated encrypted backup over SSH/SFTP, with native database dumps for PostgreSQL, MySQL, MariaDB, SQLite and MongoDB. Host-installed. Backup and restore both performed; the off-site target is written, not yet exercised. |
| [UrBackup](backup/urbackup/) | Your devices → this host | Client backup for Windows, macOS and Linux — keep laptop and desktop backups on hardware you own. Whole-disk image restore on Windows. |

Planned: Kopia, Bareos.

### Repository layout

Five top-level areas, each with a clear mandate. `business/`, `monitoring/` and `backup/` have a category README describing what belongs where and why; `core/` and `apps/` are documented per service in the tables above.

New here? Start with the area that best matches your goal: [Core Infrastructure](core/), [Apps](apps/), [Business](business/README.md), [Monitoring](monitoring/README.md), or [Backup](backup/README.md).

| Directory | Scope |
|---|---|
| [`core/`](core/) | Infrastructure shared by everything — Traefik, CrowdSec, identity providers (Authentik + Keycloak planned), OnlyOffice, certs |
| [`apps/`](apps/) | General-purpose self-hosted apps — equally useful for private homelab or a company |
| [`business/`](business/) | Apps that only make sense in a company context — invoicing, helpdesk, newsletter, compliance |
| [`monitoring/`](monitoring/) | Ops observability — uptime, metrics, content-change watching, disk SMART |
| [`backup/`](backup/) | Ops backup in both directions — this host outward (Borgmatic), your devices inward (UrBackup); structurally separate because of privileged access + remote targets |

## Project Structure

```text
secure-docker-blueprint/
│
├── core/                        # Infrastructure (always needed)
│   ├── traefik/                 #   Reverse proxy + socket proxy
│   ├── authentik/               #   SSO / Identity provider
│   ├── crowdsec/                #   Intrusion detection + Traefik bouncer
│   ├── onlyoffice/              #   Document editing server
│   ├── euro-office/             #   EU OnlyOffice fork (document server)
│   ├── collabora/               #   Lightweight office server (LibreOffice)
│   ├── dnsmasq/                 #   DNS forwarder / split-DNS
│   ├── acme-certs/              #   Certificate tool (acme.sh)
│   ├── whoami/                  #   Traefik debug service
│   ├── dockhand/                #   Docker management (Git-based stacks)
│   ├── hawser/                  #   Remote Docker agent for Dockhand
│   ├── portainer/               #   Docker management UI
│   ├── portainer-agent/         #   Remote Docker agent for Portainer
│   └── infisical/               #   Central secret manager (self-hosted)
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
│   ├── listmonk/  matomo/  zammad/  opensign/  documenso/
│   └── ...
│
├── monitoring/                  # Ops observability
│   ├── uptime-kuma/  gatus/  beszel/  changedetection/  healthchecks/  ntfy/
│   └── ...
│
├── backup/                      # Backup tooling
│   ├── borgmatic/               #   Server backup — host-installed, no compose stack
│   └── urbackup/                #   Client backup — Windows / macOS / Linux endpoints
│
├── docs/
│   ├── standards/               # Conventions and patterns
│   ├── bugfixes/                # Per-incident root-cause docs
│   └── audits/                  # Consistency & maintenance logs
│
└── scripts/
    └── overview.sh              # Dashboard of all running services
```

### Per-App Layout

Every app follows the same structure:

```text
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

## Dashboard

Quick overview of all configured services:

```bash
./scripts/overview.sh
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features, services under evaluation, and future ideas.

## Adding a New App

```bash
cp -r apps/_reference apps/my-new-app
cd apps/my-new-app
# Replace the stand-in images, drop what the app does not need
```

[`apps/_reference/`](apps/_reference/) is the canonical structure every app follows — a runnable stack, not a paper skeleton. Diff an existing app against it to find drift, or run `python3 scripts/ci/check-structure.py`. Full walkthrough: [docs/standards/new-app-checklist.md](docs/standards/new-app-checklist.md).

## Contributing

Contributions are welcome. Please follow the [conventions](docs/standards/) when adding new services or modifying existing ones.

## License

[Apache License 2.0](LICENSE)
