# Domain — Documentation

Use [`documentation-workflow.md`](../../docs/standards/documentation-workflow.md)
for purpose and maintenance, [`writing-style.md`](../../docs/standards/writing-style.md)
for wording, and the [File Map](../../docs/maintenance.md#file-map--single-source-of-truth)
for canonical sources. This summary owns no rule.

Update affected documentation in the same change set. Small corrections need no
purpose form, separate approval or session log. Record consequential decisions,
incidents and host evidence where they help future work.

| Document | Purpose |
|---|---|
| Root `README.md` | Project entry point and links to the inventories |
| Category `README.md` | Category scope and per-stack listing |
| Stack `README.md` | Setup, verification, operation, known limitations and recovery |
| Stack `UPSTREAM.md` | Source, licence, pins, upgrade notes and actual verification |
| `CHANGELOG.md` | Shipped changes |
| `ROADMAP.md` | Planned work |

Correct facts at their canonical source and regenerate affected views with their
scripts. Preserve `Last verified` through a pin update unless a new test actually
establishes a new record; see [`status-model.md`](../../docs/standards/status-model.md).

Use factual language, explain consequences and correct errors directly. Repository
content is English; discussion with the maintainer is German. Public records follow
[`Public content`](../../docs/standards/commit-rules.md#public-content). Link to
material available in a normal clone or to a public source.
