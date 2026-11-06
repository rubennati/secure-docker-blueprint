# AGENTS.md

## Start here

Read the files needed for the requested task. Use [`.ai/routing.md`](.ai/routing.md)
when the relevant sources are unclear; read [`.ai/state.md`](.ai/state.md) for
ongoing work or release context. There is no repository-wide mandatory reading list.

## Working rules

- Complete the authorized task and run the checks relevant to the change.
- Preserve existing work. Do not include unrelated edits or expand the task silently.
- Follow the authorization and evidence guidance in [`.ai/rules.md`](.ai/rules.md).
- Commit and publish only within the user's authorization; the details are in
  [`commit-rules.md`](docs/standards/commit-rules.md).
- Protect credentials and private deployment data; follow
  [`Public content`](docs/standards/commit-rules.md#public-content).
- Report what was checked, what failed, and what remains unverified. A pin change
  or a static check is not a new host-verification record.

## Requirements and recommendations

Security requirements and technical prerequisites are binding within their scope.
Recommendations guide implementation; optional practices do not become blockers
because a tool or a local setting happens to enable them. Explain a material
trade-off instead of inventing a new requirement.

## Rule precedence

The user's explicit instructions and agreed scope take precedence over repository
workflow preferences. For repository requirements, use:

1. `docs/standards/*.md`
2. `SECURITY.md`
3. `CONTRIBUTING.md`
4. `docs/maintenance.md`
5. `.github/pull_request_template.md`
6. `docs/architecture.md`

The [File Map](docs/maintenance.md#file-map--single-source-of-truth) identifies
canonical sources. `.ai/` summaries and dated audits provide context; they do not
override current standards. Report a consequential contradiction and resolve it at
its source rather than silently choosing a convenient rule.

## Tool-specific adapters

`CLAUDE.md`, `.github/copilot-instructions.md` and `.cursor/rules/00-project.mdc`
point here. Keep shared instructions here or at their canonical source.
`CLAUDE.local.md` and `.claude/` are personal and gitignored; never commit them.
