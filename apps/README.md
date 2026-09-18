# Apps

General-purpose self-hosted applications — equally useful to a private homelab and
to a company. This is the "everything else" category: a stack lands here when it
serves its own users rather than the installation.

That includes operator and diagnostic tooling. A service is not infrastructure
because an operator rather than an end user opens it, and it is not infrastructure
because it is short-lived — see [Developer & admin tools](#developer--admin-tools).

Where several tools compete — dashboards, photo galleries, wikis, form builders —
the blueprint ships more than one. What separates them is on the operator site:
[Choosing between services](https://secdockblue.rubennati.at/applications/choosing/).

## What's here

What has been established about each stack — verified against which version and
when, whether a restore was performed — is in [`LIFECYCLE.md`](../LIFECYCLE.md),
generated from the repository.

[`_reference/`](_reference/) is not a deployable service: it is the canonical
structure every stack in this repository follows.

### Dashboards & launchers

| App | Stack | Description |
|---|---|---|
| [Dashy](dashy/) | Single container | Homelab dashboard, YAML-configured |
| [Heimdall](heimdall/) | Single container (LSIO) | App-launcher with widget support |
| [Homarr](homarr/) | Single container | Modern dashboard with rich integrations |
| [Homepage](homepage/) | Single container | File-based YAML dashboard (gethomepage) |

### Publishing & knowledge

| App | Stack | Description |
|---|---|---|
| [Ghost](ghost/) | App + MySQL | Blog / CMS with SMTP + optional ActivityPub (Fediverse) |
| [WordPress](wordpress/) | App + MariaDB | Classic CMS, hardened (mu-plugin + test-script) |
| [BookStack](bookstack/) | App (LSIO) + MariaDB | Wiki / knowledge base (Laravel) |

### Photo galleries

Five options — test and pick what fits your workflow.

| App | Stack | Description |
|---|---|---|
| [Immich](immich/) | Server + ML + Postgres (pgvectors) + Valkey | AI-powered photo backup with mobile apps |
| [LibrePhotos](librephotos/) | Nginx + Django+ML + React + pgautoupgrade | Google-Photos-like (OwnPhotos fork) |
| [Lychee](lycheeorg/) | App (Laravel) + MariaDB + Redis | Clean, fast gallery |
| [PhotoPrism](photoprism/) | App (Go+TensorFlow) + MariaDB | AI classification + WebDAV |
| [Photoview](photoview/) | App (Go+GraphQL) + MariaDB | RAW processing + face recognition |

### Scheduling & booking

Three 1:1-booking apps as a choice-matrix (pick one), plus a planned group-polling tool for a different axis.

| App | Stack | When to use |
|---|---|---|
| [Cal.diy](caldiy/) | Next.js + Postgres + Redis | MIT community edition of Cal.com (community fork, personal use). |
| [Easy!Appointments](easyappointments/) | PHP + MariaDB | Lightweight PHP alternative, established 2013, GPL-3.0. |
| [Tymeslot](tymeslot/) | Elixir/Phoenix + Postgres | Calendar sync with Google, Outlook, Apple and CalDAV, video links, reminder mail; AGPL-3.0, releases several times a week. |

Planned: **Rallly** (group scheduling polls — Doodle alternative, complementary not competing with the 1:1 bookers above).

### Productivity & personal

| App | Stack | Description |
|---|---|---|
| [Monica](monicahq/) | App (Laravel) + MariaDB | Personal CRM for relationships |
| [NocoDB](nocodb/) | Single container + SQLite | No-code database / spreadsheet UI (Airtable alternative) |
| [OpnForm](opnform/) | API (Laravel) + UI (Nuxt) + Postgres + Redis | Self-hosted form builder (Typeform alternative) |
| [n8n](n8n/) | Single container + SQLite | Visual workflow automation (Zapier alternative) |

> **Cloud-free data-collection chain:** `OpnForm → n8n → NocoDB` — forms collect, n8n transforms, NocoDB stores + presents. All three on `proxy-public`, addressable as `http://<app>-app:<port>` for internal calls.

### File sync & documents

| App | Stack | Description |
|---|---|---|
| [Nextcloud](nextcloud/) | App + MariaDB + Redis + Nginx + Cron | File sync, collaboration, optional OnlyOffice |
| [Paperless-ngx](paperless-ngx/) | App + Postgres + Redis + Gotenberg + Tika | Document management with OCR, optional Authentik SSO |
| [Seafile](seafile/) | App + MariaDB + Memcached + optional components | File sync & share (community edition) |
| [Seafile Pro](seafile-pro/) | App + MariaDB + Memcached + SeaDoc + ClamAV + SeaSearch | File sync & share (pro edition) |
| [OnlyOffice](onlyoffice/) | Single container | Document editing server for Seafile, Nextcloud, etc. |
| [Euro-Office](euro-office/) | Single container | EU-governed OnlyOffice fork (Nextcloud/IONOS/XWiki/Proton) — drop-in document server |
| [Collabora](collabora/) | Single container | Lightweight LibreOffice-based office server (~1 GB) |

### Identity & security

| App | Stack | Description |
|---|---|---|
| [Vaultwarden](vaultwarden/) | App + MariaDB | Bitwarden-compatible password manager |

Planned (apps/): Headscale (self-hosted Tailscale control server), PrivateBin, SnapPass.

### Networking

| App | Stack | Description |
|---|---|---|
| [UniFi Network App](unifi/) | Controller (LSIO) + MongoDB 4.4 | Ubiquiti UniFi device controller |

### Developer & admin tools

| App | Stack | Description |
|---|---|---|
| [Adminer](adminer/) | Single container | Database administration UI (connects to other apps' DBs) |
| [IT-Tools](it-tools/) | Single container | Collection of IT / developer utilities (JSON, hash, regex, etc.) |
| [Mailpit](mailpit/) | Single container | SMTP sink for trying out the stacks that send mail — accepts every message, shows it, delivers nothing |
| [Whoami](whoami/) | Single container | Traefik debug service to verify routing, TLS and middlewares — deploy temporarily, then disable |

Docker-management tools (Dockhand / Portainer / Hawser) are in [`core/`](../core/): they control Docker itself, which is an installation-scoped capability. Whoami sits here instead — it is a routed diagnostic that serves no other stack.

Planned (apps/): Wiki.js, Outline, Formbricks, HeyForm, Shlink.

## Related

- [`core/`](../core/) — shared platform and control plane
- [`business/`](../business/) — applications that need a company to be useful
- [`docs/architecture.md`](../docs/architecture.md) — why the categories are what
  they are, and the networking model every stack here follows
