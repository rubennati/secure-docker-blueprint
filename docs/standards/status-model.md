# Status Model

One lifecycle, for one reader: a maintainer deciding what to work on. It answers
*what has been established about this stack*, and nothing else.

It carries no promise to an operator. Whether a stack suits a deployment is a
question the repository cannot answer, because it does not know the deployment.
That belongs on the operator site, in the form of concrete evidence and named
gaps — see [`writing-style.md`](writing-style.md#audience-per-file).

---

## The lifecycle

Four states. Each is **measured from an artefact**, never typed into a table.

| State | Established by | Read from |
|---|---|---|
| `scaffolded` | the stack exists | a compose file in the stack directory, or a host-installed component its category README lists |
| `verified` | it ran, against a named version | `Last verified: DATE (vX.Y.Z)` in `<stack>/UPSTREAM.md` |
| `baseline-aligned` | `verified`, and the security baseline holds | `check-baseline.py` and `check-structure.py` report no failure for that stack |
| `ops-proven` | `baseline-aligned`, and its data came back | the stack appears in the rehearsal log of [`backup/borgmatic/RESTORE.md`](../../backup/borgmatic/RESTORE.md#rehearsal-log) |

A date without a version does not reach `verified`. Which version was checked is
what makes the claim usable a year later; a bare date says only that someone
looked.

**`verified` and `baseline-aligned` currently hold the same set.** Both checkers
report zero failures across the repository, so every stack that clears the date
also clears the baseline. The two separate the moment a checker fails for one
stack, which is what the tier is for.

## Why it is measured

The previous model had a public axis of symbols typed into README tables and an
internal axis derived from those symbols by lookup. The internal axis therefore
carried no information the public one did not, and both depended on somebody
remembering to edit a table.

They fell behind. `apps/nextcloud` and `business/invoiceninja` were built,
hardened and verified on a live host on 2026-07-29; their symbols still said
preview when this standard was rewritten. Measurement moved both without anyone
typing anything.

## Who owns which fact

Every fact has one owner. Everything else derives from it. When two files
disagree, the owner wins, and the derived file was generated from stale input.

| Fact | Owner |
|---|---|
| Pinned image version | `<stack>/.env.example` |
| Last verified date and version | `<stack>/UPSTREAM.md` |
| Security baseline alignment | `<stack>/docker-compose.yml`, checked by `check-baseline.py` and `check-structure.py` |
| Restore evidence | `backup/borgmatic/RESTORE.md`, rehearsal log |
| Backup and restore documentation | `<stack>/README.md` |

Restore evidence sits in the rehearsal log because that is where it is produced:
the log records the archive, the scope, the result and the numbers. The log's
`Stack` column names the repository key, which is what makes it machine-readable.

## LIFECYCLE.md is generated

`scripts/ci/lifecycle-report.py` produces [`LIFECYCLE.md`](../../LIFECYCLE.md)
and `site/src/data/lifecycle.json`. **Neither is edited by hand.**

```bash
python3 scripts/ci/lifecycle-report.py --write
```

A generated file cannot drift: either it is current, or CI fails because it is
not.

## What CI enforces

`lifecycle-report.py --check` fails when:

- `LIFECYCLE.md` or `lifecycle.json` is out of date with respect to its sources
- a stack directory carries no `UPSTREAM.md`
- the rehearsal log names a stack that does not exist

It reports without failing when a stack still carries the pre-v0.5.1
`Last checked: DATE` field. Thirty stacks do. They sit at `scaffolded` until
someone verifies them against a named version — the field is not converted
automatically, because writing `verified` asserts that evidence exists.

---

## Related

- [`../../LIFECYCLE.md`](../../LIFECYCLE.md) — the generated per-stack view
- [`security-baseline.md`](security-baseline.md) — what the baseline requires
- [`writing-style.md`](writing-style.md) — which reader each file serves
- [`../maintenance.md`](../maintenance.md) — the chains that apply these
