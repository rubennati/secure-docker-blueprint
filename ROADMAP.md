# Roadmap

Last updated: 2026-07-26 (v0.6.0 is the latest release).

This document captures direction, not detailed changelogs. For shipped work see [`CHANGELOG.md`](CHANGELOG.md); for per-category details see the `README.md` in each top-level directory.

---

## Shipped

### v0.6.0 — CrowdSec complete (2026-06-04)

Full CrowdSec operational layer documented and structured for confident day-to-day use. Phase 3 nftables firewall bouncer added: host-level packet enforcement covering SSH and all ports beyond what Traefik sees, with SSH brute-force detection documented as opt-in alongside it. Operations runbook covers health checks, whitelisting, false positive handling, emergency procedures, and maintenance. Dashboard guidance documents the CrowdSec Console (opt-in) and the full CLI alternative. Geoblocking guidance documents country-level decisions, automated scenario, Phase 2/3 interaction, and self-lockout prevention — opt-in with explicit trade-offs. AppSec tuning guidance documents the request-level WAF layer, safe enabling progression, application-specific false-positive patterns (Nextcloud, Paperless-ngx, Authentik, WordPress, Seafile, Invoice Ninja), exclusion mechanics, and emergency disable — opt-in and disabled by default.

### v0.5.1 — Bug fixes and standards (2026-05-03)

Nextcloud internal network isolation fix (database containers had unintended internet access). Seafile floating tags replaced. Tag pinning standard formalised. maintenance.md ✅ Ready Criteria added.

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

## Since v0.6.0 — work outside the plan

Between 2026-06-04 and 2026-07-26 the repo grew in directions this document did not name. Recorded here so the milestones below stay honest. **None of it changes the milestone order** — nothing below depends on it.

| What happened | Where it lands |
|---|---|
| Repo-wide dependency sweep — every registry-checkable image reviewed, ~50 bumped (`docs/maintenance.md`) | Continuous. ~9 major bumps are pinned but have not yet run on a host; they ride along with the next host session. |
| Reference app (`apps/_reference/`) + structure checker (`scripts/ci/check-structure.py`) | New capability, not a milestone of its own. Feeds v0.9.0 (it measures the gap) and v1.0 (CI baseline). |
| Four new previews — `core/infisical`, `core/euro-office`, `core/collabora`, `business/documenso` | Continuous app work — see the choice-matrix categories below. |
| Cal.com retired (upstream went proprietary), replaced by `apps/caldiy`; phased hardening plan written after an incident on a live host | Own track — `apps/caldiy/docs/hardening-plan.md`. Not tied to a version. |
| Supply-chain hardening — SHA-pinned GitHub Actions, Trivy with checksum-verified install, OpenSSF badges, branch protection | Closes part of the v1.0 CI baseline below. |

---

## Direction

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence. The single criterion for v1.0 is: **could someone fork this and run it without needing my mental model?** — subjective but unambiguous when met.

### v0.7.0 — Backup

A working infrastructure is worthless without recovery. The architecture is designed in [`backup/README.md`](backup/README.md) — five layers, staged so the floor is reachable before the hardening:

1. **Snapshot** — explained and bounded, not implemented here (it is not a backup)
2. **Consistency** — database dumps via Borgmatic's container-aware hooks, covering PostgreSQL, MySQL, MariaDB and SQLite
3. **File data** — bind mounts and named volumes, both supported without preference
4. **Off-site** — 3-2-1, encryption, key held off the host, immutability with its real limits stated
5. **Proof** — restore rehearsal, `borgmatic check`, and run monitoring through the `monitoring/` stacks already in the repo

The agent runs **on the host**, not in a container — the one deliberate exception to this repository's Docker-only scope, because a containerised agent would need read access to every volume and therefore every secret. Reasoning in `backup/README.md`.

**Restore testing is part of this version** — a backup that has never been restored is a hypothesis, not a backup. At least one full restore walkthrough, documented step by step.

Two practical notes:

- A backup component that *does* run in a container starts from `apps/_reference/` and is checked with `scripts/ci/check-structure.py`. `backup/borgmatic/` is host-installed and therefore holds configuration and procedure instead of a Compose stack.
- The restore walkthrough needs a reachable host with real data — the same precondition as the pending major bumps above. Both are best done in one host session.

### v0.8.0 — Monitoring

Backup tells you what to do when something breaks. Monitoring tells you that something broke — and ideally before it causes data loss or downtime. Four layers:

- **Host** — CPU, RAM, disk, network trends over time. Beszel is the default: lightweight, self-hosted, no external dependencies. Know when a disk is filling up before it becomes an incident.
- **Container / Docker** — which containers are running, which have restarted, resource usage per service. Beszel covers this alongside host metrics.
- **Uptime & endpoints** — is the service actually responding correctly from the outside? Gatus or Uptime Kuma with per-app health checks and status page.
- **Alerting** — push or email notification when a service goes down or a threshold is crossed. Without this, monitoring is a dashboard nobody watches.

Each layer gets a proven setup in the blueprint. Log aggregation (Loki/Grafana stack) is out of scope here — heavier infrastructure that fits a later pass.

### v0.9.0 — Resource limits and Operator Site launch

Every live app gets `deploy.resources` (memory + CPU) and `pids_limit`. The standard is already documented in [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md); this version applies it.

Intentionally late: wrong limits break apps silently (OOM kills, throttled CPUs). Each app needs values measured on a real install, not guessed. This is the fine-tuning pass — not a quick sweep.

The size of the gap is now measurable rather than estimated — `python3 scripts/ci/check-structure.py` reports it per service. As of 2026-07-26, across 54 apps: **102 services without `deploy.resources.limits`, 41 without a healthcheck.** That number is the milestone's progress bar.

The Operator Site — an Astro/Starlight site published via GitHub Pages — also reaches its official published state at this milestone. The site is the operator-facing entry point; the repository remains the technical source of truth and nothing moves out of it. The site starts deliberately small and curated, not as a mirror of the full repository. Initial scope covers Home, Getting Started, Applications (with Vaultwarden as the first full reference guide), Operations, FAQ, and Project/Governance. The build and deployment workflow is in place by this milestone. Once published, the repository README can route operator-focused users to the site.

### v1.0 — Complete and hand-off ready

The criterion: someone else could fork this and deploy it without needing this conversation.

Before v1.0 is tagged:

- Every app verified at least once on a clean install (continuous — not a last-minute sprint)
- No `🚧` without a documented reason
- No `__REPLACE_ME__` in any verified file
- Honest review of every `🚧 preview` — promote only what was actually verified
- CI baseline: compose validate, secret scan, markdown lint, image vulnerability scan (✅ Trivy, since v0.6.0), structure checker wired in (`scripts/ci/check-structure.py` — written, not yet running in CI)
- Secret & Password Generation Standard consolidated into `docs/standards/`
- Secrets rotation guidance in `docs/standards/`
- License review — every live app checked against the license policy below
- **Status freshness system active** — `Last verified` stamps in place, Major upstream updates drop status to `🚧`; tactical work moves to GitHub Issues
- Status model applied end to end — [`docs/standards/status-model.md`](docs/standards/status-model.md) defines what each symbol promises, [LIFECYCLE.md](LIFECYCLE.md) is generated from the owning files, and CI fails on a status claim that is not backed

---

## Continuous — not tied to a version

**App testing runs in parallel to everything above.** Any time there is bandwidth: pick a `🚧` app, run the App Chain, set it to `✅`. This does not block or trigger a release. The bar for `✅` rises with the repo — an app verified today must meet the current ✅ Ready Criteria in [`docs/maintenance.md`](docs/maintenance.md), not the bar from v0.1.

Apps still to re-verify on a clean install (pre-v0.2 installs, standards have since evolved):
Vaultwarden, WordPress, Nextcloud, Seafile / Seafile Pro, Invoice Ninja.

Added 2026-07-26 — pinned to a new major during the dependency sweep, not yet run on a host:
Paperless-ngx 3.x, WordPress 7.x, Immich 3.x, Healthchecks 4.x, NocoDB (CalVer switch), Adminer 5.x, Homepage 1.13.x, OpnForm 2.2.x, Uptime Kuma 2.x. Each is marked `🚧` in `docs/maintenance.md`; verify on the next host session before the status claim stands.

**Operator Site work can happen continuously before v0.9.0** — content drafts, structure, and review loops are ongoing. Public, operator-facing publication is gated by the v0.9.0 milestone.

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

- [`monitoring/README.md`](monitoring/README.md) — 6 services in place + 6 planned (Statping, ciao, Checkmate, Zabbix, Grafana + Prometheus, Scrutiny)
- [`business/README.md`](business/README.md) — 10 services in place + 7 planned (Plane, Leantime, AppFlowy, Ackee, Plausible CE, Live Helper Chat, Eramba GRC)
- [`backup/README.md`](backup/README.md) — Kopia, Borgmatic, Bareos, UrBackup (all planned — this is v0.7.0 above)

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

- `core/acme-certs/` — being extracted to its own repository. The blueprint stub remains as `🚧 preview` but is no longer actively maintained in this repo.
- Paperless-mcp — template exists in the Paperless CONFIG.md extension notes but will live in its own repo once built.
