# Roadmap

Last updated: 2026-04-16.

This document is the single source of truth for project direction. Updated as part of every meaningful commit that completes, starts, or reprioritises a work item — never batch-updated retroactively. Update rules: see [`docs/standards/documentation-workflow.md`](docs/standards/documentation-workflow.md).

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

### Per-App Documentation Pass (Coherence Audit Package 6)

Brought every app and core component in line with blueprint standards:

- `apps/` (10): dockhand, portainer, whoami (core), ghost, nextcloud, seafile, calcom, paperless-ngx — each with README + UPSTREAM + .gitignore + style alignment
- `core/` (3): onlyoffice, traefik, authentik — same pattern
- Style consistency: `APP_TAG`/`DB_TAG` pattern, `TZ` (not `TIMEZONE`), `TRAEFIK_NETWORK` variable, `${COMPOSE_PROJECT_NAME}-*` container names, grouped Traefik labels
- `TIMEZONE` → `TZ` migration completed across the apps touched

Invoice Ninja, Vaultwarden, Hawser remain for Package 7 (Compose fixes) — see In Progress.

### CONFIG.md Artifact (blueprint v2)

Added a mandatory per-app configuration reference file alongside `README.md` and `UPSTREAM.md`. Every config option is bucketed into:

- **Mandatory** — every production instance sets this
- **Nice-to-have** — recommended default
- **Use-case-dependent** — only with a named trigger

Deliverables:
- `docs/app-setup-blueprint.md` v2 on `docs` branch — new Section 2.8 defines the template, buckets, table formats, and sub-structure by app size. v1 archived as `app-setup-blueprint-v1.md`.
- `apps/paperless-ngx/CONFIG.md` on `dev` — reference instance for large-app setup, covering all Paperless env vars, backup lifecycle, management commands, and extensions.

---

## In Progress

### Coherence Audit Remediation

Self-audit on 2026-04-16 identified 32 action items across 7 work packages. See [`docs/audits/coherence-check-2026-04-16.md`](docs/audits/coherence-check-2026-04-16.md) for full findings and rationale.

Progress:

1. ✅ **Cross-reference fixes** — done
2. ✅ **Secrets folder standardization** (`./secrets/` → `./.secrets/`) — done
3. ✅ **Service naming consistency** (`database` → `db`) — done
4. ✅ **Template corrections** — done
5. ✅ **Standards clarifications** — done
6. ✅ **Per-app documentation** — done (see Completed)
7. ⏳ **Compose fixes** — pending: Invoice Ninja (non-compliant), Vaultwarden (entrypoint wrapper for DB secret), Hawser (missing fields). Est. ~2h.

Only Package 7 remains.

### Paperless-ngx Security Hardening (Pilot for CONFIG.md Approach)

Pilot for the CONFIG.md artifact: structured hardening of an existing app via gap-analysis → bucket decisions → phased rollout → test-driven deployment.

**Phases 0–3 done** — gap analysis and bucket decisions consolidated in [`apps/paperless-ngx/CONFIG.md`](apps/paperless-ngx/CONFIG.md). All ~140 Paperless env vars catalogued, backup lifecycle documented, management commands listed.

**Phase 4: Mandatory env rollout** — 8 open action items from CONFIG.md Quick-Summary, planned as separate commits with live tests between each:

1. `PAPERLESS_ALLOWED_HOSTS` — default `*` leaves host-header injection window open
2. `PAPERLESS_TRUSTED_PROXIES` — without it the audit log sees only Traefik's IP
3. `PAPERLESS_URL` — explicit setter that covers ALLOWED_HOSTS / CORS / CSRF in one place
4. `PAPERLESS_USE_X_FORWARD_HOST` + `USE_X_FORWARD_PORT` + `PROXY_SSL_HEADER` — Django-side trust for Traefik-set proxy headers (currently half-wired)
5. `PAPERLESS_ACCOUNT_ALLOW_SIGNUPS=false` — explicit instead of implicit default
6. `PAPERLESS_EMPTY_TRASH_DELAY=30` — explicit for compliance relevance
7. Automated backup via `document_exporter` + scheduled cron — currently missing
8. DB upgrade playbook (Paperless major + PostgreSQL major) — currently blank

**Phase 5: `/admin` panel protection** — second Traefik router with `acc-tailscale` for Django admin (bypasses MFA/SSO otherwise). Cross-reference: generalisable pattern, see Admin Path Protection below.

**Phase 6: Extensions** — setup at least one of paperless-gpt / paperless-ai / paperless-mcp as its own app under `apps/`. Template for paperless-mcp already exists in `inbox/Archiv/paperless-mcp/`. Open decision: which extension first, conflict-avoidance strategy if multiple auto-taggers are used.

Each phase is tested on the live server before the next begins.

### Admin Path Protection via Traefik

Pattern for restricting admin/backend URLs to VPN-only while keeping the public frontend open. Uses `PathPrefix` routing with separate middleware chains.

Status: implemented and documented for WordPress as one of the three scenarios in `apps/wordpress/README.md`. To generalize for other apps (Ghost, Paperless, Authentik admin).

---

## Evaluating

### Secret & Password Generation Standard

Blueprint-weite Policy für das Erzeugen von Secrets (maschinell, in `.secrets/` Dateien) und Passwörtern (für menschliche Admin-Accounts). Aktuell hat jeder App-README sein eigenes Rezept, teilweise mit bekannten Fallstricken.

#### Bekannte Problem-Klassen

- **Padding-Konflikte**: `openssl rand -base64` liefert `+/=` — bricht DATABASE_URLs, Shell-Contexts, einige App-Parser
- **Trailing-Newline-Trap**: Jeder App-README predigt `| tr -d '\n'` — fehlt es einmal, schlägt Auth stumm fehl
- **Char-Set-Konflikte pro App**: Cal.com CALENDSO_ENCRYPTION_KEY muss **32-char hex** sein (`-base64` bricht), Nextcloud Redis-Password muss ohne `+/=` sein (PHP-URL-Parser), Paperless DB-Password über `DATABASE_URL` inline
- **Länge pro App unterschiedlich**: JWT ≥48 Byte, DB-Passwort 32, Session-Secret wieder anders — Kapsel-Wissen verteilt über Repos

#### Interim-Workarounds (nutzen wir heute uneinheitlich)

- `openssl rand -hex 32` für URL-eingebettete Passwörter (DATABASE_URL, REDIS_URL)
- `openssl rand -base64 48` produziert 64 Chars ohne Padding
- `openssl rand -base64 32 | tr -d '=\n'` strippt Padding aber Länge variiert
- `tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32` — pure alphanumerisch

#### Offene Entscheidungen

**Policy-Seite:**
- Eine universelle Konvention oder Use-Case-spezifische Regeln in `docs/standards/env-structure.md`?
- Entropy-Floor als Minimum (128 / 192 / 256 bits)?
- Sollen Admin-Passwörter für menschliche Nutzung (typbar, memorable) anders behandelt werden als Service-Secrets?

**Tool-Seite:**
- Helper-Script auf Repo-Ebene (`scripts/generate-secret.sh`) — welche Signatur? Nur Length-Argument, oder Format-Argument (`--format hex|base64|alphanum|urlsafe`)?
- Integration mit `.env.example`: auto-populate beim ersten `docker compose up` via Entrypoint-Hook?
- Wie umgehen mit Apps ohne `_FILE`-Support die das Passwort inline in URLs brauchen (Calcom `DB_PWD_INLINE`, Seafile entrypoint-Wrapper, Ghost `__file` suffix)? Ein Script reicht nicht — braucht abgestimmte Patterns.

**Konsistenz-Seite:**
- Aktuelle App-READMEs zeigen uneinheitliche Befehle — nachträglich angleichen wenn Policy steht
- Paperless Known-Issue "Trailing newlines break auth" sollte durch die Policy strukturell vermieden werden, nicht nur warnend dokumentiert

#### Ziel

Ein Blueprint-weites Set von **Generierungs-Patterns** (zwei oder drei, je nach Use-Case) plus **ein minimales Tool** das sie umsetzt. Alle App-READMEs referenzieren dann den Standard statt eigene Rezepte zu haben. Fallstricke wie Newline-Trap und Padding-Konflikte werden strukturell eliminiert, nicht nur dokumentiert.

Entscheidungen werden in `docs/standards/secrets-and-passwords.md` (neu) verankert, sobald getroffen.

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

Reference material: `inbox/traefik-rootless/` contains an early-draft Traefik v3.3 rootless compose variant (standard + rootless-socket side-by-side, plus README). Starting point for a future `core/traefik/docker-compose.rootless.yml` overlay once the path is confirmed.

### Centralized Observability

Logging and metrics aggregation for all services:

- Log forwarding (Loki/Promtail) for Traefik access logs, app logs
- Metrics (Prometheus) for Traefik, CrowdSec, app-specific exporters
- Grafana dashboard for quick overview
- Alerting (Alertmanager or direct webhooks)

Open: scope — full observability stack or minimal logging-only?

---

## Planned Community Infrastructure

These are GitHub-repo-level additions, not code changes.

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

Concrete: `paperless-mcp` template already exists in `inbox/Archiv/paperless-mcp/` (complete with build Dockerfile, compose file, entrypoint wrapper). Ready to move into `apps/` when activated — see Paperless-ngx Phase 6 in In Progress.

### Deploy Script

Long-term vision: `./deploy.sh <server> core/traefik apps/nextcloud` — rsync selected app directories to a server, no git/docs/inbox on target. Enables portable app deployments without the full blueprint repo on each target.
