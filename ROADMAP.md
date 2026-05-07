# Roadmap

Last updated: 2026-05-03 (v0.5.1 shipped).

This document captures direction, not detailed changelogs. For shipped work see [`CHANGELOG.md`](CHANGELOG.md); for per-category details see the `README.md` in each top-level directory.

---

## Shipped

### v0.5.0 — Authentik Forward-Auth pattern proven (2026-05-03)

Dashy and Paperless-ngx `/admin` behind Authentik Forward-Auth, live-tested
end-to-end. Two reusable patterns documented: Pattern 1 (full app) and
Pattern 2 (path-scoped). SPA rate-limit fix via `rl-spa` / `sec-3-spa`.
Three bugs fixed along the way (router priority, Pattern 2 External host,
SPA 429). Heimdall wired up code-side (opt-in comment).

### v0.4.0 — CrowdSec Bouncer Plugin live (2026-04-20)

Phase 2 activation proven end-to-end: the Traefik bouncer plugin now enforces CrowdSec decisions at the proxy. Two first-setup bugs fixed along the way (read-only FS blocking plugin storage, AppSec fail-closed default).

### v0.3.0 — Core complete (2026-04-20)

Every core service validated on a fresh install; both multi-host management paths proven end-to-end (Dockhand + Hawser / Portainer + Portainer Agent). Certificate strategy documented. Two shipped bug fixes (Traefik dynamic config load, Portainer healthcheck).

### v0.2.0 — Structure Stable Baseline (2026-04-18)

Top-level layout locked in with five categories (`core/`, `apps/`, `business/`, `monitoring/`, `backup/`). Per-category READMEs document scope and roadmap. Forks can rely on the directory layout going forward.

### v0.1.0 — Initial public release (2026-04-16)

Core infrastructure (Traefik, CrowdSec, Authentik, OnlyOffice) plus 10 hardened app deployments. Standards documentation (`docs/standards/`) and Apache 2.0 license.

See [`CHANGELOG.md`](CHANGELOG.md) for the full diff of each release.

---

## Direction

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence. The single criterion for v1.0 is: **could someone fork this and run it without needing my mental model?** — subjective but unambiguous when met.

### v0.6.0 — CrowdSec complete

Full CrowdSec stack in one version — host-level blocking and operational control:

- **nftables Bouncer** — drops packets before they reach Traefik (OS-level, complements the L7 bouncer from v0.4.0)
- **Dashboard** — see what is being blocked in real time
- **Runbook** — how to check decision lists, whitelist your own IP, drain false positives, disable quickly if needed
- **Geoblocking** — structured setup with documented trade-offs
- **AppSec tuning** — review default rules, document any false-positive patterns specific to this stack

Goal: after this version, CrowdSec is a tool you can confidently operate at every layer, not just something that runs in the background.

### v0.7.0 — Backup

A working infrastructure is worthless without recovery. Three layers:

- **Host backup** — Borgmatic with 3-2-1 strategy (local + remote targets), documented restore procedure
- **App data backup** — volume-level snapshots for stateful apps
- **Database backup** — per-app DB dump strategy (PostgreSQL, MariaDB, SQLite)

Each layer gets a blueprint pattern that works across apps, not per-app one-offs.

**Restore testing is part of this version** — a backup that has never been restored is a hypothesis, not a backup. At least one full restore walkthrough per layer, documented step by step.

### v0.8.0 — Monitoring

Backup tells you what to do when something breaks. Monitoring tells you that something broke — and ideally before it causes data loss or downtime. Four layers:

- **Host** — CPU, RAM, disk, network trends over time. Beszel is the default: lightweight, self-hosted, no external dependencies. Know when a disk is filling up before it becomes an incident.
- **Container / Docker** — which containers are running, which have restarted, resource usage per service. Beszel covers this alongside host metrics.
- **Uptime & endpoints** — is the service actually responding correctly from the outside? Gatus or Uptime Kuma with per-app health checks and status page.
- **Alerting** — push or email notification when a service goes down or a threshold is crossed. Without this, monitoring is a dashboard nobody watches.

Each layer gets a proven setup in the blueprint. Log aggregation (Loki/Grafana stack) is out of scope here — heavier infrastructure that fits a later pass.

### v0.9.0 — Resource limits

Every live app gets `deploy.resources` (memory + CPU) and `pids_limit`. The standard is already documented in [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md); this version applies it.

Intentionally late: wrong limits break apps silently (OOM kills, throttled CPUs). Each app needs values measured on a real install, not guessed. This is the fine-tuning pass — not a quick sweep.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this conversation.

Before v1.0 is tagged:

- Every app at least once sober-tested on a clean install (continuous — not a last-minute sprint)
- No `🚧` without a documented reason
- No `__REPLACE_ME__` in any live-tested file
- Honest review of every `🚧 draft` — promote only what was actually tested
- CI baseline: compose validate, secret scan, markdown lint, image vulnerability scan (Trivy or Grype)
- Secret & Password Generation Standard consolidated into `docs/standards/`
- Secrets rotation guidance in `docs/standards/`
- License audit — every live app verified against the license policy below
- **Status freshness system active** — `Last verified` stamps in place, Major upstream updates drop status to `🚧`; tactical work moves to GitHub Issues

---

## Continuous — not tied to a version

**App testing runs in parallel to everything above.** Any time there is bandwidth: pick a `🚧` app, run the App Chain, set it to `✅`. This does not block or trigger a release. The bar for `✅` rises with the repo — an app verified today must meet the current ✅ Ready Criteria in [`docs/maintenance.md`](docs/maintenance.md), not the bar from v0.1.

Apps still to re-verify on a clean install (pre-v0.2 installs, standards have since evolved):
Vaultwarden, WordPress, Nextcloud, Seafile / Seafile Pro, Invoice Ninja.

---

## In the backlog — individual app paths

App-level work that does not drive version tags.

### Choice-matrix categories — pick-one-per-install decisions

When live-tested on real data, pick the default and deprioritise the rest:

- **Dashboards** — Dashy, Heimdall, Homarr, Homepage (`apps/`)
- **Photo galleries** — Immich, LibrePhotos, Lychee, PhotoPrism, Photoview (`apps/`)
- **Scheduling** — Cal.com (AGPL + commercial), Cal.diy (MIT community), Easy!Appointments (`apps/`)
- **Business wikis** — BookStack is live; Wiki.js and Outline are planned (`apps/`)
- **Forms** — OpnForm is drafted; Formbricks and HeyForm are planned (`apps/`)

### Categories with roadmaps in their own READMEs

- [`monitoring/README.md`](monitoring/README.md) — Uptime Kuma, Gatus, Beszel, changedetection (drafted) + 6 planned
- [`business/README.md`](business/README.md) — Listmonk, Zammad, Kimai, OpenSign (drafted) + planned: Plane, Leantime, AppFlowy
- [`backup/README.md`](backup/README.md) — Kopia, Borgmatic, Bareos, UrBackup (all planned)

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

Every app documents its license in `UPSTREAM.md`. The ✅ Ready Criteria require this field to be present before an app is marked as ready.

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

- `core/acme-certs/` — being extracted to its own repository. The blueprint stub remains as `🚧 draft` but is no longer actively maintained in this repo.
- Paperless-mcp — template exists in the Paperless CONFIG.md extension notes but will live in its own repo once built.
