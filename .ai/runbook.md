# AI Runbook (Non-Normative)

Use this as a minimal workflow index.
Canonical rules remain in repository governance and standards documents.

## Start Workflow (Minimal)

1. Read [`AGENTS.md`](../AGENTS.md) for precedence and routing.
2. Read only task-relevant files first (do not preload unrelated docs).
3. For code/config changes, route directly to the matching standards file(s).
4. Before proposing completion, verify expected checks for the touched scope.

## Task Routing by Type

- Commit/branch/push behavior: [`docs/standards/commit-rules.md`](../docs/standards/commit-rules.md)
- Documentation update requirements: [`docs/standards/documentation-workflow.md`](../docs/standards/documentation-workflow.md)
- Container/security baseline: [`docs/standards/security-baseline.md`](../docs/standards/security-baseline.md)
- Traefik access/middleware/TLS: [`docs/standards/traefik-security.md`](../docs/standards/traefik-security.md)
- Security disclosure/reporting: [`SECURITY.md`](../SECURITY.md)
- Contribution/PR expectations: [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`.github/pull_request_template.md`](../.github/pull_request_template.md)
- Architecture/process context: [`docs/architecture.md`](../docs/architecture.md), [`docs/maintenance.md`](../docs/maintenance.md)

## Validation / CI References

- CI workflow gates: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- Local checks/commands should follow the standards + CI expectations for the touched files.

## Documentation Sync Reminder

When behavior/config changes, update the relevant documentation in the same change set per [`docs/standards/documentation-workflow.md`](../docs/standards/documentation-workflow.md).
