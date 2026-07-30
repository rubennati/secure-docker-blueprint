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

## Documentation — hard rules

Applies to every change that writes or edits documentation. These are pointers to
rules defined elsewhere, not a second definition of them.

1. **Before writing**, name the reader, the document purpose, the section objective and what is explicitly out of scope — [preflight](docs/standards/documentation-workflow.md#before-drafting-the-purpose-preflight).
2. **Include only what helps** the reader act, decide, verify, diagnose, or understand a dependency they need.
3. **Correct is not relevant.** A correct sentence in the wrong context is a documentation defect.
4. **One canonical owner per changing fact** — [File Map](docs/maintenance.md#file-map--single-source-of-truth). Other files use, summarise, reference or generate it for their own purpose; a second independent version is prohibited.
5. **Keep current state, planned work and history apart** — `ROADMAP.md`, `CHANGELOG.md`, `docs/bugfixes/`, `docs/audits/` and `.ai/` each own their part.
6. **State the consequence for the reader**, not the author's reasoning or how the result was reached.
7. **Register follows the section purpose** — imperative where the reader performs steps, declarative where they establish what is true. No global language rule overrides it: [address and mood](docs/standards/writing-style.md#address-and-mood).
8. **Check what changed** — the [relevance test](docs/standards/documentation-workflow.md#the-relevance-test) per paragraph, then the checks in [`.ai/quality-gates.md`](.ai/quality-gates.md).

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
- `docs/standards/writing-style.md`
- `docs/standards/security-baseline.md`
- `docs/maintenance.md`

The three that own documentation are `documentation-workflow.md` (purpose,
readers, section contracts, relevance, ownership modes, update rules),
`writing-style.md` (register and wording) and `docs/maintenance.md` (File Map —
which source owns a changing fact, and who keeps each file current).

Conditional:

- If touching Traefik or routing/security middleware, also read `docs/standards/traefik-security.md`.

## Task Routing

- Commit, branch, and push behavior: `docs/standards/commit-rules.md`
- Documentation purpose, relevance, ownership modes and update rules: `docs/standards/documentation-workflow.md`
- How documentation reads — register, address, the seven forms: `docs/standards/writing-style.md`
- Container hardening, secrets, socket access, and network isolation: `docs/standards/security-baseline.md`
- Traefik access policies, middleware chains, and TLS profiles: `docs/standards/traefik-security.md`
- Vulnerability reporting and disclosure process: `SECURITY.md`
- PR checklist and review readiness: `.github/pull_request_template.md`
- Architecture rationale and system model: `docs/architecture.md`
- Ongoing maintenance chains and owner/mirror mapping: `docs/maintenance.md`
- Licence, jurisdiction, outbound calls, and what a CDN changes: `docs/sovereignty/`

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
