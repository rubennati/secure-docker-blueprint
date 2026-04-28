# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also: [ROADMAP.md](ROADMAP.md) for what is coming next, and per-app CHANGELOGs where applicable.

## [Unreleased]

### Authentik live

Authentik now live-tested end-to-end. Initial-setup flow reachable through Traefik (`/if/flow/initial-setup/`), admin account creation works, all four services (`server`, `worker`, `db`, `redis`) stable and healthy. Status in the Core Infrastructure table flips ⚠️ → ✅.

### Fixed

- **Authentik volume permissions**: the `goauthentik/server` image runs as UID 1000 and deliberately refuses to chown bind-mount targets (`"Not running as root, disabling permission fixes"`). Added a one-shot `init-perms` Alpine service that pre-chowns `./volumes/{data,certs,custom-templates}` to `1000:1000` before `server` and `worker` start. The permission logic lives in `core/authentik/ops/scripts/init-volumes.sh` (POSIX sh, idempotent).
- **Authentik legacy `/media` mount**: upstream migrated to `/data`. Both `server` and `worker` now mount `./volumes/data:/data`; `/media` was deprecated.
- **Authentik healthcheck**: the image ships no `wget` or `curl`, so the wget-based healthcheck failed every time and kept the container marked unhealthy despite the app serving normally. Switched to a Python-based check via `urllib.request` (Python is in the image). `start_period` bumped 30s → 60s to cover cold-start Django migrations.

### Documentation

- `docs/bugfixes/authentik-2026-04-20.md` documents all three bugs (volume perms, legacy path, broken healthcheck) with symptoms, root causes, and upstream references.

### Consistency Audit — first pass

First live run of the maintenance process (`docs/maintenance.md`). Findings fixed:

- **Root README pattern**: tables now contain only `⚠️` / `✅` entries. `📋` planned items appear as inline `Planned: X, Y, Z` lines below each section — consistent across all categories. Backup all-📋 table replaced with an inline line. Ackee moved to inline planned list in business section.
- **SMTP hostname leak**: `ghost`, `calcom`, `invoiceninja` `.env.example` had real vendor hostnames (`brevo.com`, `mailtrap.io`) set as default values. Fixed to `smtp.example.com`.
- **`__REPLACE_ME__` scan rule**: scoped to `docker-compose.yml` and scripts only — `.env.example` files use `__REPLACE_ME__` intentionally as credential placeholders.
- **Vendor hostname scan**: new rule added — `.env.example` defaults must be `example.com` or empty.

### Maintenance process

`docs/maintenance.md` added — defines the governance structure for keeping the repo accurate and consistent: single source of truth map (which file owns which information), four maintenance cycles (session / app pass / version audit / consistency audit), quick-reference checklists for each cycle, and a running Maintenance Log table so every session starts from a known state.

### Moved / renamed

- **Ackee** moved from `apps/` (Publishing & knowledge) → `business/` (Marketing & analytics). Status corrected from `⚠️ draft` → `📋 planned` — no files exist yet, so draft was inaccurate.

### Architecture documented

`docs/architecture.md` added — explains the design goals, directory structure rationale (split by access pattern, not user type), hub-and-spoke networking model, four-layer security stack (Traefik → CrowdSec → Authentik → container hardening), core service roles, per-app directory layout, and backup isolation principle. The "why" behind the structure visible throughout the rest of the repo.

`backup/README.md` gains a **Per-App Backup Isolation** section: each app gets its own repository, retention policy, and cron schedule — independent failure, independent restore, controlled blast radius.

### Security baseline — Resource Limits

`docs/standards/security-baseline.md` now documents the **Recommended** standard for `deploy.resources` (memory / CPU) and `pids_limit` per container. Fills the last significant gap in the blueprint's security posture: without defined limits a crashed or compromised container can starve the host kernel. Values are calibrated by service profile (lightweight helper / cache / standard web app / database / heavy app). Applying the limits to every live-tested app is tracked as a v1.0 polish item in the ROADMAP.

### Authentik upgraded to 2026.2.2

Version bumped from `2024.12.3` (initial live-test pin) to `2026.2.2` (current latest). Verified on a clean install — all migrations run from scratch without errors. Worker healthcheck explicitly disabled (`healthcheck: disable: true`) as upstream removed the built-in worker check in `2025.10.2`.

### Fixed

- **Authentik version-jump migration failure**: upgrading `2024.12.3` → `2026.2.2` directly crashes both server and worker with `FieldError: Cannot resolve keyword 'group_id'` in migration `0056_user_roles`. Root cause: intermediate data-migration script references a field removed before `2026.2`. Fix for blueprint test environments: wipe volumes and start fresh. Fix for production: upgrade incrementally through each major release. Documented in `docs/bugfixes/authentik-upgrade-2026-04-27.md`.

---

Next tag direction: **Paperless-ngx `/admin` protected by Authentik Forward-Auth** as the first end-to-end use case for the new SSO. Then: CrowdSec Firewall Bouncer (nftables) for host-level blocking.

## [0.4.0] — 2026-04-20

### CrowdSec Bouncer Plugin live (Phase 2)

The Traefik bouncer plugin now enforces CrowdSec decisions end-to-end on a fresh install. Banned IPs receive HTTP 403 at the proxy; legitimate traffic passes through unchanged. Proven with a browser ban test against a real router.

### Fixed

- **Traefik plugin storage**: `read_only: true` on the Traefik container prevented `experimental.plugins` from creating `/plugins-storage/`, which silently disabled the plugin manager and made every `sec-crowdsec@file` middleware reference return HTTP 404. Added a dedicated `./volumes/plugins-storage:/plugins-storage` bind mount — root FS stays read-only, plugins work.
- **AppSec fail-closed default**: `integrations.yml.tmpl` shipped with `crowdsecAppsecEnabled: true` + `crowdsecAppsecUnreachableBlock: true`. With no AppSec server wired up, the plugin failed its WAF query on every request and blocked fail-closed (HTTP 403 with zero active decisions). All three AppSec flags now default to `false`; enable only when the AppSec server at :7422 is actually deployed.

### Added

- **Phase 2 verify section** in `core/crowdsec/README.md`: 4-step checklist (plugin loaded, bouncer pulls from LAPI, middleware registered in dashboard, functional ban test) with a warning not to ban the admin's own IP in stream-mode cache windows.

### Documentation

- `docs/bugfixes/traefik-crowdsec-plugin-2026-04-20.md` documents both first-setup bugs with a discriminator table — same visible failure mode (403/404 on routers with `sec-crowdsec@file`), different root causes, different fixes.
- Root README: CrowdSec description updated from "Intrusion detection engine — log analysis, threat decisions, AppSec/WAF" to "Intrusion detection engine + Traefik bouncer plugin — log analysis, threat decisions, L7 blocking" to reflect the live Phase 2 posture.

## [0.3.0] — 2026-04-20

### Core complete

Every core service reachable on a fresh install, both multi-host management paths (Dockhand + Hawser, Portainer + Portainer Agent) proven end-to-end.

### Fixed

- **Traefik**: `integrations.yml` template contained a dangling `http:/middlewares:` structure that aborted the dynamic config load with "http cannot be a standalone element". File is now fully commented by default — no routers, middlewares, or ACME issuance silently disabled on first boot.
- **Portainer**: removed custom wget-based healthcheck. The Portainer image ships no wget/curl/shell, so any CMD-SHELL healthcheck left the container marked unhealthy indefinitely. Runs healthy by default now.

### Added

- **Portainer Edge Agent** (`core/portainer-agent/`) as the counterpart to Hawser. Both agents tested end-to-end on a fresh install:
  - Dockhand + Hawser: everything on standard HTTPS 443 via Traefik
  - Portainer + Portainer Agent: requires an extra TCP 8000 tunnel port on the central host (VPN-bound only; see inline documentation)
- **Certificate strategy** documented in `core/traefik/README.md`: wildcard vs. per-domain, which env vars + which compose labels go with each. Previously implicit, now explicit.
- **`docker-compose.override.yml` pattern** in `core/portainer/`: local installation-specific ports / overlays stay out of the tracked compose, gitignored.
- **Status column** on the Core Infrastructure table in the root README, aligned with the ✅ / ⚠️ legend used elsewhere.

### Documentation

- `docs/bugfixes/traefik-2026-04-20.md`, `docs/bugfixes/portainer-2026-04-20.md` capture root cause + fix for the two bugs above.
- Per-service READMEs updated where setup needed a missing step: Dockhand ("Adding the local environment"), Hawser ("environment must be saved in Dockhand before the token works"), Portainer Agent (4-step Edge Mode setup + VPN-bind guidance).

### Moved / renamed

- `core/acme-certs/` marked draft (⚠️) — extracted to its own repository. The blueprint no longer treats it as live-tested core.

## [0.2.0] — 2026-04-18

### Structure Stable Baseline

Repository layout is now stable: forks can rely on the five top-level directories (`core/`, `apps/`, `business/`, `monitoring/`, `backup/`). Per-category READMEs document scope and roadmap.

### Added

- **New top-level directories**: `business/`, `monitoring/`, `backup/`. Each with a dedicated README defining scope and roadmap.
- **`monitoring/`** (4 drafted, 6 planned): Uptime Kuma, Gatus, Beszel, changedetection.io, Healthchecks.
- **`business/`** (1 live, 6 drafted, 2 planned): Invoice Ninja (live), Dolibarr, Matomo, Kimai, Listmonk, Zammad, OpenSign; Live Helper Chat + Eramba GRC planned.
- **`backup/`** (roadmap only): Kopia, Bareos, UrBackup planned.
- **17 new apps drafted** (`apps/`): Adminer, IT-Tools, Dashy, Heimdall, Homarr, Homepage, BookStack, Immich, LibrePhotos, Lychee, PhotoPrism, Photoview, Monica, n8n, NocoDB, OpnForm, UniFi Network Application.
- **Cloud-free data chain** documented (OpnForm → n8n → NocoDB webhook pattern) in each relevant README.
- **Two-router Traefik split** pattern for apps that need admin-VPN-only + subscriber-paths-public (Listmonk, Invoice Ninja).
- **Path-based Traefik router split** pattern for API+UI-on-one-host apps (OpnForm, OpenSign).

### Changed

- **7 directory moves** to align with the sharpened categorisation rule:
  - `apps/healthchecks/` → `monitoring/healthchecks/`
  - `apps/invoiceninja/` → `business/invoiceninja/`
  - `apps/dolibarr/` → `business/dolibarr/`
  - `apps/matomo/` → `business/matomo/`
  - `apps/dockhand/` → `core/dockhand/`
  - `apps/portainer/` → `core/portainer/`
  - `apps/hawser/` → `core/hawser/`
- **Root README** restructured around the five-category layout, with per-category tables and a "Repository layout" overview section.

### Security

- **Repo-wide scan pass**: no real domains, IPs, or author-identifying strings in any committed file on `main` / `dev`.
- **All secrets use Docker Secret `_FILE` pattern** where the upstream image supports it. Apps without `_FILE` support use the `DB_PWD_INLINE` convention with the duplicate-password-in-env trade-off documented in their README.
- **`no-new-privileges:true`** on every container.
- **MariaDB `cap_drop: ALL` + minimal `cap_add`** on every MariaDB service.
- **Internal networks (`internal: true`)** isolate DBs / Redis / ML from the host on every multi-service app.

### Statistics

- Live-tested apps: 14
- Drafted apps: 30+
- Planned apps in category READMEs: ~18
- Top-level categories: 5

## [0.1.0] — 2026-04-16

Initial public release.

### Core infrastructure

- **Traefik** reverse proxy with socket-proxy, 10 security chains (`sec-0` to `sec-5` plus iframe-friendly `e` variants), 5 access policies (public / local / tailscale / private / deny), 3 TLS profiles (basic / aplus / modern)
- **CrowdSec** integration in three phases (engine, bouncer plugin, firewall bouncer), phase 1 live and phase 2 ready-to-enable
- **Authentik** identity provider for SSO (Forward-Auth, OAuth2 / OIDC / SAML)
- **OnlyOffice** document server with dedicated iframe-friendly middleware chain

### Apps

10 hardened Docker Compose deployments with per-app `README.md` + `UPSTREAM.md` + `.gitignore` + standards-aligned `docker-compose.yml` and `.env.example`:

- dockhand, portainer, whoami (core), ghost, nextcloud, seafile, calcom, paperless-ngx
- Plus core services: onlyoffice, traefik, authentik

### Standards and documentation

- `docs/standards/` — compose-structure, env-structure, naming-conventions, security-baseline, commit-rules, documentation-workflow, traefik-labels, traefik-security, new-app-checklist
- `docs/app-setup-blueprint.md` (on `docs` orphan branch) — 8-phase workflow for adding or updating apps, v2 introduces `CONFIG.md` as mandatory per-app artifact
- `apps/paperless-ngx/CONFIG.md` — reference implementation of the CONFIG.md format bucketed by Mandatory / Nice-to-have / Use-case-dependent
- Per-app hardening reference: WordPress (PHP security, `.htaccess`, mu-plugin, test-security.sh with 24 checks)

### Licensing and policies

- Apache 2.0 license
- `SECURITY.md` with GitHub Private Vulnerability Reporting workflow
- `ROADMAP.md` as single source of truth for project direction, updated per-commit not retroactively

### Known limitations in this release

- Package 7 of the coherence audit (compose fixes for Invoice Ninja, Vaultwarden, Hawser) not yet complete
- Paperless-ngx Phase 4 security hardening (8 mandatory action items per `apps/paperless-ngx/CONFIG.md`) still to roll out
- No CI workflows yet (compose validate, markdown lint, secret scan) — planned for 0.2.0
- No automatic backup orchestration — planned in Evaluating section of ROADMAP

[Unreleased]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.3.0
[0.2.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.2.0
[0.1.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.1.0
