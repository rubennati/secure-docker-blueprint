# Repository Map (Non-Normative)

`secure-docker-blueprint` is a security-focused Docker Compose blueprint for self-hosted infrastructure.
It provides hardened, reusable service patterns across core infra, apps, business tools, and monitoring.
Canonical rules live in the main repository documents, not in this file.

## Top-Level Directory Map

- `core/` — shared infrastructure services (proxy, auth, security, platform components)
- `apps/` — general self-hosted application stacks
- `business/` — business-oriented application stacks
- `monitoring/` — observability and uptime tooling
- `backup/` — backup/recovery tooling and patterns
- `docs/` — architecture, standards, maintenance/process, templates, audits, bugfix notes
- `.github/` — CI workflow and collaboration templates
- `.claude/` — Claude-local tooling permissions/config

## Canonical Locations

- Standards: [`docs/standards/`](../docs/standards/)
- Architecture rationale: [`docs/architecture.md`](../docs/architecture.md)
- Process/maintenance chains: [`docs/maintenance.md`](../docs/maintenance.md)
- Contributor + security governance: [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`SECURITY.md`](../SECURITY.md)

## App Definitions

- Service definitions live in per-app/per-service `docker-compose.yml` files under:
  - [`core/`](../core/)
  - [`apps/`](../apps/)
  - [`business/`](../business/)
  - [`monitoring/`](../monitoring/)

## Templates and Collaboration Gates

- Document/templates: [`docs/templates/`](../docs/templates/)
- PR/Issue templates: [`.github/pull_request_template.md`](../.github/pull_request_template.md), [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/)
- CI gates: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

## Troubleshooting and History

- Troubleshooting patterns: [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md)
- Release history: [`CHANGELOG.md`](../CHANGELOG.md)
- Direction/planning: [`ROADMAP.md`](../ROADMAP.md)
