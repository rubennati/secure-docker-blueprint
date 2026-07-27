# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also: [ROADMAP.md](ROADMAP.md) for what is coming next, and per-app CHANGELOGs where applicable.

## [Unreleased]

### Added

- **Coverage checker** (`scripts/ci/check-coverage.py`, CI job `Checker coverage`): inverts the question the other jobs ask — not "does this stack comply?" but "is there content nothing looks at?". A directory counts as covered when either the structure checker enumerates it or the lifecycle report includes it; neither alone suffices, since the structure checker keys on compose files and cannot see a host-installed component. Fails on a content directory nothing enumerates and on a tracked top-level directory declared nowhere, so adding a category now blocks CI until a checker claims it. Verified against both historical gap classes rather than assumed: a compose-less stack directory and an undeclared top-level directory each produce a FAIL. Three such gaps had surfaced by accident within one day, each having left real stacks unchecked for months. Runs but is not yet in the required set — that is a branch-protection setting.
- **Backup documentation, repository-wide** (51 stacks, 7 of 59 → 58 of 59): every stack README now carries a `## Backup` section, written from its compose file — database engine, container, database name and user, the `.secrets/` path, which volumes hold state versus reproducible data, and a copy-pasteable borgmatic block. `/etc/borgmatic/config.yaml` is assemblable from the apps instead of reverse-engineered from compose files during an incident. The value is in what is not obvious from the configuration: Seafile needs **three** databases dumped and backing up only `seafile_db` restores to something that starts and does not work; Nextcloud is the one stack where maintenance mode genuinely matters, because the file index and the file tree diverge under load; Immich's Postgres carries a vector extension and must be restored into its own image; PhotoPrism's `volumes/storage` is mostly cache but holds sidecar edits that exist nowhere else, so excluding the whole tree is wrong; Vaultwarden's `rsa_key*` leaves every client unable to log in if lost; OpenSign needs `authentication_database: admin` or the dump authenticates against the wrong database; Zammad and Seafile Pro need a reindex after a restore, during which search returns nothing while every file is present. Several stacks keep their irreplaceable half **outside** the stack directory (`UPLOAD_LOCATION`, `SCAN_DIRECTORY`, `ORIGINALS_PATH`), which is exactly why it gets forgotten. Two stacks carry a block marked unusable as written — Invoice Ninja and Vaultwarden still keep their database password in `.env` rather than `.secrets/`. `backup/urbackup`'s section leads with an *exclusion*: `BACKUP_STORAGE_PATH` must not enter borgmatic's sources. `backup/borgmatic` is `n/a` rather than missing — a backup tool cannot describe backing itself up with itself, and `lifecycle-report.py` carries that as a declared exception.
- **Resource measurement procedure** (`docs/resource-measurement.md`): how to turn a running host into the numbers v0.9.0 needs — what to sample, the load states that make a sample valid, and how a peak becomes a limit. The profile table in `security-baseline.md` stays the owner of the values. Includes a sampler and a peak extractor that normalises `KiB`/`MiB`/`GiB`, because a naive numeric comparison ranks `800MiB` above `1.5GiB` and yields a limit at roughly half the real peak.
- **Host session checklist for v0.8.0** (`docs/host-session-v0.8.0.md`): the six monitoring stacks in one ordered run, sequenced by dependency — the receiver first, then the closed-circuit monitor, then the observing ones. Each block ends with an alert that has to arrive on a real device, not a green dashboard.
- **ntfy** (`monitoring/ntfy/`): 🚧 self-hosted push notification server — the receiving end of the alerting chain, and the first notification receiver in the category. Every monitoring service in the repository can reach it, which is what makes it usable as a single channel across all of them. Deliberately built to stand alone, because a receiver on the monitored host stops when that host does: one Traefik, one compose file, no dependency on the rest of the category. `acc-public` is a documented deviation from the VPN-only default — a receiver has to be reachable from the devices that carry it — with `auth-default-access: deny-all` as the compensating control, since the upstream default leaves every topic world-readable and world-writable once the server is public. Gotify added as 📋 planned; it overlaps with ntfy but has no public instance, so it always needs a host of its own.
- **Alerting documentation** (`monitoring/README.md`): a verified channel matrix — which of the five monitoring services can reach ntfy, Gotify, Matrix, a webhook or SMTP — checked against upstream documentation rather than inferred. Two entries decide setups: **Beszel sends only through Shoutrrr URLs and has no email path**, so a single channel spanning all five cannot be SMTP; and Healthchecks reaches Gotify only through Apprise, which is not in the stock configuration. The dead-man's-switch section is restated as the **closed-circuit principle** from safety engineering — an alarm that fires when the expected signal *stops* is the only kind that detects its own failure. Deployment-topology guidance (where the receiver runs) is separated from what the blueprint itself verifies, so the channel checklist no longer implies a particular server landscape.
- **Per-app backup documentation pattern** (`apps/_reference/README.md`): every app README gains a `## Backup` section naming its database and container, which volumes hold state versus cache, whether it needs quiescing, and a copy-pasteable borgmatic block pointing at the same `.secrets/` file the stack already mounts. The point is that `/etc/borgmatic/config.yaml` becomes assemblable from the apps instead of reverse-engineered from compose files during an incident. Added to the new-app checklist as a step; `LIFECYCLE.md` reports which apps still lack it.
- **Host-session checklist** (`docs/host-session-v0.7.0.md`): everything left for v0.7.0 in one ordered run, since it all shares the same precondition — Borgmatic install and first backup, the restore rehearsal that actually closes the milestone, UrBackup verification, the nine pending major versions, and the 22 legacy verification stamps. Ordered so one failure blocks as little as possible.
- **UrBackup** (`backup/urbackup/`): 🚧 client and endpoint backup — laptops, desktops and other machines back up to storage you own instead of a proprietary cloud. Clients for Windows, macOS and Linux; whole-disk image restore on Windows. This is the second direction of `backup/`: Borgmatic backs up the host, UrBackup backs up the machines around it. Bridge networking with the web interface behind Traefik and `acc-tailscale` by default — upstream's example uses host networking, which removes network isolation and rules out Traefik; manual client addition works without it because the server initiates the connection. `network-host.yml` is an opt-in overlay for those who want broadcast discovery. Digest-pinned, because upstream publishes only rolling series tags. Two baseline deviations documented as inherent to a backup server: no `user:` and no `read_only`.
- **Borgmatic** (`backup/borgmatic/`): 🚧 the v0.7.0 default and the repository's first **host-installed** component — configuration, systemd timer, setup README and restore playbook, deliberately no Compose stack. SSH/SFTP is the primary target. Database dumps use the 2.0.8 `container:` hook for PostgreSQL, MySQL, MariaDB, SQLite and MongoDB — the last covering `apps/unifi` and `business/opensign`, easy to overlook; both bind mounts and named volumes are covered; retention is tied to a stated RPO; run monitoring points at the Healthchecks and Uptime Kuma stacks already in `monitoring/`. `RESTORE.md` is written as a quarterly rehearsal first and a procedure second, and insists on evidence over exit codes. Not yet exercised on a host — the rehearsal log is empty by design.
- **Backup architecture** (`backup/README.md`): the v0.7.0 design, written before any service exists. Establishes the layer model (snapshot / backup / archive, and why the first is not the second), places the backup agent **on the host** as a deliberate, reasoned exception to this repository's Docker-only scope, and covers bind mounts and named volumes without declaring a preference. Database consistency uses Borgmatic's container-aware hooks (2.0.8+ `container:`) — PostgreSQL, MySQL, MariaDB, SQLite and MongoDB, no published ports and no `docker exec` wrapper. Ransomware section states what Borg's append-only mode actually does per upstream documentation: `delete` and `prune` remain permitted, recovery is a manual transaction rollback and only works while `borg compact` has not run — delay and recoverability, not prevention. Adoption is staged in four steps so the floor is reachable before the hardening, and the proof layer reuses the Healthchecks and Uptime Kuma stacks already in `monitoring/`. References BSI IT-Grundschutz CON.3, NIST SP 800-34, ISO 22301 and NIS2. Per-app repository separation is demoted from a rule to an option with its trade-off stated.
- **Status model** (`docs/standards/status-model.md`): one definition replacing three parallel status systems. Separates what an operator can rely on (`preview` / `ready` / `ops-ready`, shown as the README symbol) from what the maintainer has established (`scaffolded` / `verified` / `baseline-aligned` / `ops-proven`, shown in `LIFECYCLE.md`), maps the two onto each other, and names the ✅ Ready Criteria as the single gate between 🚧 and ✅ — all ten criteria together are exactly `baseline-aligned`, which is exactly public `ready`. Also records which file owns which fact, including that `core/` and `apps/` have no category README by design and their status is owned by the root README.
- **Generated lifecycle view** (`scripts/ci/lifecycle-report.py`): `LIFECYCLE.md` is now derived from the owning files — pins from `.env.example`, verification dates from `UPSTREAM.md`, statuses from the owning README — and covers all 54 stacks instead of 6. Hand-maintenance is what let the previous version go three months stale while claiming backup and restore documentation that no stack had. `--write` regenerates, `--check` fails CI.
- **Two CI jobs**: `Canonical structure` runs `check-structure.py` (written in the previous session, never wired in); `Status model` runs `lifecycle-report.py --check`, which fails on a status claim that is not backed — the owner and root README disagreeing, ✅ without a verification date, or `LIFECYCLE.md` left stale. The existing `Structure check` job kept only its file-presence rule and was renamed `Required files`; its `:latest` check is superseded by `check-structure.py`, which also rejects major-only tags.
- **`apps/_reference/UPSTREAM.md`**: the per-app upstream template, folded in from `docs/templates/` — which is now removed, so only one canonical template exists. `README.md` and `new-app-checklist.md` point at the reference app.
- **Homepage** (`apps/homepage/`): v0.10.9 ready, status `🚧 → ✅`. Healthcheck added (`/api/healthcheck`).
- **BookStack** (`apps/bookstack/`): v25.02 ready, status `🚧 → ✅`. Wiki, login, and page creation verified.
- **Easy!Appointments** (`apps/easyappointments/`): v1.5.x ready, status confirmed ✅.
- **Cal.diy** (`apps/caldiy/`): v6.2.0 ready, status `🚧 → ✅`. Full migration run and booking flow verified. Custom entrypoint injects all secrets and builds a safe `postgresql://` URL. TCP fallback healthcheck works around upstream `/api/health` incompatibility.
- **Traefik** (`core/traefik/`): IPv4-only vs. dual-stack IPv6 networking documented and implemented. New opt-in overlay `network-dual-stack.yml` enables IPv4+IPv6 on `proxy-public` (IPv4-only stays the default — no change for existing installs). Addresses the failure mode where a Tailscale IPv6 client loses its real source IP on an IPv4-only public network — Docker's userland-proxy re-sources the connection from the bridge gateway address (e.g. `172.19.0.1`) before Traefik ever sees it, and `acc-tailscale`'s `ipAllowList` then blocks it. New deep-dive doc `core/traefik/docs/ipv6-dual-stack.md` covers Docker daemon prerequisites (`ipv6`, `ip6tables`, `userland-proxy: false`, with backup/rollback), ULA prefix selection, the migration path from an existing IPv4-only network, and troubleshooting. See `docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`.
- **Infisical** (`core/infisical/`): 🚧 self-hosted central secret manager (VPN-only default) + local test stack.
- **Euro-Office** (`core/euro-office/`): 🚧 EU-governed OnlyOffice fork (Nextcloud/IONOS/XWiki/Proton) — drop-in document server + local test stack.
- **Collabora Online** (`core/collabora/`): 🚧 lightweight LibreOffice-based office server (~1 GB vs ~4 GB) + local test stack.
- **Documenso** (`business/documenso/`): 🚧 e-signature platform (DocuSign alternative) + local test stack.
- **Cal.diy hardening**: `docs/hardening-plan.md` (phased roadmap) and `docs/cloudflare.md` (required proxy layer — WAF, geo allowlist, origin lock); public self-registration disabled; `deploy.resources` caps.
- **Local test stacks**: `docker-compose.local.yml` added for Cal.diy and the four new services (standalone on localhost, no Traefik/secrets).
- **Dependency sweep** (`docs/maintenance.md`): repo-wide image-version review with per-service status.
- **Reference app** (`apps/_reference/`): the canonical, runnable structure every app follows — layer-tagged `.env.example`, production + local compose, secret-injection entrypoint, and a README defining the four review lenses (structure, security, architecture, resources). Copy it to start a new app; diff against it to realign an existing one.
- **Structure checker** (`scripts/ci/check-structure.py`): reports drift from that structure with severity per rule — FAIL for dangerous (`:latest`/major-only tags, plaintext secrets, unprotected `.secrets/`, datastore on `proxy-public`), WARN for inconsistent (section order, missing resource limits or healthchecks, `env_file:`). Not yet wired into CI.

### Removed

- **Cal.com** (`apps/calcom/`): retired — Cal.com Inc. moved the production codebase to a proprietary licence. Replaced by `apps/caldiy/`.

### Security

No vulnerabilities in the blueprint's own code. Upstream security image updates + hardening improvements:

- **Upstream security updates applied**: Vaultwarden `1.37.0` (SSRF + 7 fixes), Portainer(+agent) `2.39.5` (containerd/Alpine CVEs), Authentik `2026.5.6`, Nextcloud `32.0.13`, Ghost `6.54.0`, CrowdSec `1.7.8`, Listmonk `6.2.0`, Dolibarr `23.0.3`, Changedetection `0.55.8`
- **`.secrets/` gitignore gap closed**: the repo-root `.gitignore` matched `**/secrets/`, which does **not** match the dot-prefixed `.secrets/` every app actually uses — an app without its own `.gitignore` could have committed real secret files. `**/.secrets/` now covers them repo-wide.
- **Non-reproducible image tags pinned**: `paperless-ngx` postgres `16 → 16.14`, `opensign` mongo `6 → 6.0`, `opnform` nginx `1 → 1.29` — major-only tags silently move to new majors.

- **OpenSSF Best Practices badge**: registered at www.bestpractices.dev (project [#13091](https://www.bestpractices.dev/projects/13091)), 87% passing score
- **GitHub Actions hardening**: all workflow actions pinned to commit SHAs across `ci.yml`, `trivy.yml`, and `scorecard.yml`; workflow-level `permissions: read-all` set on `ci.yml` and `trivy.yml`; `security-events: write` scoped to the single job that uploads SARIF in `trivy.yml`; Dependabot enabled for the `github-actions` ecosystem (weekly, grouped)
- **Trivy install hardened**: `curl | sh` pattern replaced with checksum-verified binary download from GitHub Releases using the official `trivy_0.71.0_checksums.txt` SHA256
- **pip dependency pinned**: `pip install pyyaml` replaced with `pip install --require-hashes -r scripts/ci/requirements.txt`; hashes cover cp312, cp313, and sdist
- **Vikunja Dockerfile**: `USER 1000` added to final stage; `HEALTHCHECK` added (wget to `/api/v1/info`, matching the Compose healthcheck); `busybox` helper stage pinned to digest (`1.38.0-musl@sha256:8635836…`)
- **SECURITY.md**: reporting link changed from relative `../../security` path to absolute `https://github.com/rubennati/secure-docker-blueprint/security/advisories/new` — satisfies OpenSSF Scorecard `SecurityPolicyContainsLinks` probe
- **Branch protection**: main branch now requires 5 CI status checks, 1 approving review, conversation resolution; force-push and deletion blocked
- **Traefik trusted proxy headers**: `forwardedHeaders.trustedIPs` (Cloudflare's published IPv4+IPv6 ranges) added to both entrypoints in `traefik.yml.tmpl` — previously unset, flagged as a gap in `docs/security-verification.md` (control #12). `forwardedHeaders.insecure` remains unset.

### Changed

- **CONTRIBUTING.md**: `## CI and testing` section added — names the CI pipeline as the automated test suite, documents each of the 5 jobs, and provides the primary local validation command (`python3 scripts/ci/check-baseline.py`)
- **docs/security-verification.md**: stale "no CVE scanning" entries updated to reflect `trivy.yml`; GitHub Actions pinning row moved from open gaps to addressed items
- **Cal.diy**: updated to `v6.2.0-4`, pinned by digest; app/db resource caps raised to Cal.com's 2 vCPU / 4 GB minimum. The fork rebuild is not yet exercised on a host — `UPSTREAM.md` keeps `Last verified: 2026-07-26 (v6.2.0-3)` until it is.
- **~30 image pins bumped** across `apps/`, `core/`, `business/`, `monitoring/` (dependency sweep — details in `docs/maintenance.md`). Floating/broken tags fixed: OpenSign and Cal.diy digest-pinned, matomo pinned to `5.12.0-apache`, zammad corrected from the non-existent `7.0.1` tag to `7.1.1-0036`. Majors bumped and flagged 🚧 for migration verification (WordPress 7.0.2, Immich 3.0.3, Paperless-ngx 3.0.3, Healthchecks 4.2, NocoDB CalVer, Homepage 1.13.2, OpnForm 2.2.2, Adminer 5.5.0, Uptime-Kuma 2.4.0)
- **🚧 renamed from "Draft" to "Preview"** across every README and standard. The symbol sits on the public axis, so its label should describe the reader's risk ("evaluate it yourself") rather than the maintainer's progress. Historical CHANGELOG and Progress Log entries keep the original wording.
- **ROADMAP.md** synced after standing still since 2026-06-04. Milestone order deliberately unchanged — nothing in the intervening work blocks v0.7.0. New "Since v0.6.0 — work outside the plan" section places the dependency sweep, the reference app, the four new previews, the Cal.diY track, and the supply-chain work. v0.9.0 now carries measured numbers instead of an estimate (54 apps · 102 services without `deploy.resources.limits` · 41 without a healthcheck).

### Fixed

- **Two stacks were invisible to the structure checker**: `apps/seafile` and `apps/seafile-pro` split their stack across one Compose file per component and have no `docker-compose.yml`, so `scripts/ci/check-structure.py` — which globbed for that exact filename — had never examined either. Two ✅ stacks, never checked for `:latest` tags, plaintext secrets, unprotected `.secrets/` or datastores on the public network. Both are now covered and both pass with zero failures; the warning total rose from 147 to 176 purely because their services became visible. Opt-in overlay files (`activitypub.yml`, `*.local.yml`, `network-dual-stack.yml`) remain deliberately unchecked.
- **12 unbacked status claims**: `business/` (dolibarr, kimai, listmonk, matomo, zammad, opensign) and all six `monitoring/` services claimed ✅ in the root README while their owning category README said 🚧. The category README was right — all twelve carry the pre-v0.5.1 `Last checked:` field instead of `Last verified: DATE (vX.Y.Z)`, so ✅ Ready criterion 8 was unmet. Root README corrected to 🚧; the new CI job prevents a recurrence.
- **Dead links on the front page**: the "New here?" line pointed at `core/README.md` and `apps/README.md`, neither of which exists — both 404'd for every visitor. Those two categories are documented per service in the root README tables instead, and the line now says so.
- **Structure drift cleared**: `core/whoami` had no `.gitignore`, `core/traefik/.env.example` had no `COMPOSE_PROJECT_NAME` (safe to add — its container and network names are set explicitly), and `business/invoiceninja/.env.example` had its sections out of canonical order.

---

## [0.6.0] — 2026-06-04

### Added

- **CrowdSec Phase 3 — nftables firewall bouncer** (`core/crowdsec/`): host-level packet enforcement via `crowdsec-firewall-bouncer-nftables`. Drops traffic from banned IPs before it reaches any service — Traefik, SSH, or otherwise. Complements the Phase 2 Traefik bouncer (L7) with network-layer coverage across all ports and protocols.
- **SSH brute-force detection** (`docs/firewall-bouncer.md`): opt-in setup documented alongside Phase 3. Covers the `crowdsecurity/sshd` collection, `auth.log` volume mount, GID configuration, activation steps, end-to-end verification including synthetic log injection, and journald-only system notes.
- **CrowdSec operations runbook** (`docs/runbook.md`): day-to-day reference covering health checks for all three phases, monitoring and inspection commands, whitelisting (temporary and permanent), false positive investigation workflow, emergency procedures (clear all bans, disable individual phases, full stack disable), and maintenance (hub upgrades, engine version upgrades).
- **CrowdSec dashboard guidance** (`docs/dashboard.md`): documents the CrowdSec Console (opt-in hosted dashboard) — enrollment, verification, unenrollment, privacy implications, and tier limits. Includes a full CLI alternative table for operators who prefer to keep all data local. Prometheus/Grafana integration deferred to v0.8.0 Monitoring.
- **Geoblocking guidance** (`docs/geoblocking.md`): opt-in country-level blocking documented with explicit trade-offs. Covers GeoIP enrichment (already active via installed collections), Mechanism A (manual `cscli decisions add --scope Country`), Mechanism B (`crowdsecurity/countries-blacklist` scenario), Phase 2/3 interaction including SSH lockout risk, self-lockout prevention steps, and emergency reversal. No default country list provided.
- **AppSec tuning guidance** (`docs/appsec.md`): documents the request-level WAF layer — how it differs from scenario detection, current blueprint state (installed and disabled by default), active rule sets (`appsec-generic-rules`, `appsec-virtual-patching`), safe four-step enabling progression (verify reachability → enable fail-open → observe → optionally tighten), diagnosing AppSec blocks vs. IP bans, application-specific false-positive patterns for Nextcloud, Paperless-ngx, Authentik, WordPress, Seafile, and Invoice Ninja, exclusion mechanics and over-exclusion risks, and emergency disable.

---

## [0.5.1] — 2026-05-03

### Fixed

- **Nextcloud**: `app-internal` network was missing `internal: true` — database and Redis containers had unintended internet access despite being on an internal network
- **Seafile CE**: four sidecar images (`sdoc-server`, `notification-server`, `seafile-md-server`, `thumbnail-server`) had floating `major.minor-latest` tags — replaced with `__REPLACE_ME__` pending verified tag lookup
- **Immich**: removed `healthcheck: disable: false` on `machine-learning` and `app` containers — this is the default value and had no effect
- **README**: Quick Start secret generation commands used `secrets/` instead of `.secrets/`; missing `| tr -d '\n'` in `openssl` pipeline
- **README**: per-app layout diagram used `secrets/` instead of `.secrets/`
- **README**: "Passwords never in environment variables" claim softened — deviations (Zammad, Immich) are documented per app
- **security-baseline.md**: Hawser socket mount described as using a TCP proxy — clarified as a documented deviation; socket proxy remains the target once upstream supports it

### Changed

- **Tag pinning standard**: two-tier policy formalised — app images pinned to full digest or exact version; infrastructure images (DB, cache, proxy) pinned to `major.minor`
- **Zammad**: inline DB password documented as a known deviation — Zammad (Rails) does not support `_FILE` env vars
- **Portainer Agent**: added comment explaining the `/:/host:ro` full-filesystem mount
- **ROADMAP**: v0.7–v1.1 milestones added; continuous app-testing principle documented; image vulnerability scanning, secrets rotation guidance, and backup restore testing added to the pre-v1.0 and v0.7 scope

### Standards

- **maintenance.md**: ✅ Ready Criteria formalised as a 9-point checklist
- **maintenance.md**: `Last verified: YYYY-MM-DD (vX.Y.Z)` format standardised across all `UPSTREAM.md` files; all 10 live-tested apps updated

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

[Unreleased]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.4.0
[0.3.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.3.0
[0.2.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.2.0
[0.1.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.1.0
