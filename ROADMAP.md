# Roadmap

Last updated: 2026-04-20 (Authentik live).

This document captures direction, not detailed changelogs. For shipped work see [`CHANGELOG.md`](CHANGELOG.md); for per-category details see the `README.md` in each top-level directory.

---

## Shipped

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

Pre-1.0 tags are set when a natural milestone is reached, not on a fixed cadence. The single criterion for v1.0 is "would I recommend this repo as a fork base to a third party?" — subjective but unambiguous when met.

Next natural tag points, in order but without hard schedule:

### CrowdSec Firewall Bouncer (nftables)

Host-level blocking, complements the L7 Traefik bouncer shipped in v0.4.0. Drops packets before they reach Traefik. Architecturally separate (different deployment pattern, OS-level install), so treated as its own tag.

### Paperless-ngx Forward-Auth via Authentik

Authentik itself is now live (status ✅ in the Core Infrastructure table; three first-setup bugs fixed and documented in `docs/bugfixes/authentik-2026-04-20.md`). The outstanding piece is the first production use-case: putting Paperless-ngx `/admin` behind an Authentik forward-auth middleware. That validates the pattern for broader rollout.

### Paperless-ngx security hardening phases

Phases 0–3 (gap analysis, env catalogue) are done — see [`apps/paperless-ngx/CONFIG.md`](apps/paperless-ngx/CONFIG.md). Phase 4 is the 8 mandatory env-var fixes; Phase 5 is `/admin` behind Authentik; Phase 6 is optional extension apps (paperless-gpt / paperless-ai / paperless-mcp).

### v1.0 polish

Before v1.0 is tagged:

- Scan for `__REPLACE_ME__` remnants in live-tested files
- Honest review of every `🚧 draft` — keep honest, promote only what was actually tested
- `CONFIG.md` pattern extended to other complex apps that benefit from it
- CI pass (compose validate, secret scan, markdown lint)
- **Resource limits rollout**: apply `deploy.resources` (memory/CPU) and `pids_limit` to every live-tested app per the profile table in `docs/standards/security-baseline.md`. Standard is documented; per-app values still need to be set.

---

## In the backlog — individual app paths

App-level work that does not drive version tags. Picks up continuously as live-testing progresses.

### Complex apps still to re-verify end-to-end

Vaultwarden, WordPress, Nextcloud, Seafile / Seafile Pro, Invoice Ninja, Paperless-ngx are marked live-tested from pre-v0.2 runs but have not been re-verified on a clean install yet. Low risk (blueprint patterns stable) but worth a pass before v1.0.

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

### App Evaluation Criteria (concept — still to develop)

Structured per-app metadata to help users make informed decisions before deploying. Not a rating scale — factual criteria that each person weighs themselves. Candidate criteria:

- **Origin**: country / organisation behind the project
- **License**: AGPL, GPL, MIT, Apache, commercial dual-license, …
- **Stack size**: number of containers, minimum RAM
- **Security features**: Docker Secrets / `_FILE` support, 2FA, SSO / OIDC integration, audit log
- **Active development**: release cadence, last commit, community size
- **Privacy posture**: what gets logged, telemetry / phone-home behaviour, GDPR posture

Still open: where this lives (extension of `UPSTREAM.md`? standardised block in each app `README.md`? separate `EVAL.md`?) and how to keep it from becoming a maintenance burden.

### Secret & Password Generation Standard

Blueprint-wide policy for secret generation (in `.secrets/` files) and password generation (for admin accounts). Currently each app README has its own recipe, some with known pitfalls (Laravel / Mongo DSN incompatibility with certain chars). Consolidation into a single `docs/standards/` reference is open.

### Recommendations & Packages

As live-testing of choice-matrix categories completes, a `docs/packages/` section captures opinionated bundles: "Small-Business Starter", "Cloud-free Data Collection", "Photo Home Lab". Each bundle names the picks, reading order, and integration config. Planned for v1.0 polish.

### Alternative container runtimes

Long-term consideration beyond standard Docker — Podman, Docker Swarm, K3s. Not blocking v1.0.

### MCP connectors

Expose selected apps via Model Context Protocol for AI-assisted operation. Candidates: Paperless-ngx document search, Vaultwarden secret retrieval. Blueprint defines the pattern; individual MCP servers live in their own repos.

### Deploy script

`./deploy.sh <server> core/traefik apps/nextcloud` — rsync selected app directories to a server, no git / docs / inbox on target. Portable app deployments without the full blueprint on each host.

---

## Out of scope here

- `core/acme-certs/` — being extracted to its own repository. The blueprint stub remains as `🚧 draft` but is no longer actively maintained in this repo.
- Paperless-mcp — template exists in the Paperless CONFIG.md extension notes but will live in its own repo once built.
