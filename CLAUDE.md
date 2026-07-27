# Claude Code Notes

This file is a thin pointer. The source of truth for all AI tools is [`AGENTS.md`](AGENTS.md) at the project root.

Start every non-trivial task with the shared `.ai/` workspace:

- [`.ai/index.md`](.ai/index.md) — start sequence
- [`.ai/state.md`](.ai/state.md) — current phase, objective, open decisions
- [`.ai/routing.md`](.ai/routing.md) — which files to read for this task type

`AGENTS.md` defines rule precedence and the mandatory reading list. Commit, branch
and push behaviour is binding and lives in
[`docs/standards/commit-rules.md`](docs/standards/commit-rules.md) — read it before
committing anything.
