# Candidate evaluation — 2026-09-21

Fifteen products proposed for the blueprint, checked against what the repository
requires of a stack before one is written. Every line below was read from the
project's own repository, its published registry tags, or a container started
here; nothing is taken from the proposal text.

Three already ship: [`business/dolibarr`](../../business/dolibarr/),
[`apps/bookstack`](../../apps/bookstack/), [`business/kimai`](../../business/kimai/).
Twelve remain.

## What decides the verdict

| Requirement | Where it comes from |
|---|---|
| A published image with a version tag | `docs/standards/env-structure.md` — a bare major or `latest` fails `check-structure.py` |
| An independently operated service | The product criterion: a CLI or per-job container gets no entry |
| A deployment the project itself supports | Upstream's own compose or install documentation |
| Licence and origin stated | `scripts/ci/sovereignty-report.py --check` |

Maturity is recorded, not scored: stars, the date of the last push, and the date
of the newest stable release are facts a reader can weigh. Nothing here ranks one
product against another.

## Result

| Product | Stars | Last push | Licence | Image, pinnable tag | Tier |
|---|---|---|---|---|---|
| [calrs](https://github.com/olivierlambert/calrs) | 257 | 2026-09-20 | AGPL-3.0 | `ghcr.io/olivierlambert/calrs:1.17.1` | 1 |
| [Calnode](https://github.com/Calnode/calnode) | 90 | 2026-09-20 | Apache-2.0 | `ghcr.io/calnode/calnode:0.9.0` | 1 |
| [SolidInvoice](https://github.com/SolidInvoice/SolidInvoice) | 972 | 2026-09-20 | MIT | `solidinvoice/solidinvoice:3.0.1` | 1 |
| [FacturaScripts](https://github.com/NeoRazorX/facturascripts) | 493 | 2026-09-19 | LGPL-3.0 | `facturascripts/facturascripts:2026.65` | 1 |
| [Akaunting](https://github.com/akaunting/akaunting) | 10 130 | 2026-09-20 | Other (see below) | `akaunting/akaunting:3.1.21` | 1 |
| [ERPNext](https://github.com/frappe/erpnext) | 39 408 | 2026-09-21 | GPL-3.0 | `frappe/erpnext:v16.35.0` | 1 |
| [Twenty](https://github.com/twentyhq/twenty) | 57 178 | 2026-09-21 | Other (see below) | `twentycrm/twenty:v2.41.0` | 1 |
| [CISO Assistant](https://github.com/intuitem/ciso-assistant-community) | 4 436 | 2026-09-20 | Other (see below) | `ghcr.io/intuitem/ciso-assistant-community/{backend,frontend}:v4.0.5` | 1 |
| [DefectDojo](https://github.com/DefectDojo/django-DefectDojo) | 4 948 | 2026-09-21 | BSD-3-Clause | `defectdojo/defectdojo-django:3.3.100` | 1 |
| [Chatwoot](https://github.com/chatwoot/chatwoot) | 37 019 | 2026-09-19 | Other (see below) | `chatwoot/chatwoot:v4.18.0` | 1 |
| [obot](https://github.com/obot-platform/obot) | 1 031 | 2026-09-18 | MIT | `ghcr.io/obot-platform/obot:v0.25.6` | 1 |
| [DayOtter](https://github.com/Dayotter/dayotter) | 44 | 2026-09-21 | AGPL-3.0 | none published | 3 |
| [Dapta Calendars](https://github.com/Dapta-Tech/dapta-calendars-slate) | 1 | 2026-09-19 | MIT | none published | 3 |
| [MAILFLOW-AI](https://github.com/NeoNexAI/MAILFLOW-AI_MAILING) | 3 | 2026-06-13 | AGPL-3.0 | none published | 3 |
| [Crater](https://github.com/crater-invoice-inc/crater) | 8 350 | 2024-08-10 | AGPL-3.0 | none published | 3 |

**Tier 1** — a published, version-tagged image exists and the project documents a
container deployment. These can be written as stacks under the existing rules.

**Tier 3** — no published image. The project ships a Dockerfile and a compose file
that builds from source. See [What to do about the build-only products](#what-to-do-about-the-build-only-products).

There is no Tier 2: every candidate that publishes an image publishes a version
tag. The two that first looked `latest`-only do have one — the tag was under a
different name than the proposal gave.

## Stack shape, from each project's own compose

| Product | Services upstream ships | Datastores |
|---|---|---|
| calrs | 1 | SQLite in the data volume |
| Calnode | 1 | SQLite in the data volume |
| SolidInvoice | 2 | MySQL |
| Akaunting | 2 (image repository) | MySQL |
| FacturaScripts | 2 (image repository) | MySQL |
| Twenty | 4: server, worker, db, redis | PostgreSQL, Redis |
| Chatwoot | 5: rails, sidekiq, postgres, redis, base | PostgreSQL with pgvector, Redis |
| CISO Assistant | 6: backend, frontend, huey, mcp, qdrant, caddy | SQLite or PostgreSQL, Qdrant |
| DefectDojo | 7: uwsgi, nginx, celeryworker, celerybeat, initializer, postgres, valkey | PostgreSQL, Valkey |
| ERPNext | 7: backend, frontend, websocket, two queues, scheduler, configurator | MariaDB, Redis (external to the compose file) |
| obot | 1, plus an external PostgreSQL for production | PostgreSQL |

Upstream's compose is not always at the root of the product's repository:

- **ERPNext** ships none. The supported deployment is the separate
  [`frappe/frappe_docker`](https://github.com/frappe/frappe_docker) repository
  (2 571 stars, pushed 2026-09-19), whose `compose.yaml` plus `overrides/` is the
  real source.
- **Twenty** keeps it at `packages/twenty-docker/docker-compose.yml`.
- **Akaunting** and **FacturaScripts** keep it in their image repositories, not in
  the application repository.
- **Chatwoot** ships a separate `docker-compose.production.yaml`; the root
  `docker-compose.yaml` is for development.
- **DefectDojo**'s root compose is the supported production base, with overrides
  beside it.
- **CISO Assistant** ships `docker-compose.yml` plus a `config/` directory with
  variants, including a Traefik example.

## What needs attention, per product

These are facts to carry into the stack's `UPSTREAM.md`, not reasons to exclude.

**Licences that are not a single OSI identifier.** Four products split their
licence, so the sovereignty report will class them as mixed or source-available
rather than open source:

- **Twenty** — AGPL-3.0 with individually marked files under a commercial licence.
- **CISO Assistant** — AGPL for the community code; everything under `enterprise/`
  is under the vendor's commercial licence.
- **Chatwoot** — portions licensed separately from the base.
- **Akaunting** — its own licence file rather than a standard identifier.

Each needs its `- **License:**` line written from the licence file itself, and the
spelling may need adding to `SOURCE_AVAILABLE` in `scripts/ci/sovereignty-report.py`.

**Akaunting's image lags its source releases.** The newest source release is 3.2.4
(2026-09-17); the newest image tag is 3.1.21. Pinning the image means running a
release older than the repository's newest. That belongs in `UPSTREAM.md`.

**Two young scheduling projects.** calrs (257 stars, first-party single
maintainer) and Calnode (90 stars) are both under a year of public history. Both
were started here and behaved correctly under the full baseline, which is
evidence about the image, not about the project's longevity. The same judgement
that applies to `core/orion-belt` applies here: record the maturity and let the
reader weigh it.

**Products whose scope reaches past one host.** DefectDojo, CISO Assistant and
ERPNext are platforms with their own user and permission models, and ERPNext in
particular is an ERP whose deployment upstream treats as a multi-container
system with its own site management. Each is a larger commitment than a
single-purpose app, and ERPNext's `configurator` and site-creation step has no
equivalent anywhere else in this repository.

**Chatwoot and Twenty carry an AI or vector component.** Chatwoot's production
compose pins `pgvector/pgvector:pg16` rather than plain PostgreSQL. That is a
datastore choice to carry over, not an optional extra.

## What to do about the build-only products

Four products publish no image: **DayOtter**, **Dapta Calendars**, **MAILFLOW-AI**
and **Crater**. They cannot be written as ordinary stacks, because every stack in
this repository pins a published tag, and `scripts/ci/list-images.sh` feeds those
tags to the CVE scan. An image built on the operator's host has no tag to pin, no
digest anyone else can verify, and Trivy cannot pull it — the same gap already
recorded for the two stacks that build their own image.

The repository already has the standard for building rather than pulling —
[`docs/standards/custom-application.md`](../standards/custom-application.md) — and
two precedents: `business/vikunja` adds a layer to a published image, and
`apps/caldiy` consumes a reviewed release from a fork this project governs. Both
build from a source that is reviewed before it is built. Neither builds an
unreviewed third-party repository straight from its default branch, and that is
the difference that matters here.

**Proposal — three routes, by what the product actually offers:**

1. **Ask upstream to publish an image.** For DayOtter, whose deployment is
   otherwise complete: `deploy/docker-compose.prod.yml` exists, and the only
   missing piece is a published tag. An issue costs nothing and may remove the
   problem entirely.
2. **Evaluation entry, no stack.** Record the product in the category README's
   planned list with the reason it is not deployable here yet, and revisit when a
   tag appears. This is what `ROADMAP.md` already does for Suricata and Coraza.
3. **Fork and build, only where the product is worth governing.** This is the
   Cal.diY route, and it costs a review of the source, a build pipeline, an image
   identity this project controls, and ongoing maintenance of the fork. It is
   justified when the product is wanted and upstream will not publish — not
   because a stack is missing.

**Recommendation per product:**

| Product | Route | Why |
|---|---|---|
| DayOtter | 1, then 2 | 44 stars, active, complete production compose; only the published tag is missing |
| Dapta Calendars | 2 | v0.1.0, 1 star, pre-1.0 by its own statement |
| MAILFLOW-AI | 2 | 3 stars, no release at all, compose only under `infrastructure/` |
| Crater | 2 | Newest release 2022-03-06, last push 2024-08-10; the project has not moved in a year |

Route 3 is proposed for none of the four. Nothing here is in the position Cal.diY
was in, where the product was already deployed and the fork protected an
existing installation.

## What was verified by running it

Two products were started here, on the full baseline (`read_only`,
`cap_drop: ALL`, `no-new-privileges`, non-root, no published port), against a
throwaway data directory.

**calrs 1.17.1** — started and applied its migrations; `/healthz` answered 200.
The image already runs as uid 999. It carries no HTTP client, so a healthcheck
uses bash's `/dev/tcp`, which returned `HTTP/1.0 200 OK` against `/healthz`.
Its CLI creates the first administrator (`calrs user create --admin`) and closes
registration (`calrs config auth --registration false`); the password prompt needs
a terminal, so the bootstrap is interactive. After closing registration, a POST to
`/auth/register` created no user — the user list still held one. Login with the
correct password redirected (303) and the dashboard answered 200; a wrong password
re-rendered the form. Cross-site request forgery protection is on: the token comes
from a `__Host-` cookie and must be sent back as `_csrf`.

**Calnode 0.9.0** — started under the same settings forced to uid 1000; `/healthz`
returned `{"status":"ok"}` through the image's own `wget`. It is a single Go binary
with SQLite in `/data`. Production needs `CALNODE_ENCRYPTION_KEY`; the application
refuses to start without it once `BASE_URL` is `https`, and losing the key makes
stored credentials unrecoverable. Its first-run setup is `POST /v1/setup`, public
and once-only. Litestream is built into the entrypoint and restores the database if
the volume comes up empty.

Nothing else on the list was started. No stack files were written for any of them.

## Proposed order

Eleven Tier 1 products, in batches that share a category and a review:

| Batch | Products | Note |
|---|---|---|
| A | calrs, Calnode | Both already exercised; single container each |
| B | SolidInvoice, FacturaScripts, Akaunting | Invoicing, each two services |
| C | Twenty, Chatwoot | Business, four and five services |
| D | CISO Assistant, DefectDojo | Security operations, six and seven services |
| E | obot | AI, single container plus a database |
| F | ERPNext | Largest; deployment lives in a second repository |

Each batch stays a separate pull request under the existing rules: pinned images,
Docker Secrets, the security baseline, a `README.md` with a `## Backup` section, an
`UPSTREAM.md` with licence and origin, and a real functional test before the status
is claimed. Every stack lands `scaffolded` — none of them will have run behind
Traefik on a host.

This adds eleven stacks while `ROADMAP.md` holds applications until the open v1.0
items close. That is a deliberate exception, made to get the products in front of a
reviewer, and it does not change what v1.0 requires.
