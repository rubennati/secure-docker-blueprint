# Business Apps

Self-hosted apps **that only make sense in a business / company context**. The criterion: *do you need to run a business to meaningfully use this?* If yes → here. If the app is equally useful to a private homelab user (wiki, password manager, URL shortener, …) it belongs in [`apps/`](../apps/).

This keeps `business/` a meaningful category instead of a grab-bag. See [`docs/architecture/directory-layout.md`](../docs/architecture/directory-layout.md) (on the `docs` branch) for the full categorisation rule.

## Status

✅ Ready · 🚧 Draft · 📋 Planned

### Project management & planning

| App | Use case | Status | Notes |
|---|---|---|---|
| [OpenProject CE](openproject/) | Full PM — Gantt, kanban, work packages, time tracking, wikis | ✅ | 6-service stack; Trello + Jira alternative. CE = local accounts only, no SSO. |
| [Vikunja](vikunja/) | Task management — kanban, lists, Gantt, table view | ✅ | 2-service stack; Authentik OIDC, SSO-ready |
| Plane | Project management — issues, cycles, modules, analytics | 📋 | Jira alternative; AGPL-3.0; multi-service stack |
| Leantime | PM for non-project-managers — goals, tasks, time tracking | 📋 | AGPL-3.0; all-in-one single container option available |
| AppFlowy | Notion alternative — docs, databases, kanban, AI | 📋 | AGPL-3.0; could also live in apps/ (not business-exclusive) |

### Billing & operations

| App | Use case | Status | Notes |
|---|---|---|---|
| [Invoice Ninja](invoiceninja/) | Invoicing, billing, quotes, client portal | ✅ | |
| [Dolibarr](dolibarr/) | ERP / CRM — accounting, HR, inventory, projects | 🚧 | Migrated from `apps/dolibarr/` |
| [Kimai](kimai/) | Time tracking per project / customer | 🚧 | Integrates with Invoice Ninja via webhooks |

### Marketing & analytics

| App | Use case | Status | Notes |
|---|---|---|---|
| [Listmonk](listmonk/) | Newsletter, mailing lists, transactional mail | 🚧 | Two-router pattern documented: admin VPN-only + subscriber paths public |
| [Matomo](matomo/) | GDPR-compliant web analytics for company / customer sites | 🚧 | Migrated from `apps/matomo/` — primary use-case is the business website |
| Ackee | Privacy-focused analytics — no cookies, GDPR by design | 📋 | Minimal alternative to Matomo; no files yet |
| Plausible CE | Privacy-first analytics — clean UI, no cookie banner | 📋 | Middle ground between Matomo (heavy) and Ackee (minimal); AGPL-3.0 |

### Customer support

| App | Use case | Status | Notes |
|---|---|---|---|
| [Zammad](zammad/) | Full helpdesk / ticketing / SLA | 🚧 | 7-service stack, ≥ 4 GB RAM |
| Live Helper Chat | Real-time visitor chat on company website | 📋 | PHP, lighter than Zammad, for pre-sales chat |

### Legal & compliance

| App | Use case | Status | Notes |
|---|---|---|---|
| [OpenSign](opensign/) | E-signatures — DocuSign alternative | 🚧 | Mail via Mailgun or SMTP; eIDAS with qualified cert |
| Eramba GRC | Governance / Risk / Compliance mapping (NIS2, DSGVO, ISO-27001) | 📋 | Heavy. For regulated businesses. |

## Why these and not others

Applying the criterion consistently, the following were **deliberately kept in `apps/`** because private homelab users have the same use-case:

- **NocoDB, n8n, Vaultwarden, Cal.com, Monica, BookStack** — general productivity, equally useful private
- **Wiki.js, Outline, Formbricks, HeyForm, Shlink, PrivateBin, SnapPass, Headscale** — general utilities / knowledge / identity; not business-exclusive

And the following moved to other top-level categories:

- **Healthchecks** → [`monitoring/`](../monitoring/) (ops observability, not business)
- **Keycloak** → [`core/`](../core/) (alongside Authentik — both are IAM infrastructure)
- **Kopia, Bareos, UrBackup** → [`backup/`](../backup/) (ops, not business)

## Rollout sequence

For someone building out a fresh company stack:

### Phase 1 — Foundation (core/ + apps/)

Traefik, Vaultwarden, Nextcloud/Seafile, Paperless-ngx already in place.

### Phase 2 — Billing + customer-facing (this category)

1. **Invoice Ninja** — day-one of first billable project
2. **Kimai** — track hours from the start (→ Invoice Ninja via n8n)
3. **Zammad** — when customer-support requests start coming in
4. **Listmonk** — when you have a list
5. **OpenSign** — when the first contract needs digital signing

All 5 are available here.

### Phase 3 — Analytics + extras

- **Matomo** — replace Google Analytics on the company website
- **Live Helper Chat** — if website live-chat becomes a thing
- **Eramba GRC** — if NIS2 / ISO-27001 looms

## The n8n hub

The `apps/n8n/` + `apps/nocodb/` + `apps/opnform/` cloud-free trio connects every business app via webhook:

- Form submitted → create Zammad ticket + append to Listmonk list
- Invoice paid → trigger OpenSign delivery confirmation
- Kimai weekly hours → email via Listmonk to project manager
- Matomo goal hit → NocoDB conversion row
- Uptime Kuma alert → Zammad ticket

## Layout

Each app subdirectory follows the blueprint structure:

```
business/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── UPSTREAM.md
├── .secrets/        # gitignored
└── volumes/         # gitignored
```
