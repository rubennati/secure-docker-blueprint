# AGENTS.md

## Purpose
This file is a routing index for AI agents and does not redefine project rules.
Existing repository documents remain the source of truth.

## Rule Precedence
1. `docs/standards/*.md`
2. `SECURITY.md`
3. `CONTRIBUTING.md`
4. `docs/maintenance.md`
5. `.github/pull_request_template.md`
6. `docs/architecture.md`

## Mandatory Start Documents
Read these first for any non-trivial task:
- `CONTRIBUTING.md`
- `SECURITY.md`
- `docs/standards/commit-rules.md`
- `docs/standards/documentation-workflow.md`
- `docs/standards/security-baseline.md`
- `docs/maintenance.md`

Conditional:
- If touching Traefik or routing/security middleware, also read `docs/standards/traefik-security.md`.

## Task Routing
- Commit, branch, and push behavior: `docs/standards/commit-rules.md`
- Required documentation updates when code changes: `docs/standards/documentation-workflow.md`
- Container hardening, secrets, socket access, and network isolation: `docs/standards/security-baseline.md`
- Traefik access policies, middleware chains, and TLS profiles: `docs/standards/traefik-security.md`
- Vulnerability reporting and disclosure process: `SECURITY.md`
- PR checklist and review readiness: `.github/pull_request_template.md`
- Architecture rationale and system model: `docs/architecture.md`
- Ongoing maintenance chains and owner/mirror mapping: `docs/maintenance.md`

## Conflict Rule
If guidance appears to conflict, follow the Rule Precedence order above.
Use `docs/maintenance.md` owner/mirror mapping to resolve which document owns a given fact.

## Tool-Specific Adapters
Tool-specific files (for example `CODEX.md`, `CLAUDE.md`) may be added later only as thin adapters that reference canonical documents, not as independent rule sources.
