# Documentation Workflow

Keep instructions accurate for their reader and update them with the change they
describe. This file covers purpose, ownership and maintenance; use
[`writing-style.md`](writing-style.md) for wording guidance.

## Core Principle

Code and affected documentation belong in the same change set and must agree
before merge. They may occupy more than one commit when that helps review.
Unrelated documentation defects do not automatically expand the task.

## Before drafting: the purpose preflight

For a new document or a substantial rewrite, identify the reader, the result they
need, the relevant sources and what belongs elsewhere. A short note is sufficient
when discussing the structure would help review. No form or separate approval is
required for a small correction.

## Section contracts

Use headings that match the information beneath them. Installation explains how
to reach a working state; verification states the check and expected result;
operations and troubleshooting support running and diagnosing the system.
Architecture and decision records explain dependencies and trade-offs.
Use the sections needed by the reader, not a fixed list for every file.

## Who You Are Writing For

Write for someone who needs to install, operate, review or diagnose the system.
Include values, consequences, choices and expected results. Keep development
narration out of installation steps; include rationale where it changes a decision
or explains a dependency.

### Layered, not exhaustive

Answer the common task on the page and link to deeper material. Operator-site pages
must let the reader complete the task without first learning the repository's
internal vocabulary. A reference section may link to maintainer material.

### A shared tool gets one page; each stack contributes its own section

Document a shared tool's installation and operation at that tool. Stack pages
provide their own configuration, recovery requirements and links to the shared
procedure. Keep both navigation paths usable.

## Information ownership

The [File Map](../maintenance.md#file-map--single-source-of-truth) identifies the
canonical sources. Correct a changing fact there and update dependent summaries
or regenerate dependent views. References, examples and summaries are useful when
the reader needs them; avoid independently maintained copies of an inventory.

Status facts follow [`status-model.md`](status-model.md#who-owns-which-fact).
Generated views are updated with their scripts, not by editing their output.

## Current state, plans, and history have separate owners

| Material | Location |
|---|---|
| Setup, operations and known limitations | stack `README.md`, relevant standards |
| Upstream pins, upgrade notes, verification date and version | stack `UPSTREAM.md` |
| Planned work | `ROADMAP.md` |
| Shipped changes | `CHANGELOG.md` |
| Architecture and consequential decisions | `docs/architecture.md`, `.ai/decisions.md` |
| Dated assessments and host evidence | `docs/audits/`, `docs/host-session-*.md`, relevant lab records |
| Significant incidents and reusable fixes | `docs/bugfixes/`, `TROUBLESHOOTING.md` |
| Active work and handoff context | `.ai/state.md`, `.ai/tasks.md`, `.ai/progress.md` |

Record evidence and decisions when they affect future work. Routine edits need no
additional session report. Public records follow
[`Public content`](commit-rules.md#public-content); identify a test environment by
its role rather than private addresses or credentials.

When referencing a numbered decision outside its document, name the source as
well, for example `core D6` or `review D3`, or link directly to the entry.

## The relevance test

During review, check whether the changed text answers the reader's question,
belongs in this section and agrees with its canonical source. Remove unnecessary
repetition and distinguish facts, recommendations and untested assumptions.
This is review guidance, not a per-paragraph form or approval step.

## Document Types

| Type | Update when | Examples |
|---|---|---|
| Live | behavior or instructions change | stack `README.md`, `UPSTREAM.md` |
| Policy or reference | the relevant rule changes | `SECURITY.md`, `docs/standards/` |
| Snapshot | evidence is recorded; later work references or supersedes it | dated audits and host reports |
| Plan | scope, direction or completion changes | `ROADMAP.md` |
| Generated | its canonical inputs change | `LIFECYCLE.md`, site data, security coverage |

A historical record is not a current instruction. Keep a programme that still
directs work aligned with current rules, or mark it superseded.

## Update Triggers

| Change | Update |
|---|---|
| Add or remove a stack | stack files, category listing, relevant plan items and generated views; root README only if its overview changes |
| Change an image pin | production and matching local example, upstream version and upgrade notes, relevant generated views and changelog |
| Change behavior or configuration | affected setup, operations, migration or troubleshooting instructions |
| Change a standard | its source, dependent guidance and affected implementations within the agreed scope; disclose remaining migration work |
| Complete a host verification | actual tested version, date, scope and evidence in `UPSTREAM.md`, then regenerate lifecycle views |
| Release | changelog, version references and completed plan items |

A pin update does not update `Last verified`. Preserve the tested version and date
until a new test establishes a new record. State when the new pin has not run on
a host. Static checks and successful rendering are not host verification.

## Sync Points

Before proposing completion, review affected documentation and run checks suited
to the change. Fix defects introduced by the change. Report consequential existing
defects, and ask only if fixing them requires a material extension of the task.
All required CI gates still apply before merge; their current behavior is in
[`ci.md`](ci.md). At release, also follow the
[Release Chain](../maintenance.md#release-chain).

## Checklist for Common Changes

- **New stack:** setup and upstream information, category listing, matching local
  example where applicable, generated views and relevant changelog entry.
- **Image update:** both example pins, upstream notes and migrations, relevant
  checks, explicit host-test status, generated views. Preserve existing verification.
- **Bug fix:** corrected behavior and affected instructions; add an incident record
  when the cause, recovery or lesson is useful beyond the diff.
- **Standard change:** canonical rule and dependent guidance agree; identify any
  implementation migration that remains.

## AI Responsibility

Complete the authorized documentation work, verify its claims and check relevant
links and formatting. State what was and was not tested. Explain a substantive
conflict or missing decision rather than silently inventing policy. No routine
preflight form, session log or repeated approval is required.

## Related Standards

- [`writing-style.md`](writing-style.md) — wording and register
- [`status-model.md`](status-model.md) — lifecycle evidence
- [`../maintenance.md`](../maintenance.md) — canonical sources and maintenance triggers
- [`commit-rules.md`](commit-rules.md) — authorization, commits and publishing
- [`new-app-checklist.md`](new-app-checklist.md) — adding a stack
