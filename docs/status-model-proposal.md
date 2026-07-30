# Status model — what it measures, and what a reader needs

**Decided 2026-07-30: A + C in the repository, B on the site.** The analysis
below is what the decision rests on. What has been applied, and what has not, is
recorded at the end.

`docs/standards/status-model.md` defines two axes and assigns owners. It was
written to end a real defect: three files carried independent status and twelve
services disagreed with themselves. It solved that.

This asks the question that was not asked at the time: whether the symbol
measures something a reader can use.

---

## The decision a reader actually makes

The root README states the approach:

> The blueprint takes a **choice-matrix** approach: where several tools compete
> (dashboards, photo galleries, wikis, form builders), multiple options are
> included so you can test and pick what fits.

So the reader's decision is *which of these*. Measured across the seven
categories that offer more than one candidate:

| Category | Candidates | Status values |
|---|---|---|
| Dashboards & launchers | 4 | ✅ only |
| Photo galleries | 5 | 🚧 only |
| Scheduling & booking | 2 | ✅ only |
| Publishing & knowledge | 3 | ✅ 🚧 |
| Productivity & personal | 4 | ✅ 🚧 |
| File sync & documents | 4 | ✅ 🚧 |
| Developer & admin tools | 26 | ✅ 🚧 |

In three of seven, every candidate carries the same symbol. The column is
constant where the choice is, so it does not inform the choice.

Where it does vary, it separates *checked* from *not yet checked*. Dashy and
Homarr are both ✅; nothing in the status says which suits a given deployment.
The Description column carries that.

## What the symbol measures

Maintainer progress. `✅ ready` is defined as clean install, core function,
security baseline, documentation — the bar for shipping anything at all. A
configuration in this repository that does not meet it is unfinished, not
different.

The distribution follows from that:

| Symbol | Stacks |
|---|---|
| ✅ ready | 21 |
| 🚧 preview | 38 |

Thirty-eight of fifty-nine tell the reader "the blueprint does not vouch for
this" — on a repository whose entire content is those configurations. The
dominant signal on the front page is the maintainer's backlog.

`✅` also carries an instruction the blueprint cannot support: *Deploy it.* The
repository does not know the deployment.

## A second defect, found while checking this

In `monitoring/README.md`, `✅` means `ready` in the legend on line 7 and
"feature present" in the comparison table on lines 95–99. One glyph, two
meanings, one file.

## The surface problem

`status-model.md` splits by question:

- line 16 — public axis: *"what the README tables show"*
- line 31 — internal axis: *"lives in `LIFECYCLE.md`"*

Both files are in the repository. `site/src/components/StackStatus.astro` renders
`entry.public` — the same axis the README already shows.

The result is that the repository carries both views and the site carries a copy
of one of them. 105 of 410 lines in the root README are status tables, addressed
to the operator the site exists to serve. There is no surface that carries the
maintainer view alone.

## Where the symbol appears

Changing it touches:

| Surface | Extent |
|---|---|
| root `README.md` | 105 table lines |
| `business/`, `monitoring/`, `backup/` READMEs | one table each, plus a legend |
| `LIFECYCLE.md` | generated, 59 rows |
| `site/src/components/StackStatus.astro` | one badge, used on every stack page |
| `site/src/content/docs/faq/` | the label explanation |
| `scripts/ci/lifecycle-report.py` | owner map, `--check` |
| `scripts/ci/check-coverage.py` | counts a stack as covered when lifecycle enumerates it |

---

## Option A — split by surface, keep the vocabulary

The repository carries what a maintainer needs: verified against which version,
on which date, which deviations from upstream, what remains. The site carries
the reader's view, which is where the badge already renders.

The root README keeps the catalogue — name, stack shape, description, link — and
drops the status column.

**Cost:** moderate. The owner map in `lifecycle-report.py` moves from the README
tables to `UPSTREAM.md`, which already holds `Last verified: DATE (vX.Y.Z)` for
every stack. Category READMEs lose a column. The site is unaffected.

**What it fixes:** the duplication, and the repository doing the site's job.

**What it does not fix:** the symbol still measures maintainer progress. Four
dashboards still land on the same value. Relocating it does not make it
discriminate.

## Option B — replace the tier with the facts

No four-step symbol. Per stack, the facts a reader can weigh:

| Fact | Already exists in |
|---|---|
| verified against version X on date Y | `UPSTREAM.md` |
| licence and origin | `UPSTREAM.md`, generated into `sovereignty.json` |
| deviations from upstream, with reasons | `UPSTREAM.md` |
| backup and restore documentation | read by `lifecycle-report.py` |
| what is proven versus assumed | the shape used in `docs/sovereignty/data-egress.md` |

Every one of these is already recorded. None needs a new judgement.

**Cost:** the largest. Every surface in the table above, plus `status-model.md`
itself, plus the FAQ page that explains the labels.

**What it fixes:** a reader gets facts with dates instead of a verdict. Nothing
claims fitness on the reader's behalf.

**What it costs beyond work:** a date is harder to scan than a symbol. Someone
comparing twenty stacks at a glance loses that glance.

## Option C — keep the tier, redefine what it measures

Rewrite the tiers around evidence depth rather than maintainer progress — for
example: configured / run by the maintainer / run with real data / restored from
backup.

**Cost:** moderate. Vocabulary and the mapping table change; the surfaces stay.

**What it does not fix:** the choice-matrix case. Four dashboards the maintainer
ran once still land on the same tier.

---

## Recommendation

**A, then B.** A is the smaller change and fixes the defect that is provable
today — two surfaces carrying the same axis, and the repository front page
addressed to the site's audience.

A does not make the symbol useful, and this document should not pretend
otherwise. B is what addresses the reader's decision, and it is easier to do
once the surfaces are separated, because after A the symbol has one home instead
of three.

C is not recommended. It costs about as much as A and leaves the case that
prompted this — a category where every candidate carries the same value —
exactly where it is.

## Open for the maintainer

1. Whether the root README keeps a status column at all after A.
2. Whether `🛡️ ops-ready` survives. It is currently held by nothing, and the
   restore that would earn it was performed on 2026-07-29 and recorded in
   `backup/borgmatic/RESTORE.md` but not at its owner.
3. Whether the site's badge stays a symbol or becomes the date and version.

---

## Decision and state, 2026-07-30

The repository keeps one lifecycle, for a maintainer. Operator-facing promises
leave it. The site carries evidence and named gaps instead of a badge.

**Applied:**

- `docs/standards/status-model.md` rewritten. One lifecycle, four states, each
  measured from an artefact. The public axis and its promises are gone.
- `scripts/ci/lifecycle-report.py` measures the state instead of reading a
  symbol back. It reads the verification anchor from `UPSTREAM.md`, baseline
  alignment from the two checkers' exit codes, and restore evidence from the
  rehearsal log.
- `backup/borgmatic/RESTORE.md` gained a `Stack` column, which is what makes the
  rehearsal log machine-readable. `apps/nextcloud` reached `ops-proven` from it
  without anyone typing a status.
- Root README and the three category READMEs lost their status columns and
  legends — 144 table rows.
- `StackStatus.astro` replaced by `StackEvidence.astro`. The site states what was
  verified, against which version, whether data was restored, and one authored
  sentence naming what was not exercised. No tier vocabulary reaches it.

**Measured against the previous hand-typed symbols:** nothing fell.
`apps/nextcloud` and `business/invoiceninja` rose, both verified on a live host
on 2026-07-29 while their symbols still said preview.

**Not yet applied:**

- 50 stack READMEs still carry their own `**Status:**` line in the retired
  vocabulary. 28 hold only status, version and date; 22 also carry information
  worth keeping, such as an upgrade warning.
- `ROADMAP.md`, `docs/maintenance.md` and the two host-session documents still
  name the retired tiers.
- The choice matrices remain in the root README. Moving selection guidance to
  the site is part of the target picture and has not started.
