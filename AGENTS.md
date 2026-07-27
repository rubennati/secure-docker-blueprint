# AGENTS.md

## Purpose
This file is a routing index for AI agents and does not redefine project rules.
Existing repository documents remain the source of truth.

## Start here
Before any non-trivial task, read the shared `.ai/` workspace:

1. `.ai/index.md` — start sequence and repository map
2. `.ai/state.md` — current phase, objective, open decisions, active constraints
3. `.ai/routing.md` — which documents this task type actually needs
4. `.ai/rules.md` — how to work here

`.ai/` coordinates work. It never overrides the documents listed under Rule Precedence.

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
This file is the source of truth for all AI tools. Tool-specific files exist only
because each tool reads its own path:

- `CLAUDE.md` — Claude Code
- `.github/copilot-instructions.md` — GitHub Copilot
- `.cursor/rules/00-project.mdc` — Cursor

Pointer files stay short (target: ≤20 lines) and defer to this file for any rule that
is not specific to the tool. Never duplicate a rule across pointer files — add it here
instead.

`CLAUDE.local.md` and `.claude/` are personal and gitignored; never commit them.
