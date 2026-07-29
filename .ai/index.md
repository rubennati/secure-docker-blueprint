# AI Workspace Index

Operational context for AI collaboration. Canonical rules live in the repository's
governance documents — this directory coordinates work, it does not redefine rules.

## Start sequence

1. [`../AGENTS.md`](../AGENTS.md) — rule precedence and mandatory reading
2. [`state.md`](state.md) — where the project is right now
3. [`routing.md`](routing.md) — which files this task actually needs
4. [`rules.md`](rules.md) — how to work here

## Core files

| Purpose | Files |
|---|---|
| Execution status | [`state.md`](state.md), [`tasks.md`](tasks.md), [`progress.md`](progress.md) |
| Governance memory | [`decisions.md`](decisions.md), [`quality-gates.md`](quality-gates.md) |
| Risk and failure tracking | [`risks.md`](risks.md), [`errors.md`](errors.md) |
| Working patterns | [`domains/`](domains/) |

## Repository map

`secure-docker-blueprint` is a security-focused Docker Compose blueprint for
self-hosted infrastructure. Five top-level categories, split by **how** each tool
accesses the system:

| Directory | Mandate |
|---|---|
| `core/` | Infrastructure every other service depends on — privileged |
| `apps/` | General-purpose self-hosted applications |
| `business/` | Applications that only make sense in a company context |
| `monitoring/` | Observability across the stack |
| `backup/` | Data protection across the stack — privileged |

Supporting: `docs/` (architecture, standards, maintenance, bugfixes, audits),
`scripts/ci/` (the checkers), `site/` (operator site), `.github/` (CI and templates).

## Canonical locations

- Standards: [`../docs/standards/`](../docs/standards/)
- Architecture rationale: [`../docs/architecture.md`](../docs/architecture.md)
- Process and owner/mirror map: [`../docs/maintenance.md`](../docs/maintenance.md)
- Status semantics: [`../docs/standards/status-model.md`](../docs/standards/status-model.md)
- Governance: [`../CONTRIBUTING.md`](../CONTRIBUTING.md), [`../SECURITY.md`](../SECURITY.md)
- App template: [`../apps/_reference/`](../apps/_reference/)
- Release history: [`../CHANGELOG.md`](../CHANGELOG.md) · Direction: [`../ROADMAP.md`](../ROADMAP.md)
- Per-stack lifecycle (generated): [`../LIFECYCLE.md`](../LIFECYCLE.md)
