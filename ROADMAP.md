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

### v0.6.0 — CrowdSec Firewall Bouncer (nftables)

Host-level blocking via nftables — drops packets before they reach Traefik.
Complements the L7 Traefik bouncer shipped in v0.4.0. Architecturally
separate (OS-level install), so treated as its own tag.

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

### v0.9.0 — CrowdSec: operational control

CrowdSec runs after v0.4 and v0.6, but remains a black box — it is not clear what it blocks, whether it has self-blocked you, or how to intervene quickly. This version makes it observable and controllable:

- **Dashboard** — CrowdSec dashboard or Metabase integration: see what is being blocked in real time
- **Runbook** — how to check decision lists, whitelist your own IP, drain false positives, disable quickly if needed
- **Geoblocking** — structured setup with documented trade-offs (not just "add a list")
- **AppSec tuning** — review default rules, document any false-positive patterns specific to this stack

Goal: after this version, CrowdSec is a tool you can confidently operate, not just something that runs in the background.

### v0.10.0 — App configuration tiering

Most apps currently have one level of configuration: "it runs." This version introduces a consistent tiering across all live apps:

- **Minimum** — the smallest working set of env vars. No hidden required settings. Someone who just wants the app running can stop here.
- **Advanced** — performance, storage, and integration options. Commented out by default, with a brief note on what each does. Paperless Phase 4 (8 mandatory env-var fixes) is the first example of what this looks like in practice.
- **Expert** — deep tuning, rarely needed. May reference upstream docs rather than repeating them.

The tiering lives in `.env.example` (inline comments) and `CONFIG.md` where the app already has one. Not every app needs all three levels — the point is that Minimum is always explicitly defined.

### v0.11.0 — Resource limits

Every live app gets `deploy.resources` (memory + CPU) and `pids_limit`. The standard is already documented in [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md); this version applies it.

Intentionally last before v1.0: wrong limits break apps silently (OOM kills, throttled CPUs). Each app needs values measured on a real install, not guessed. This is the fine-tuning pass — not a quick sweep.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this conversation.

Before v1.0 is tagged:

- Every app at least once sober-tested on a clean install (continuous — not a last-minute sprint)
- No `🚧` without a documented reason
- No `__REPLACE_ME__` in any live-tested file
- Honest review of every `🚧 draft` — promote only what was actually tested
- `CONFIG.md` pattern extended to other complex apps that benefit from it
- CI baseline: compose validate, secret scan, markdown lint, **image vulnerability scan** (Trivy or Grype — catches known CVEs in pinned image versions before they reach production)
- Secret & Password Generation Standard consolidated into `docs/standards/` (currently each app README has its own recipe, some with known pitfalls)
- **Secrets rotation guidance** — documented procedure for rotating `.secrets/` values in a running stack without downtime; lives in `docs/standards/`
- **License audit** — every live app has its license documented in `UPSTREAM.md` and verified against the license policy below

### v1.1 — Living repo

v1.0 is a state. v1.1 is a process — the repo maintains itself:

- **Status freshness system**: every `✅` app carries a `Last verified` stamp. When a Major upstream version ships, status drops to `🚧` until re-verified. Minor updates within a Major are low-risk and require only an `UPSTREAM.md` bump. Rule lives in [`docs/maintenance.md`](docs/maintenance.md).
- **GitHub Issues replace `ROADMAP.md` for tactical work**: strategic direction stays in this file; per-app tasks ("re-verify Vaultwarden", "add Advanced tier to Nextcloud") move to Issues — trackable, closeable, referenceable.
- **Packages / bundles** (`docs/packages/`): opinionated stacks for common setups — "Small-Business Starter", "Home Lab Photo + Files", etc. Each names the picks, reading order, and integration config.

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
- [`business/README.md`](business/README.md) — Listmonk, Zammad, Kimai, OpenSign (drafted) + 2 planned
- [`backup/README.md`](backup/README.md) — Kopia, Borgmatic, Bareos, UrBackup (all planned)

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

### App Evaluation Criteria (concept — still to develop)

Structured per-app metadata to help make informed decisions before deploying. Not a rating scale — factual criteria that each person weighs themselves. Candidate criteria:

- **Origin**: country / organisation behind the project
- **License**: AGPL, GPL, MIT, Apache, commercial dual-license, …
- **Stack size**: number of containers, minimum RAM
- **Security features**: Docker Secrets / `_FILE` support, 2FA, SSO / OIDC integration, audit log
- **Active development**: release cadence, last commit, community size
- **Privacy posture**: what gets logged, telemetry / phone-home behaviour, GDPR posture

Still open: where this lives (extension of `UPSTREAM.md`? standardised block in each app `README.md`? separate `EVAL.md`?) and how to keep it from becoming a maintenance burden.

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
