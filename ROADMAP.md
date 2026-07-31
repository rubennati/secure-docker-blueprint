# Roadmap

Direction reviewed 2026-07-31.

What remains to be built, what blocks it, and what proves it finished. Shipped
work belongs to [`CHANGELOG.md`](CHANGELOG.md), per-stack status to the tables in
[`README.md`](README.md) and the generated [`LIFECYCLE.md`](LIFECYCLE.md), and
per-category detail to the `README.md` in each top-level directory.

---

## Direction

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence. The single criterion for v1.0 is: **could someone fork this and run it without needing my mental model?** — subjective but unambiguous when met.

### v0.8.0 — Monitoring

Backup tells you what to do when something breaks. Monitoring tells you that something broke — and ideally before it causes data loss or downtime.

Six services are already in place, spanning the axes described in [`monitoring/README.md`](monitoring/README.md). The milestone is reached when each axis has **one verified service** — not when all six are verified, and not one axis per operator:

| Axis | In place | Verified for the milestone |
|---|---|---|
| Host & container metrics | Beszel + agent | Beszel |
| Uptime & endpoints | Uptime Kuma, Gatus | either one — they are a preference pair, not a hierarchy |
| Scheduled-job liveness | Healthchecks | Healthchecks — also the receiver for backup run monitoring |
| Content change | changedetection.io | changedetection.io |
| Disk health | *(Scrutiny planned)* | out of scope — needs physical-disk passthrough |
| **Alerting** | notification integrations in the services above, plus `monitoring/ntfy` as a receiver | at least one channel proven to actually arrive |

**Alerting is the cross-cutting layer, not a fifth service.** It is delivered by the services above rather than by a separate tool, and it is the one thing that turns a dashboard nobody watches into monitoring. A notification path that has never fired is worth as little as a backup that has never been restored.

Log aggregation (Loki/Grafana) stays out of scope — heavier infrastructure for a later pass.

**Blocked by** the same host the backup milestone ran on. Backup's proof layer
waits here too: borgmatic's run monitoring reports to Healthchecks or Uptime
Kuma, so those have to work before the timer is switched on.

### v0.9.0 — Measured resource limits

**Every service now carries a ceiling**, and the healthcheck question is decided
for every service — either one is defined or the compose file states why the image
cannot have one. `python3 scripts/ci/check-structure.py` is the progress bar for
both: it reports `no-resources` and `no-healthcheck` per service, and currently
reports neither.

**What remains is the values.** The ceilings in place were derived — from what a
component budgets for itself, from a peak where one was available, and generously
on purpose, because a limit the normal workload reaches kills an import and looks
like an application fault. Several stacks say so in the compose file: *starting
values, not measured ones*. Turning them into measured values needs a running
install per stack, which is why this milestone is late rather than early. The
procedure is in [`docs/resource-measurement.md`](docs/resource-measurement.md) —
what to sample, under which load states, and how a peak becomes a limit; the
profile table in [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md)
owns the target values.

**Done when** every `✅` stack's limits come from a measurement on a real install
rather than from the derivation rule.

**The Operator Site is live** at [secdockblue.rubennati.at](https://secdockblue.rubennati.at) since 2026-07-31, ahead of the milestone that used to hold it. It is the operator-facing entry point; the repository remains the technical source of truth and nothing moved out of it. Deliberately small and curated rather than a mirror of the repository, so it grows by review rather than by export.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this conversation.

Before v1.0 is tagged:

- Every app verified at least once on a clean install (continuous — not a last-minute sprint)
- No stack left at `scaffolded` without a documented reason
- No `__REPLACE_ME__` in any verified file
- Honest review of every `scaffolded` stack — a state rises only on evidence
- CI baseline complete: the jobs exist — compose validation, secret scan, security baseline, canonical structure, status model, checker coverage, docs QA (markdown lint, links, prose register) and workflow supply chain. Two gaps remain: **Trivy runs with `exit-code: 0`** and blocks nothing until the existing CRITICAL findings have been assessed once, and **`Checker coverage`, `Docs QA` and `Workflow supply chain` are not in the required set** — a branch-protection setting, not a file in this repository
- Secret & Password Generation Standard consolidated into `docs/standards/`
- Secrets rotation guidance in `docs/standards/`
- License review — every live app checked against the license policy below
- **Status freshness system active** — `Last verified` stamps in place, a major upstream update retires the verification anchor; tactical work moves to GitHub Issues
- Status model applied end to end — [`docs/standards/status-model.md`](docs/standards/status-model.md) defines what each symbol promises, [LIFECYCLE.md](LIFECYCLE.md) is generated from the owning files, and CI fails on a status claim that is not backed

---

## Continuous — not tied to a version

**App testing runs in parallel to everything above.** Any time there is bandwidth: pick a `scaffolded` app, run the App Chain, record the verified version. This does not block or trigger a release. The bar for the bar rises with the repository — an app verified today must meet the current baseline-aligned criteria in [`docs/maintenance.md`](docs/maintenance.md), not the bar from v0.1.

Apps still to re-verify on a clean install, because the standards have moved since
they were last checked: Vaultwarden, WordPress, Nextcloud, Seafile / Seafile Pro,
Invoice Ninja.

Pinned to a new major during the dependency sweep and not yet run anywhere:
Paperless-ngx 3.x, WordPress 7.x, Immich 3.x, Healthchecks 4.x, NocoDB (CalVer
switch), Adminer 5.x, Homepage 1.13.x, OpnForm 2.2.x, Uptime Kuma 2.x. Each is
`scaffolded` until it starts on a host — [`LIFECYCLE.md`](LIFECYCLE.md) carries the current
pin and status per stack.

**Cal.diY hardening** ([`apps/caldiy/docs/hardening-plan.md`](apps/caldiy/docs/hardening-plan.md))
runs on its own track, tied to no version. Phase 0 and Phase 1 configuration has
landed; the Phase 0 acceptance checks are open and Phases 2 and 3 have not started.

**Operator Site work is continuous and tied to no version** — content, structure and review loops are ongoing, and each push to `main` that touches `site/` publishes. What is written there is public the moment it lands, which is the reason for the content gate in front of it.

---

## In the backlog — individual app paths

App-level work that does not drive version tags.

### Choice-matrix categories — pick-one-per-install decisions

Once verified on real data, pick the default and deprioritise the rest:

- **Dashboards** — Dashy, Heimdall, Homarr, Homepage (`apps/`)
- **Photo galleries** — Immich, LibrePhotos, Lychee, PhotoPrism, Photoview (`apps/`)
- **Scheduling** — Cal.diy (MIT community), Easy!Appointments (`apps/`). Cal.com was retired — upstream moved the production codebase to a proprietary licence.
- **Business wikis** — BookStack is live; Wiki.js and Outline are planned (`apps/`)
- **Forms** — OpnForm is in place; Formbricks and HeyForm are planned (`apps/`)
- **Office / document servers** — OnlyOffice is live; Euro-Office (EU-governed fork) and Collabora (lighter, LibreOffice-based) are drafted (`core/`)
- **E-signatures** — OpenSign and Documenso, both drafted (`business/`)

### Categories with roadmaps in their own READMEs

Each of these owns its own planned list, including which services are on disk and
which are named only:

- [`monitoring/README.md`](monitoring/README.md) — the five monitoring axes plus the notification receiver; planned additions include Grafana + Prometheus and Scrutiny
- [`business/README.md`](business/README.md) — planned additions include Plane, Leantime, AppFlowy, Ackee, Plausible CE, Live Helper Chat and Eramba GRC
- [`backup/README.md`](backup/README.md) — Borgmatic has been backed up from and restored from; what remains there is the off-site target, which is written and not yet exercised, and UrBackup, which has never been started. Kopia and Bareos are named, not built

### Project management — to evaluate

Three candidates to assess before committing to a default recommendation:

| App | Angle | License | Notes |
|---|---|---|---|
| **Plane** | Jira alternative — issues, cycles, modules, analytics | AGPL-3.0 | Multi-service stack (web, worker, beat, minio); richer than Vikunja, lighter than OpenProject |
| **Leantime** | PM designed for non-project-managers — goals, tasks, time tracking | AGPL-3.0 | Single-container option available; different UX philosophy than the others |
| **AppFlowy** | Notion alternative — docs, databases, kanban, AI | AGPL-3.0 | ⚠️ Non-standard deployment: only the backend (AppFlowy Cloud) runs in Docker — users connect via desktop or mobile app, not a browser. Evaluate whether this fits the blueprint model before including. |

Evaluation criteria: self-hosted Docker complexity, SSO/OIDC support, `_FILE` secret support, active maintenance, CE feature set vs paid gating.

---

## Evaluating

### License policy

This blueprint is for personal self-hosted infrastructure. The following applies:

**Accepted for self-hosted personal use:**

- MIT, Apache 2.0, BSD — permissive, no conditions on use
- GPL-2.0 / GPL-3.0 — copyleft applies to distribution, not to running the software
- AGPL-3.0 — the most common license in this space (Nextcloud, Authentik, Vaultwarden, Zammad). Self-hosting for personal use is explicitly allowed. If you expose the service to others (even within a company), the AGPL requires that you make your modifications available — running unmodified upstream images means no obligation.
- BSL / Commercial Source — time-limited source-available licenses (e.g. MariaDB BSL). Generally fine for self-hosting; verify the "Change Date" and "Additional Use Grant" per project.

**Requires case-by-case review:**

- Commercial dual-license (e.g. Cal.com AGPL + commercial) — self-hosting is free under the AGPL tier; check if the feature set you need requires the commercial tier
- Source-available without redistribution rights — usable, but you cannot fork or modify

**Not included in this blueprint:**

- Proprietary closed-source images with no self-hosting rights

Every app documents its license in `UPSTREAM.md`. The baseline-aligned criteria require this field before a stack is recorded as as ready.

---

### App configuration tiering (concept — no fixed timeline)

Most apps currently have one level of configuration: "it runs." A tiered approach would give each app a clearly defined Minimum (smallest working set, no hidden required settings), an Advanced layer (performance, storage, integration options — commented out by default), and optionally an Expert layer (deep tuning, references upstream docs). Paperless-ngx Phase 4 is the first concrete example of what this looks like.

This is a concept to develop continuously — not a version milestone. Picked up app by app as they are re-verified.

### App Evaluation Criteria (concept — no fixed timeline)

Structured per-app metadata to help make informed decisions before deploying. Not a rating scale — factual criteria that each person weighs themselves. License and Origin are already covered in `UPSTREAM.md`. Remaining candidates:

- **Stack size**: number of containers, minimum RAM
- **Security features**: Docker Secrets / `_FILE` support, 2FA, SSO / OIDC integration, audit log
- **Active development**: release cadence, last commit, community size
- **Privacy posture**: what gets logged, telemetry / phone-home behaviour, GDPR posture

Still open: where this lives and how to keep it from becoming a maintenance burden.

### Deploy script

`./deploy.sh <server> core/traefik apps/nextcloud` — rsync selected app directories to a server, no git / docs / inbox on target. Portable app deployments without the full blueprint on each host.

### Alternative container runtimes

Long-term consideration beyond standard Docker — Podman, Docker Swarm, K3s. Not blocking v1.0.

### MCP connectors

Expose selected apps via Model Context Protocol for AI-assisted operation. Candidates: Paperless-ngx document search, Vaultwarden secret retrieval. Blueprint defines the pattern; individual MCP servers live in their own repos.

---

## Out of scope here

- `core/acme-certs/` — being extracted to its own repository. The blueprint stub remains `scaffolded` but is no longer actively maintained in this repo.
- Paperless-mcp — template exists in the Paperless CONFIG.md extension notes but will live in its own repo once built.
