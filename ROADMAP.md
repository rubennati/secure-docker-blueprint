# Roadmap

Status reference point: 2026-04-16.

Update process: see [`docs/standards/documentation-workflow.md`](docs/standards/documentation-workflow.md).

## Completed

### Traefik Security Middleware Refactoring

Split into three dynamic config files for clarity:

- `security-blocks.yml` — reusable header, rate-limit, compression, CSP blocks
- `security-chains.yml` — 10 presets: `sec-0` through `sec-5` + `e` variants for iframe-friendly apps
- `integrations.yml` — CrowdSec bouncer plugin + Authentik forward auth middleware

Removed legacy `browserXssFilter` (deprecated header). Added `customFrameOptionsValue: SAMEORIGIN` for embed variants (Vaultwarden, OnlyOffice).

### Access Policies (IPv4 + IPv6)

Five access middleware defined in `access.yml`:

- `acc-public` — no restriction
- `acc-local` — RFC1918 + IPv6 ULA
- `acc-tailscale` — Tailscale CGNAT + IPv6 ULA range
- `acc-private` — LAN + Tailscale combined
- `acc-deny` — emergency kill switch

### TLS Profiles

Three profiles in `tls-profiles.yml`:

- `tls-basic` — TLS 1.2+ with default cipher selection
- `tls-aplus` — TLS 1.2+ with strict ECDHE ciphers, `X25519` preferred (SSL Labs A+)
- `tls-modern` — TLS 1.3 only

### CrowdSec Integration

Phase 1 (Engine) is live and tested. Phase 2 (Traefik Bouncer Plugin) is prepared in config files with a documented enable procedure — not activated by default to keep first-time setup simple.

| Phase | Component | Status |
|-------|-----------|--------|
| Phase 1 | Security Engine (`core/crowdsec/`) | Live |
| Phase 2 | Traefik Bouncer Plugin in `integrations.yml` | Ready to enable |
| Phase 3 | Firewall Bouncer (host nftables) | Planned — host-level install |

Phase 2 activation steps are documented in `core/crowdsec/README.md`.

### WordPress Hardening

Complete hardening layer:

- PHP security via `uploads.ini` — limits + `expose_php=Off` + `disable_functions`
- Apache `.htaccess-security` — blocks PHP in uploads, xmlrpc, author enumeration, directory listing
- `security-hardening.php` mu-plugin — blocks REST API user enum, removes generator fingerprints
- Test-script `ops/scripts/test-security.sh` — 24 automated security checks
- Three documented deployment scenarios (public admin / VPN admin / fully internal)

### Project Documentation

- Root `README.md` — value proposition, features, quick start, security model
- `SECURITY.md` — vulnerability reporting policy via GitHub Private Advisories
- `docs/standards/commit-rules.md` — branch model, commit conventions, push strategy
- `docs/standards/documentation-workflow.md` — doc update triggers, ownership, freshness rules
- `LICENSE` — Apache 2.0

---

## In Progress

### Coherence Audit Remediation

Self-audit on 2026-04-16 identified 32 action items across 7 work packages. See [`docs/audits/coherence-check-2026-04-16.md`](docs/audits/coherence-check-2026-04-16.md) for full findings and rationale.

Priority order:

1. **Cross-reference fixes** — add missing apps to README, fix `new-app-checklist` path reference, clean up ROADMAP references (~1h)
2. **Secrets folder standardization** — `./secrets/` → `./.secrets/` in 6 services (~30min)
3. **Service naming consistency** — `database` → `db` in 3 apps (~30min)
4. **Template corrections** — align `docs/templates/` with standards (~20min)
5. **Standards clarifications** — provider suffixes, secret generation, cross-references (~1h)
6. **Per-app documentation** — 7 missing READMEs, 6 missing UPSTREAMs, 6 missing `.gitignore`, 3 core READMEs (~4–6h)
7. **Compose fixes** — Invoice Ninja (non-compliant), Vaultwarden (entrypoint wrapper for DB secret), Hawser (missing fields) (~2h)

Packages run as independent commits on `dev`. Target: complete all 7 packages within two weeks of the audit.

### Paperless-ngx Security Hardening (Pilot for Implementation-Level Concept)

Pilot project for applying a structured hardening process to an existing app: gap analysis → user decisions → phased rollout → test-driven deployment.

Phases in planning (from audit result):

1. `PAPERLESS_ALLOWED_HOSTS` + `PAPERLESS_TRUSTED_PROXIES` (critical basics)
2. Explicit defaults: `ACCOUNT_ALLOW_SIGNUPS=false`, `AUDIT_LOG_ENABLED=true`
3. Session hardening + webhook SSRF protection
4. Remote user auth decision with documented exception handling
5. `/admin` panel protection via second Traefik router

Each phase is tested on the live server before the next begins.

### Admin Path Protection via Traefik

Pattern for restricting admin/backend URLs to VPN-only while keeping the public frontend open. Uses `PathPrefix` routing with separate middleware chains.

Status: implemented and documented for WordPress as one of the three scenarios in `apps/wordpress/README.md`. To generalize for other apps (Ghost, Paperless, Authentik admin).

---

## Evaluating

### Mutual TLS (mTLS) – Certificate-Based Access

Client certificate authentication as an additional access layer. Stronger than IP allowlists or passwords.

Use cases:

- API endpoints that only specific servers should reach
- Admin panels with hardware-bound authentication
- Zero-trust access without VPN dependency

Approach: Traefik TLS option with `clientAuth` requiring certificates signed by a custom CA. The `core/acme-certs` tool could be extended to also generate client certificates.

### Backup Strategy – Multi-Layer with Verification

Comprehensive backup concept covering all levels of the stack, with automated restore testing.

**Layer 1: Host-level** — Full system backup via restic or borgbackup, offsite target (S3, Backblaze B2, NFS)

**Layer 2: App-level** — Per-app backup scripts in `ops/scripts/backup.sh`, consistent snapshots (stop → dump → backup → start), standardized output to `./volumes/backups/`

**Layer 3: Database-level** — Automated `pg_dump` / `mysqldump` via sidecar or cron container, encrypted dumps

**Layer 4: Verification** — Automated restore tests on a schedule, checksum validation, alerting on failed backups

Open questions: single tool (restic?) or per-layer, central service or per-app scripts, secure secrets backup.

### IPv6 – Dual-Stack and IPv6-Only Setups

Full IPv6 support across the stack, including IPv6-only deployments.

Scope:

- Docker network configuration for dual-stack and IPv6-only
- Traefik entrypoints with IPv6 already supported
- Firewall rules (nftables) covering both protocols
- Per-app testing for IPv6-only operation
- NAT64/DNS64 for IPv6-only connecting to IPv4 services

### Container Resource Management

Define resource limiting strategy to prevent single containers from taking down the host.

Scope:

- CPU limits and reservations
- Memory limits and reservations
- PIDs limit (prevent fork bombs)
- I/O throttling for disk-heavy services
- Hardware-aware profiles vs. percentage-based

Goal: No single container can consume 100% CPU or RAM. OOM kills the container, not the host.

### Docker Rootless Mode

Evaluate running Docker in rootless mode for improved host security.

Current state: Docker rootless is functional but has known limitations — not all apps work, volume permissions, port binding, network modes may need adjustment.

Evaluation goals:

- Test each app for rootless compatibility
- Document works / workarounds / incompatible
- Decide: optional alternative or future default

### Centralized Observability

Logging and metrics aggregation for all services:

- Log forwarding (Loki/Promtail) for Traefik access logs, app logs
- Metrics (Prometheus) for Traefik, CrowdSec, app-specific exporters
- Grafana dashboard for quick overview
- Alerting (Alertmanager or direct webhooks)

Open: scope — full observability stack or minimal logging-only?

---

## Planned Community Infrastructure

These are GitHub-repo-level additions, not code changes. Tracked in `docs/public-go-live-guide.md` (private).

- `CONTRIBUTING.md` — contribution guide
- `CODE_OF_CONDUCT.md` — Contributor Covenant
- `CHANGELOG.md` — versioned change log
- `.github/ISSUE_TEMPLATE/` — bug, feature, new app templates
- `.github/pull_request_template.md`
- `CODEOWNERS`
- Minimal GitHub Actions — compose validate, markdown lint, secret scan

---

## Ideas

### Alternative Container Runtimes

Long-term considerations beyond standard Docker:

- **Podman** — daemonless, rootless by default, Docker CLI compatible. How well does it work with Traefik, Compose, and the socket proxy pattern?
- **Docker Swarm** — built-in orchestration for multi-node setups. Adds service discovery, rolling updates, secrets management.
- **Kubernetes (K3s)** — full container orchestration. Major architectural shift — Helm charts instead of Compose files. Only relevant at scale.

The current Docker Compose approach covers single-host and small-scale deployments well.

### MCP Connectors for Apps

Expose selected apps via MCP (Model Context Protocol) for AI-assisted operation. Candidates: Paperless-ngx document search, Vaultwarden secret retrieval, Invoice Ninja invoice creation.

Scope: blueprint defines the pattern, individual MCP servers developed in separate repos.

### Deploy Script

Long-term vision: `./deploy.sh <server> core/traefik apps/nextcloud` — rsync selected app directories to a server, no git/docs/inbox on target. Enables portable app deployments without the full blueprint repo on each target.
