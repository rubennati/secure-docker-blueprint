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
| [Akaunting](akaunting/) | Accounting — invoices, bills, bank accounts, reports | Business Source License: production use free up to two users, one company or one thousand invoices. Image lags the source by one minor release |
| [Invoice Ninja](invoiceninja/) | Invoicing, billing, quotes, client portal | Credentials moved into Docker Secrets; not yet exercised on a host |
| [Dolibarr](dolibarr/) | ERP / CRM — accounting, HR, inventory, projects | Migrated from `apps/dolibarr/` |
| [Kimai](kimai/) | Time tracking per project / customer | Integrates with Invoice Ninja via webhooks |
| [SolidInvoice](solidinvoice/) | Invoicing — clients, quotes, recurring invoices, payments | One container with SQLite. **Setup not verified**: the web installer was not completed, and the command-line installer does not finish in 3.0.1 |

### Marketing & analytics

| App | Use case | Notes |
|---|---|---|
| [Listmonk](listmonk/) | Newsletter, mailing lists, transactional mail | Two-router pattern documented: admin VPN-only + subscriber paths public |
| [Matomo](matomo/) | GDPR-compliant web analytics for company / customer sites | Migrated from `apps/matomo/` — primary use-case is the business website |

### Customer relationships

| App | Use case | Notes |
|---|---|---|
| [Twenty](twenty/) | CRM — companies, people, opportunities, tasks, with an extensible data model and API | Server + worker + PostgreSQL + Redis. The first account creates the workspace; further sign-ups need an invitation |

### Customer support

| App | Use case | Notes |
|---|---|---|
| [Chatwoot](chatwoot/) | Shared inbox for website chat, email and messaging channels | Rails + Sidekiq + PostgreSQL (pgvector) + Redis. The first visit creates the administrator; public sign-up off |
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
- **FacturaScripts** — invoicing and accounting. Evaluated 2026-09-21 and held: its
  supported deployment mounts the whole webroot as a volume and copies the code in
  on the first start only, so a pinned image tag describes the first install and
  nothing after it; updates run through the application's own updater. See
  [`../docs/audits/candidate-evaluation-2026-09-21.md`](../docs/audits/candidate-evaluation-2026-09-21.md).

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
