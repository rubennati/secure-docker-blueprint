# Domain — Release

**Spec:** [`docs/maintenance.md`](../../docs/maintenance.md) Release Chain ·
[`ROADMAP.md`](../../ROADMAP.md)

## When a tag is set

- **Minor (`v0.Y.0`):** a milestone of `ROADMAP.md`, reached when the thing it names
  has been **proven**, not when it has been written.
- **Patch (`v0.Y.Z`):** the result of a monthly maintenance round or an out-of-turn
  security fix that changed something an operator would take
  ([`docs/maintenance.md`](../../docs/maintenance.md#maintenance-round)). A month in
  which nothing relevant changed has no tag.
- **Who:** the maintainer sets every tag. An agent proposes one only with its reason —
  a round has merged, an out-of-turn fix has merged, a milestone is reached — and
  never after every pull request.

Under 1.0, forks should expect snapshots rather than stability guarantees.

**v1.0.0 has a second gate: the operator site.** It is not tagged while
the operator site is unfinished, and being live is not the same as being
finished. Criteria for both surfaces:
[`ROADMAP.md`](../../ROADMAP.md#v10--complete-and-hand-off-ready). Site publishing
itself stays unversioned — this gate constrains the tag, not the content.

## Sequence

1. Run the Consistency Chain from `docs/maintenance.md`
2. All local gates clean — see [`quality-gates.md`](../quality-gates.md)
3. `CHANGELOG.md`: `[Unreleased]` → `[X.Y.Z]`, comparison links updated
4. `ROADMAP.md`: shipped items removed from the open lists
5. `README.md`: version badge
6. Record significant release verification in the relevant host or maintenance record, when new evidence exists
7. Every stack in [`docs/in-use.md`](../../docs/in-use.md) checked as of the round's
   cut-off — new version, security fix, breaking change, lab upgrade test — with the
   version and the date; a later upstream release waits for the next round
8. `upstream-status.json` and `LIFECYCLE.md` from the round's scan, refreshed only when
   the tag comes more than a week later; the stacks whose pin moved past their tested
   version read for likely breakage
9. Secret scan by dispatch on `dev`
10. Tag, then `gh release create vX.Y.Z --draft` with the tag's `CHANGELOG.md` section
11. After the release pull request is merged, `main` back into `dev` through a pull
    request

## Merging to main

`dev` merges into `main` only as a release, after testing has passed. This is a
deliberate step, not a backlog to clear — `main` staying behind is not by itself a
problem. The one other way into `main` is a Dependabot security pull request: GitHub
raises those against the default branch only.

Agents do not merge to `main`, do not force-push, and do not change branch
protection.

## Version semantics

The version badge and `CHANGELOG.md` describe what has shipped. `ROADMAP.md`
describes direction and never duplicates the changelog. `LIFECYCLE.md` describes
per-stack evidence and is generated.
