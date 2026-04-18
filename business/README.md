# Business Apps

Self-hosted toolchain for running a company end-to-end: communication, legal, operations, identity, knowledge, backup. Designed as a **Profi-Level self-hosted alternative** to the typical SaaS stack (Mailchimp + Zendesk + Intercom + Harvest + DocuSign + Confluence + Typeform + Bitly + Okta + Tailscale + …).

The apps split cleanly by business function. Pick what you need — nothing couples tightly, everything composes via Traefik + shared networks + webhook-based integration (n8n in the middle for routing).

## Status

✅ live-tested · ⚠️ draft · 📋 planned

### 📧 Marketing & outreach

| App | Use case | Status |
|---|---|---|
| [Listmonk](listmonk/) | Newsletter, mailing list, transactional mail | ⚠️ |

### 🎫 Customer support

| App | Use case | Status | Notes |
|---|---|---|---|
| [Zammad](zammad/) | Full helpdesk / ticketing / SLA | ⚠️ | 7-service stack, ~4 GB RAM minimum |
| Live Helper Chat | Website live-chat widget | 📋 | PHP, lighter, real-time visitor chat |

### ⏱️ Operations & billing

| App | Use case | Status | Notes |
|---|---|---|---|
| [Kimai](kimai/) | Time tracking per project/customer | ⚠️ | Integrates with Invoice Ninja via API/export |

### ✍️ Legal & compliance

| App | Use case | Status | Notes |
|---|---|---|---|
| [OpenSign](opensign/) | E-signatures — DocuSign alternative | ⚠️ | eIDAS-compatible with a qualified cert |
| Eramba GRC | Governance / Risk / Compliance (NIS2, DSGVO, ISO-27001 mapping) | 📋 | Heavy. For regulated businesses. |

### 📚 Knowledge & collaboration

Two wiki alternatives (beyond the already-drafted [BookStack](../apps/bookstack/)):

| App | Use case | Status | Notes |
|---|---|---|---|
| Wiki.js | Feature-rich wiki, Node.js, many auth backends | 📋 | Heavier than BookStack, more flexible |
| Outline | Modern, Notion-like wiki | 📋 | React/Node, prettier UI, Slack integration |

### 📝 Forms & surveys

Two more alternatives beyond the already-drafted [OpnForm](../apps/opnform/):

| App | Use case | Status | Notes |
|---|---|---|---|
| Formbricks | Qualtrics-style surveys — in-product, NPS, research | 📋 | Next.js, event-driven, embeddable |
| HeyForm | Typeform-style form builder, richer than OpnForm | 📋 | Alternative to OpnForm, more designs |

### 🔗 Utilities

| App | Use case | Status | Notes |
|---|---|---|---|
| Shlink | Branded URL shortener (`go.firma.at/xy`) with stats | 📋 | REST API, QR codes, geolocation |
| PrivateBin | Encrypted paste service — send secrets one-time | 📋 | Zero-knowledge, client-side AES |
| SnapPass | One-time secret sharing (password reset links for users) | 📋 | Redis-backed, expiring links |

### 💾 Backup

Three approaches, pick one per workload:

| App | Use case | Status | Notes |
|---|---|---|---|
| Kopia | Deduplicating snapshots to S3 / SFTP / local | 📋 | Modern, fast. Desktop UI + server mode. |
| Bareos | Enterprise Bacula-fork with director/storage/file daemons | 📋 | Heavy. For regulated backup policies. |
| UrBackup | Windows/Linux image + file backup with web UI | 📋 | Good for workstations + servers. |

### 🔐 Identity & network

| App | Use case | Status | Notes |
|---|---|---|---|
| Keycloak | Full IAM (realms, clients, roles, federated identity) | 📋 | Heavy. Use if you outgrow Authentik. |
| Headscale | Self-hosted Tailscale control server | 📋 | Kicks the Tailscale SaaS dependency. Network-critical. |

## Recommended rollout sequence

For someone building out a fresh company stack on this blueprint:

### Phase 1 — Foundation (already live)

Traefik + Vaultwarden + Nextcloud/Seafile + Paperless-ngx. That's the baseline: reverse proxy, password manager, file sync, documents.

### Phase 2 — Customer-facing (draft now, implement when ready)

1. **Listmonk** — if you have a list
2. **Zammad** — if you have customer support requests
3. **OpenSign** — when the first contract needs to be signed digitally
4. **Kimai** — track hours from day 1 of first billable project

All 4 are in this category as drafts.

### Phase 3 — Scaling & operations

- **Shlink** (branded links for marketing + trackability)
- **Formbricks** or **HeyForm** (pick one to complement OpnForm or replace it)
- **Wiki.js** or **Outline** (pick one — if BookStack's Laravel-stack doesn't fit)
- **SnapPass** (sharing initial creds with new hires)

### Phase 4 — Scale + compliance

- **Keycloak** (when you have too many apps for Authentik's admin model)
- **Eramba GRC** (when a formal audit looms: NIS2, ISO-27001)
- **Headscale** (when the Tailscale SaaS bill bothers you)

### Phase 5 — Specialised

- **Kopia / Bareos / UrBackup** — backup strategy depends on your workload mix
- **Live Helper Chat** — if live website chat becomes a thing

## The n8n hub

Most of these integrate loosely via webhook → n8n → target API. Build your business process automations in n8n:

- Form submitted → create Zammad ticket + append to Listmonk list + Slack/Mattermost notification
- New invoice in Invoice Ninja → generate OpenSign signing request for delivery confirmation
- Kimai weekly summary → email via Listmonk to project manager
- Uptime Kuma alert → Zammad ticket auto-created with severity

The [apps/n8n/](../apps/n8n/), [apps/nocodb/](../apps/nocodb/), and [apps/opnform/](../apps/opnform/) cloud-free trio is already in place — every business app in this category plugs in via its webhook channel.

## Layout

Each app subdirectory follows the blueprint structure:

```
business/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── .secrets/           # gitignored, created at setup
└── volumes/            # gitignored, created at setup
```
