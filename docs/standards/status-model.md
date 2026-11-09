# Status Model

A stack carries no state. The repository shows facts about it, each read from one
artefact, and leaves the conclusion to the reader. The first reader is whoever is
about to install or update a stack; the maintainer deciding what to work on next
is the second.

No fact is a grade, and nothing falls. A pin move changes the pin and nothing
else: the date of the last test stays, and the version that was tested appears
beside it.

---

## What a stack shows

One row per stack, in [`LIFECYCLE.md`](../../LIFECYCLE.md) and in the site
catalogue, both generated from the same source.

| Column | Shows | Read from |
|---|---|---|
| **Stack** | the name, linked to the stack folder | the stack directory |
| **Pin** | the pinned version of the primary image, and the date upstream released it | `<stack>/.env.example`; the date from `upstream-status.json` |
| **Newest** | the newest stable release, or the newest LTS release where upstream names one, and its date; `= Pin` when the pin is the newest; the date upstream was checked; ⚠️ when the upstream repository is archived or has published no release for twelve months | `upstream-status.json` |
| **Findings** | CRITICAL and HIGH findings across every image of the stack, at the current pin | `upstream-status.json` |
| **Last tested** | the date of the last run on a host; `with restore` when a backup of its data was restored; the tested version, only where it differs from the pin | `Last verified:` in `<stack>/UPSTREAM.md`; the rehearsal log of [`backup/borgmatic/RESTORE.md`](../../backup/borgmatic/RESTORE.md#rehearsal-log) |

Everything else is in the stack folder, which is the detail page:

- `README.md` — what the stack is, how it is set up, backup and restore, and
  `## Open findings`: every CRITICAL and HIGH finding at the current pin, the
  list generated from the scan, a reason written by hand where a finding is left
  in place on purpose
- `UPSTREAM.md` — the upstream sources, the `Last verified` line with what the run
  established, the notes of each version move
- `docker-compose.local.yml`, where the stack has a local test variant

## Rules

- **Every fact has one artefact.** Nothing is typed into a table; a table is
  generated or it does not exist.
- **A test date belongs to the run.** A run on a host checks the setup — the
  routing, TLS, the hardening, a restart, a restore, the application's own
  function the README names. A later pin move neither erases the date nor
  establishes a new one; the reader sees both the pin and the version that ran.
- **Release dates come from upstream releases,** not from the registry: an image
  tag is rebuilt and pushed again, and its push date says nothing about the
  release. They are read from the first GitHub repository in the `## Source`
  section of `UPSTREAM.md`, or from the one a `**Releases:**` line there names,
  where an image's versions are released elsewhere than its source.
- **Newest means the same kind of tag as the pin.** A tag that cannot be compared
  is shown as not determinable, never as current.
- **Upstream data is written into the repository** at every pin move and before
  every release, by `scripts/ci/upstream-status.py`, with the date it was checked.
  Between those, the weekly issue labelled `stack-status` is the early warning
  ([DEC-079](../../.ai/decisions.md#dec-079)).
- **A finding is information.** It fails no job
  ([DEC-079](../../.ai/decisions.md#dec-079)); it is fixed by moving the pin or
  recorded with a reason.
- **The security baseline is not a column.** `check-baseline.py` and
  `check-structure.py` enforce it for every stack; a stack that breaks it fails CI.
- **No test date means not run on a host yet.** For a blueprint that is the
  ordinary case and needs no sentence. Where something particular stands in the
  way — a GPU, port 25 and public DNS, an archived upstream — the stack's
  `UPSTREAM.md` names it (`Last verified: not yet — reason`), and the reason
  appears in the row.

## Who owns which fact

Every fact has one owner. Everything else derives from it. When two files
disagree, the owner wins, and the derived file was generated from stale input.

| Fact | Owner |
|---|---|
| Pinned image version | `<stack>/.env.example`; for a host-installed component, which has none, `Based on version` in its `UPSTREAM.md` |
| Upstream release dates, newest release, archived or quiet upstream, findings at the pin | `upstream-status.json`, written by `scripts/ci/upstream-status.py` |
| Last test date and version, and what the run established | `<stack>/UPSTREAM.md`, `Last verified` |
| What stands in the way of a host run, where something particular does | `<stack>/UPSTREAM.md` |
| Restore evidence | `backup/borgmatic/RESTORE.md`, rehearsal log |
| Reasons for findings left in place | `<stack>/README.md`, `## Open findings`; the exceptions in `.trivy-baseline.json` |
| Security baseline alignment | `<stack>/docker-compose.yml`, checked by `check-baseline.py` and `check-structure.py` |
| Backup and restore documentation | `<stack>/README.md` |

Restore evidence sits in the rehearsal log because that is where it is produced:
the log records the archive, the scope, the result and the numbers. The log's
`Stack` column names the repository key, which is what makes it machine-readable.

## LIFECYCLE.md is generated

`scripts/ci/lifecycle-report.py` produces [`LIFECYCLE.md`](../../LIFECYCLE.md),
`site/src/data/lifecycle.json` and the findings block under `## Open findings` in
each stack README; `scripts/ci/site-catalogue.py` reads the same facts for the
catalogue. **None of them is edited by hand** — the text around the findings
block is.

```bash
python3 scripts/ci/lifecycle-report.py --write
```

A generated file cannot drift: either it is current, or CI fails because it is
not.

## What CI enforces

`lifecycle-report.py --check` fails when:

- `LIFECYCLE.md` or `lifecycle.json` is out of date with respect to its sources
- the rehearsal log, an exception in `.trivy-baseline.json` or
  `upstream-status.json` names a stack that does not exist

A stack without `UPSTREAM.md` is reported by `check-structure.py` (`missing-file`).

It also fails when a findings block in a stack README differs from
`upstream-status.json`, and when a stack has findings at its pin or a recorded
exception and its README has no `## Open findings` section.

It reports without failing when a stack still carries the pre-v0.5.1
`Last checked: DATE` field, which names no version (`legacy-stamp`), and when
`upstream-status.json` was written for another pin (`not-checked`).

## Why there are no states

The first model typed status symbols into README tables
([DEC-009](../../.ai/decisions.md#dec-009)); they drifted apart. The second
measured four states from artefacts — `scaffolded`, `verified`,
`baseline-aligned`, `ops-proven` ([DEC-066](../../.ai/decisions.md#dec-066)).
Measurement stopped the drift, but the states still named what the maintainer had
done, not what a reader can rely on, and they read like certificates a blueprint
cannot issue. A state held only at the exact pin it was tested at, so the pin
round of 2026-11-05 moved the count of `ops-proven` stacks from 14 to 2 without a
single stack changing except its pins.
[DEC-080](../../.ai/decisions.md#dec-080) replaces the states with the facts
above.

---

## Related

- [`../../LIFECYCLE.md`](../../LIFECYCLE.md) — the generated per-stack view
- [`security-baseline.md`](security-baseline.md) — what the baseline requires
- [`writing-style.md`](writing-style.md) — which reader each file serves
- [`../maintenance.md`](../maintenance.md) — the chains that apply these
