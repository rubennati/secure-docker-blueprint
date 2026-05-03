# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also: [ROADMAP.md](ROADMAP.md) for what is coming next, and per-app CHANGELOGs where applicable.

## [Unreleased]

---

## [0.5.0] — 2026-05-03

### Authentik Forward-Auth integration live

Traefik Forward-Auth patterns documented and proven end-to-end. Two variants
implemented and tested:

- **Pattern 1 — full app** (Dashy, Heimdall): the entire app is behind
  Authentik. One router, `sec-authentik@file` in the middleware chain. Unauthenticated requests redirect to the Authentik login page.
- **Pattern 2 — path-scoped** (Paperless-ngx `/admin`): a second Traefik
  router with `priority=100` and `PathPrefix(/admin)` carries `sec-authentik@file`; the main router stays open. Allows a public-facing app to protect only its admin backend.

Both patterns are opt-in — commented out by default in each app's
`docker-compose.yml`. Activation instructions in
`core/authentik/README.md` — Step 0 (one-time Traefik middleware setup) and
Pattern 1 / Pattern 2 sections.

The `sec-authentik` middleware in `core/traefik/ops/templates/dynamic/integrations.yml.tmpl` also documents that `forwardAuth` is not limited to the local Docker host — the `address` field accepts any reachable endpoint (other LAN machine, remote server).

### SPA rate-limit fix — rl-spa + sec-*-spa chains

Code-split SPAs (NocoDB, n8n, Authentik login page) fire 100+ parallel HTTP
requests on first visit. The existing `rl-soft` token bucket (burst: 50) is
exhausted in milliseconds → HTTP 429 on initial page load. The temporary
`sec-1` workaround (no rate limit at all) has been replaced with a proper fix:

- **`rl-spa`** — new rate-limit block: `average: 100, burst: 200`. Absorbs
  the initial SPA chunk load. Safe only behind a network-level access control
  (`acc-tailscale`).
- **`sec-2-spa`** — basic headers + rl-spa + compress.
- **`sec-3-spa`** — strict headers + rl-spa + compress + permissions-policy.

NocoDB and n8n: `APP_TRAEFIK_SECURITY=sec-1` → `sec-3-spa`.

For the Authentik login page (public access): router splitting — a dedicated
`/_static/` router with `sec-1@file` (no rate limit) and `priority=100`
handles static assets; the main Authentik router keeps `sec-3` for all other
paths (API, flow endpoints). Canonical Traefik OSS pattern.

### Fixed

- **Traefik path-scoped router priority** (`apps/paperless-ngx`,
  `core/authentik`): explicit `priority=10` loses to the auto-calculated
  priority from rule string length (~29 for a typical `Host(...)` rule).
  The path-scoped `-admin` and `/_static/` routers never won. Fixed:
  `priority=10` → `priority=100`.
- **Authentik Pattern 2 External host** must include the protected path.
  With External host set to the domain root, Authentik redirects there after
  login — for Paperless-ngx the Angular frontend shows `/404` because the
  user has no Paperless account. Correct value: `https://<host>/admin/`.
  Documented in `core/authentik/README.md` Pattern 2 Step 2a.
- **`security-chains.yml.tmpl` table**: `sec-1e`, `sec-2e`, `sec-3e` were
  missing from the header table entirely. Table rewritten with explicit
  content column (no cumulative `+` notation) and inline comments added for
  all `e` variants.

### Documentation

- `docs/bugfixes/authentik-forward-auth-2026-05-03.md` — three bugs with
  root causes and fixes: router priority, Pattern 2 External host,
  SPA 429 rate-limit.

### IT-Tools, Adminer, NocoDB, n8n live

All four apps live-tested on clean installs. Status `🚧 → ✅`.

Six bugs found and fixed across the four apps:

- **IT-Tools — non-existent tag**: `.env.example` referenced `2025.7.18-a0bc346` which does not exist on GHCR. Corrected to `2024.10.22-7ca5933`.
- **IT-Tools — cap_drop crash-loop**: `cap_drop: ALL` dropped `CAP_CHOWN`, which the nginx entrypoint requires to set up `/var/cache/nginx/*` before dropping to UID 101. Removed `cap_drop: ALL`; filesystem hardening retained via `read_only: true` + `tmpfs` for `/tmp`, `/var/cache/nginx`, `/var/run`.
- **Adminer — healthcheck always unhealthy**: the official `adminer` image ships no `curl` or `wget`. Replaced the `curl`-based check with a PHP one-liner using `stream_socket_client('tcp://127.0.0.1:8080')` — PHP is always present in the image. No `$variables` in the expression avoids Docker Compose interpolation.
- **NocoDB / n8n — HTTP 429 on first page load**: both are heavy SPAs that load 100+ assets in parallel on the first visit. The Traefik `sec-3` middleware chain includes `rl-soft` (burst: 50), which is immediately saturated. Resolved in v0.5.0 with the new `sec-3-spa` chain (`rl-spa`, burst: 200). See the SPA rate-limit fix entry above.
- **NocoDB — signup blocked without SMTP**: the original compose file used non-existent env var names for the super-admin. Corrected to `NC_ADMIN_EMAIL` / `NC_ADMIN_PASSWORD` (verified against source); both optional with `:-` default for installs with SMTP.
- **n8n — `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR`**: n8n's internal `express-rate-limit` raised a `ValidationError` on every request because Express `trust proxy` was not configured. Fixed with `N8N_PROXY_HOPS: "1"` — tells n8n to trust one reverse-proxy hop (Traefik) for `X-Forwarded-For`. Source: [n8n-io/n8n#9172](https://github.com/n8n-io/n8n/issues/9172).

Additionally removed the deprecated `N8N_RUNNERS_ENABLED` env var (removed in n8n 2.19.2 — task runner is always active).

### Documentation

- `docs/bugfixes/it-tools-adminer-nocodb-n8n-2026-05-02.md` documents all six bugs with symptoms, root causes, and fixes.

### Security baseline — Resource Limits

`deploy.resources` (memory, CPU, PIDs) moved from the mandatory checklist to the **Optional** section in `docs/standards/security-baseline.md`. Resource limits require per-app investigation before any values are set; they are tracked as a v1.0 polish item in the ROADMAP, not a prerequisite for going live.

### Dashy, Heimdall, Homarr live

All three dashboard apps live-tested on clean installs. Status `🚧 → ✅`.

Version fixes: Dashy `3.1.1` → `4.0.4` (tag never existed; healthcheck path updated for v4: `.js` extension added). Homarr `1.39.0` → `v1.60.0` (tag never existed; note `v`-prefix in GHCR tags).

Security baseline applied across all three:

- **Dashy**: `cap_drop: ALL` added; config mount hardened to `:ro` (file-managed, no in-app editor); `deploy.resources` + `pids_limit` added.
- **Heimdall**: `deploy.resources` + `pids_limit` added; healthcheck added; `cap_drop` intentionally skipped — LSIO/s6-overlay image needs root capabilities during init (same pattern as Paperless-ngx).
- **Homarr**: `deploy.resources` + `pids_limit` added (1G/1.00 cpus — bundles Next.js + internal Redis + cron); healthcheck added; `cap_drop` intentionally skipped — starts as UID=0, runs internal Redis.

Env file corrections: Heimdall and Homarr section headers aligned to `App Configuration` standard; TZ examples comments added.

### Ghost live

Ghost live-tested end-to-end on a clean install: `ghost:6.27.0-alpine` + `mysql:8.4`, with optional ActivityPub overlay (`ghcr.io/tryghost/activitypub:1.2.2`) via `COMPOSE_FILE`. Status `🚧 → ✅`.

Four bugs found and fixed along the way:

- **`ERR_INVALID_ARG_TYPE` at MySQL auth**: Ghost uses nconf's `__` notation — `database__connection__password__file` creates a nested object `{file: '...'}` instead of reading the secret. mysql2 crashes when it receives an Object at sha1. Fixed with a custom `ops/entrypoint.sh` that reads the Docker Secret files and exports plain env vars before handing off to the original entrypoint. Same pattern as other apps in the blueprint.
- **`mysqladmin ping -h localhost` uses Unix socket, not TCP**: healthcheck reported `Healthy` before TCP port 3306 was ready — dependent containers (`activitypub-migrate`) got `connection refused`. Fixed to `-h 127.0.0.1` to force TCP. Password added via `$(cat /run/secrets/DB_ROOT_PWD)` because `MYSQL_ROOT_PASSWORD_FILE` is not resolved outside the init phase.
- **`ERR_TOO_MANY_REDIRECTS` on ActivityPub endpoints**: ActivityPub's `behindProxy` wrapper reconstructs URLs from `X-Forwarded-Proto`. The official ghost-docker setup (Caddy) forwards this header automatically; Traefik requires an explicit `customrequestheaders` middleware on the ActivityPub router.
- **SMTP TLS mismatch (Ghost 6 login blocked)**: Ghost 6 sends an email verification code for every new-device login — broken SMTP blocks the admin login entirely. `mail__options__secure` was hardcoded `true` (SSL/TLS, port 465); Brevo uses port 587 (STARTTLS, `secure: false`). Made `GHOST_MAIL_SECURE` configurable via env var; updated `.env.example` defaults to Brevo/STARTTLS.

ActivityPub separated as an optional overlay (`activitypub.yml`), enabled via `COMPOSE_FILE=docker-compose.yml:activitypub.yml`. Stack structure aligned with the official ghost-docker compose: shared Ghost content volume for ActivityPub images, `mysql-init/` init scripts with `MYSQL_MULTIPLE_DATABASES`, `activitypub-migrations:1.2.2` pinned (corrected from `edge`). Docker Secrets layered on top throughout.

### Documentation

- `docs/bugfixes/ghost-2026-05-01.md` documents all four bugs with root causes and fixes.

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

[Unreleased]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.4.0
[0.3.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.3.0
[0.2.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.2.0
[0.1.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.1.0
