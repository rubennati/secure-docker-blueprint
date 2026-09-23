# Apps

General-purpose self-hosted applications — equally useful to a private homelab and
to a company, including operator and diagnostic tooling. See
[`docs/architecture.md`](../docs/architecture.md#directory-structure) for how this
category is defined relative to the other four.

Where several tools solve the same problem — dashboards, photo galleries, office
servers — the blueprint ships more than one.

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
| [Wiki.js](wikijs/) | App (Node) + Postgres | Wiki with Markdown and visual editors, per-page permissions, about twenty authentication modules. The 2.5 line takes security fixes while 3.0 is in beta; the setup wizard is open until it has run once |
| [Shlink](shlink/) | Server + Postgres + optional web client | URL shortener on your own domain with visit statistics and a REST API. No accounts — API keys. Three routers: the redirects, `/rest`, and the browser interface |

### Photo galleries

Five options.

| App | Stack | Description |
|---|---|---|
| [Immich](immich/) | Server + ML + Postgres (pgvectors) + Valkey | AI-powered photo backup with mobile apps |
| [LibrePhotos](librephotos/) | Nginx + Django+ML + React + pgautoupgrade | Google-Photos-like (OwnPhotos fork) |
| [Lychee](lycheeorg/) | App (Laravel) + MariaDB + Redis | Clean, fast gallery |
| [PhotoPrism](photoprism/) | App (Go+TensorFlow) + MariaDB | AI classification + WebDAV |
| [Photoview](photoview/) | App (Go+GraphQL) + MariaDB | RAW processing + face recognition |

### Scheduling & booking

Five 1:1-booking apps.

| App | Stack | When to use |
|---|---|---|
| [Cal.diy](caldiy/) | Next.js + Postgres + Redis | MIT community edition of Cal.com (community fork, personal use). |
| [calnode](calnode/) | Single Go binary + SQLite | Booking pages, admin interface and a REST API in one container. The first-run setup route is public until it has run once; pre-1.0. |
| [calrs](calrs/) | Single Rust binary + SQLite | Availability read from a CalDAV server you already run. Registration is open until the first administrator exists. |
| [Easy!Appointments](easyappointments/) | PHP + MariaDB | Lightweight PHP alternative, established 2013, GPL-3.0. |
| [Tymeslot](tymeslot/) | Elixir/Phoenix + Postgres | Calendar sync with Google, Outlook, Apple and CalDAV, video links, reminder mail; AGPL-3.0, releases several times a week. |

Planned: **DayOtter** (scheduling platform, AGPL-3.0). It publishes no image, so it waits for upstream to publish one or for one built here — see [`../docs/audits/candidate-evaluation-2026-09-22.md`](../docs/audits/candidate-evaluation-2026-09-22.md#decided-on-2026-09-22).

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

Five different jobs, not five competing password managers — each holds a
different kind of secret, for a different length of time, for a different
audience. [`core/infisical`](../core/infisical/) is the fifth: it lives in
`core/` because it is installation-scoped infrastructure other stacks pull
machine credentials from, not a user-facing app, but it belongs in the same
mental map as the four below.

| App | Stack | Role |
|---|---|---|
| [Vaultwarden](vaultwarden/) | App + MariaDB | **Password management** — durable storage of human logins: website, username, password, TOTP, collections |
| [Yopass](yopass/) | App + Memcached | **Secret intake & ephemeral sharing** — a link that self-destructs, for handing someone a credential once |
| [Hemmelig](hemmelig/) | Single container | **Secret intake & ephemeral sharing** — the same job as Yopass, plus a built-in (if manual) secret-request flow |
| [PrivateBin](privatebin/) | Single container | **Secret intake & ephemeral sharing** — general zero-knowledge paste; passwords are one of many things it carries |
| [Infisical](../core/infisical/) | App + Postgres + Redis | **Infrastructure secrets** — API keys, DB credentials, CI/CD tokens, machine identities; lives in `core/` |

None of the three ephemeral-sharing apps replace Vaultwarden's job (nothing
here stores a login permanently) or Infisical's (nothing here is a machine
identity or a CI credential store), and Vaultwarden and Infisical do not do
theirs — see [Choosing between the secret-sharing apps](#choosing-between-the-secret-sharing-apps)
for what actually separates the three from each other.

Planned (apps/): Headscale (self-hosted Tailscale control server).

#### Choosing between the secret-sharing apps

Yopass, Hemmelig and PrivateBin solve overlapping but not identical problems.
Password Pusher is a known alternative in this space not shipped here — one
push mechanism does not need three implementations, and none of the three
above compete with each other closely enough yet to force that choice.

| | Yopass | Hemmelig | PrivateBin |
|---|---|---|---|
| Primary purpose | Ephemeral secret sharing | Ephemeral secret sharing + secret requests | Generic encrypted paste |
| Self-hosted | Yes | Yes | Yes |
| Free/open-source license | Yes — Apache-2.0 | **No** — O'Saasy License Agreement (MIT-derived; self-hosting unrestricted, reselling as a competing SaaS is not; not OSI-approved) | Yes — Zlib |
| Client-side encryption | Yes | Yes | Yes |
| Zero-knowledge | Yes | Yes | Yes |
| Send a secret (sender creates the link) | Yes | Yes | Yes |
| Request a secret (recipient-generated link) | **No** — paid Yopass Business feature only | Yes — built in, but the decryption key must be sent back to the requester manually (see its README) | No |
| External submitter needs an account | No | No (only the requester does, for the request flow) | No |
| Durable vault function | No | No | No |
| Machine-secret features | No | No | No |
| Notable restriction | Secret Requests requires a commercial license | License is not OSI-approved (self-hosting itself is unaffected); no new image published in ~6 months despite active source commits | None found |

No overall recommendation is made here on purpose — Yopass for a plain
disposable link with the simplest security story, Hemmelig if the
request-a-secret workflow matters enough to accept its license and manual
key hand-off, PrivateBin for anything that is not specifically a credential
(a config fragment, a recovery code, a note) or when license simplicity
matters most.

### Threat modeling

| App | Stack | Description |
|---|---|---|
| [OWASP Threat Dragon](threat-dragon/) | Single container | Data-flow diagrams, trust boundaries, threats and mitigations — stateless, models live in the browser or an optional connected Git repository |

Functionally unrelated to the secret-sharing apps above — it stores no
secrets and shares nothing between people.

### Security operations

Specialized security-operations tools — deception, supply-chain risk
tracking, vulnerability management, governance and compliance, incident
response, endpoint hunting. Each is a standard,
Traefik-or-direct-port app: no other stack in this repository depends on
them, which is why they sit here rather than in `core/`, alongside
[step-ca](../core/step-ca/) (PKI) and [zot](../core/zot/) (registry), the
two security-adjacent capabilities that *are* installation-scoped
infrastructure other stacks could route through. None of the entries below
are a SIEM, an XDR platform, or a SOC — see `ROADMAP.md`'s "Out of scope
here" for why that category stays out of this blueprint entirely.

| App | Stack | Description |
|---|---|---|
| [OpenCanary](opencanary/) | Single container | Deception/honeypot — fake FTP, Telnet, HTTP, MySQL, RDP services that log every connection attempt. Not an IDS, EDR or SIEM — see its README |
| [CISO Assistant](ciso-assistant/) | Backend + task worker + frontend + Postgres | Governance, risk and compliance — ISO 27001, NIS2, NIST CSF and 300+ further frameworks mapped to controls, risks and evidence. Administrator created at first start; the first start takes about ten minutes |
| [Dependency-Track](dependency-track/) | API + frontend + Postgres | Software Composition Analysis — SBOM ingestion, component and vulnerability tracking across a portfolio over time. Not a container/image scanner — see its README for the Trivy distinction |
| [DefectDojo](defectdojo/) | nginx + uWSGI + Celery worker and beat + initializer + Postgres + Valkey | Vulnerability management — imports scanner and pentest output, deduplicates findings, tracks them to closure. Upstream's public default keys replaced |
| [DFIR-IRIS](dfir-iris/) | App + worker + Postgres + RabbitMQ | Collaborative incident-response case management — cases, IOCs, evidence, timelines. Holds real incident data; read its Security model before deploying |
| [Velociraptor](velociraptor/) | Single container (server only) | Endpoint DFIR / threat hunting — VQL queries and collection across a fleet. An operative platform, not an always-on convenience app; losing its config breaks existing client trust — see its README |

### Document processing

| App | Stack | Description |
|---|---|---|
| [Docling Serve](docling-serve/) | Single container | Document understanding as an API — layout, structure, tables and Markdown/JSON export, aimed at RAG and other AI pipelines. `apps/paperless-gpt` can use it as its OCR backend |
| [paperless-gpt](paperless-gpt/) | Single container | Titles, tags, correspondents and OCR for Paperless-ngx through a language model — Ollama, any OpenAI-compatible endpoint, or Docling Serve for OCR. It has no authentication of its own, so its router carries an access policy and a basic-auth middleware |

Held: **paperless-ai** — its README states that the repository is not maintained, and
it is revisited once the announced rewrite is released. See
[`../docs/audits/candidate-evaluation-2026-09-22.md`](../docs/audits/candidate-evaluation-2026-09-22.md#decided-on-2026-09-22).

### Networking

| App | Stack | Description |
|---|---|---|
| [UniFi Network App](unifi/) | Controller (LSIO) + MongoDB 4.4 | Ubiquiti UniFi device controller |

### AI & local models

| App | Stack | Description |
|---|---|---|
| [Ollama](ollama/) | Single container | Local model runtime — pulls models by name, runs on CPU or an NVIDIA GPU, native and OpenAI-compatible API. **No authentication** — the route's access policy is the only gate |
| [Qdrant](qdrant/) | Single container | Vector database — collections, similarity search with payload filters, snapshots; API key required, REST and gRPC |
| [LiteLLM](litellm/) | Proxy + PostgreSQL | OpenAI-compatible gateway in front of any model backend — virtual keys with model allowlists and budgets, spend log. Master key for the operator, virtual keys for clients |
| [Open WebUI](open-webui/) | Single container | Chat interface with user accounts, history and document upload for any OpenAI-compatible endpoint. Administrator created at first start, self-signup off |
| [agentgateway](agentgateway/) | Single container | LLM and MCP gateway — API-key-protected `/v1` and `/mcp` on one port, web UI behind basic auth. Distroless, no healthcheck |
| [Dify](dify/) | 10 services | LLM application platform — chat and workflow apps, knowledge bases on pgvector, plugin-based model providers, sandboxed code nodes. Setup password guards the first account; agent runtime and `/e/` webhooks not carried |
| [vLLM](vllm/) | Single container | High-throughput OpenAI-compatible model serving on an NVIDIA GPU. `--api-key` covers `/v1` only, so the route forwards `/v1/` and nothing else. CUDA image not yet run on a GPU |

Planned: **obot** (MCP gateway and agent platform). It runs the MCP servers it
hosts as containers and does not start without the Docker API; creating those
containers takes write access, which is root-equivalent on the host, so its stack
will carry that access as a documented deviation. See
[`../docs/audits/candidate-evaluation-2026-09-22.md`](../docs/audits/candidate-evaluation-2026-09-22.md#decided-on-2026-09-22).

### Developer & admin tools

| App | Stack | Description |
|---|---|---|
| [Adminer](adminer/) | Single container | Database administration UI (connects to other apps' DBs) |
| [IT-Tools](it-tools/) | Single container | Collection of IT / developer utilities (JSON, hash, regex, etc.) |
| [GreenMail](greenmail/) | Single container | SMTP, IMAP and POP3 test server with a real mailbox per recipient — for automated tests that log in and assert on what arrived |
| [Mailpit](mailpit/) | Single container | SMTP sink for trying out the stacks that send mail — accepts every message, shows it, delivers nothing |
| [Whoami](whoami/) | Single container | Traefik debug service to verify routing, TLS and middlewares — deploy temporarily, then disable |
| [Windmill](windmill/) | Server + 2 workers + PostgreSQL 18 | Code-first scripts, flows, APIs and scheduled jobs on a Postgres-backed queue. Replace the built-in administrator before exposing it |
| [httpbin](httpbin/) | Single container | HTTP request and response service for testing clients — echoes, status codes, redirects, delays. The Python Software Foundation's fork; start command replaced because the image's own fails in 0.10.4 |

Docker-management tools (Dockhand / Portainer / Hawser) are in [`core/`](../core/): they control Docker itself, which is an installation-scoped capability. Whoami sits here instead — it is a routed diagnostic that serves no other stack.

Planned (apps/): HeyForm.

## Related

- [`core/`](../core/) — shared platform and control plane
- [`business/`](../business/) — invoicing, project management, helpdesk, analytics, e-signature
- [`docs/architecture.md`](../docs/architecture.md) — why the categories are what
  they are, and the networking model every stack here follows
