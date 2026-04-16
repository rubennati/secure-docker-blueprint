# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also: [ROADMAP.md](ROADMAP.md) for what is coming next, and per-app CHANGELOGs where applicable.

## [Unreleased]

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

[Unreleased]: https://github.com/rubennati/secure-docker-blueprint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rubennati/secure-docker-blueprint/releases/tag/v0.1.0
