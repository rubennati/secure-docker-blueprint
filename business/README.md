# Business Apps

Self-hosted business applications — invoicing, project management, helpdesk,
analytics, e-signature. See
[`docs/architecture.md`](../docs/architecture.md#directory-structure) for how this
category is defined relative to the other four.

## What's here

10 stacks, deployable now. What has been established about each — verified against
which version and when, whether a restore was performed — is in
[`LIFECYCLE.md`](../LIFECYCLE.md), generated from the repository.

### Project management & planning

| App | Use case | Notes |
|---|---|---|
| [OpenProject CE](openproject/) | Full PM — Gantt, kanban, work packages, time tracking, wikis | 6-service stack; Trello + Jira alternative. CE = local accounts only, no SSO. |
| [Vikunja](vikunja/) | Task management — kanban, lists, Gantt, table view | 2-service stack; Authentik OIDC, SSO-ready |

### Billing & operations

| App | Use case | Notes |
|---|---|---|
| [Invoice Ninja](invoiceninja/) | Invoicing, billing, quotes, client portal | Credentials moved into Docker Secrets; not yet exercised on a host |
| [Dolibarr](dolibarr/) | ERP / CRM — accounting, HR, inventory, projects | Migrated from `apps/dolibarr/` |
| [Kimai](kimai/) | Time tracking per project / customer | Integrates with Invoice Ninja via webhooks |

### Marketing & analytics

| App | Use case | Notes |
|---|---|---|
| [Listmonk](listmonk/) | Newsletter, mailing lists, transactional mail | Two-router pattern documented: admin VPN-only + subscriber paths public |
| [Matomo](matomo/) | GDPR-compliant web analytics for company / customer sites | Migrated from `apps/matomo/` — primary use-case is the business website |

### Customer support

| App | Use case | Notes |
|---|---|---|
| [Zammad](zammad/) | Full helpdesk / ticketing / SLA | 7-service stack, ≥ 4 GB RAM |

### Legal & compliance

| App | Use case | Notes |
|---|---|---|
| [OpenSign](opensign/) | E-signatures — DocuSign alternative | Mail via Mailgun or SMTP; eIDAS with qualified cert |
| [Documenso](documenso/) | E-signatures — DocuSign alternative | Remix + Postgres; local signing cert (.p12) |

## Planned

Not deployable here yet. See [`ROADMAP.md`](../ROADMAP.md) for status.

- **Plane** — project management
- **Leantime** — project management
- **AppFlowy** — Notion-style workspace
- **Ackee** — analytics
- **Plausible CE** — analytics
- **Live Helper Chat** — customer chat
- **Eramba GRC** — governance/risk/compliance

## The n8n hub

The `apps/n8n/` + `apps/nocodb/` + `apps/opnform/` cloud-free trio connects every business app via webhook:

- Form submitted → create Zammad ticket + append to Listmonk list
- Invoice paid → trigger OpenSign delivery confirmation
- Kimai weekly hours → email via Listmonk to project manager
- Matomo goal hit → NocoDB conversion row
- Uptime Kuma alert → Zammad ticket

## Layout

Each app subdirectory follows the blueprint structure:

```text
business/<app>/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── UPSTREAM.md
├── .secrets/        # gitignored
└── volumes/         # gitignored
```
