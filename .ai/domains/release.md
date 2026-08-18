# Domain — Release

**Spec:** [`docs/maintenance.md`](../../docs/maintenance.md) Release Chain ·
[`ROADMAP.md`](../../ROADMAP.md)

## When a tag is set

Pre-1.0 tags mark a natural milestone, not a calendar date or a feature checklist.
A milestone is reached when the thing it names has been **proven**, not when it has
been written. Every release since v0.2.0 follows that rule.

Under 1.0, forks should expect snapshots rather than stability guarantees.

## Sequence

1. Run the Consistency Chain from `docs/maintenance.md`
2. All local gates clean — see [`quality-gates.md`](../quality-gates.md)
3. `CHANGELOG.md`: `[Unreleased]` → `[X.Y.Z]`, comparison links updated
4. `ROADMAP.md`: milestone moved to Shipped, "Last updated" bumped
5. `README.md`: version badge
6. `docs/maintenance-log.md`: add a row
7. Every `🚧` re-checked for honesty; every `✅` re-checked against dependency updates
8. Tag, then `gh release create vX.Y.0 --draft` for minor versions — patch versions
   are git tags only

## Merging to main

`dev` merges into `main` only after testing has passed. This is a deliberate step,
not a backlog to clear — `main` staying behind is not by itself a problem.

Agents do not merge to `main`, do not force-push, and do not change branch
protection.

## Version semantics

The version badge and `CHANGELOG.md` describe what has shipped. `ROADMAP.md`
describes direction and never duplicates the changelog. `LIFECYCLE.md` describes
per-stack evidence and is generated.
