# Documentation Workflow

What a document is for, who reads it, which facts it owns, and when it has to be
updated. Documentation that lags behind the code misleads. Documentation that is
current and answers a question its reader did not ask costs them the answer they
came for.

This standard and [`writing-style.md`](writing-style.md) divide one subject
between them:

| This file owns | `writing-style.md` owns |
|---|---|
| Purpose, readers, section contracts, relevance, ownership modes, update rules | Register on sentence and paragraph level — the seven forms, address and mood |
| *Whether* a sentence belongs in this document at all | *How* it reads once it belongs |

Neither file overrides the other. A sentence has to pass both.

## Core Principle

**Same-commit documentation.** Code changes and their documentation updates go into the same commit (or the next one at the latest). "We'll fix the docs later" is not allowed.

## Before drafting: the purpose preflight

Every documentation change starts here. The block is filled in before the first
sentence is written — in working notes, in the pull request, or in the exchange
that requested the change. It is not committed alongside the file.

```text
Target file:
Primary readers:
Document purpose:
Section being edited:
Reader's immediate goal:
Result this section must provide:
Required information:
Explicitly out of scope:
Canonical owners of the required facts:
```

Drafting begins once the nine lines agree with each other. Two disagreements
come up repeatedly:

- **The section objective is not part of the document purpose.** The section
  belongs in a different document. Fill the block in again for that one.
- **A required fact is owned elsewhere.** Use it, summarise it for this reader,
  or link to the owner — see [Information ownership](#information-ownership).
  A second independent version is not one of the options.

`Explicitly out of scope` is the line that does the work. It names the subjects
the material invites and the reader did not ask for: how the current result was
reached, what the previous configuration was, what else might go wrong,
which alternatives were rejected, which unrelated issue appeared during
development. Each of those has an owner listed further down.

## Section contracts

A document may serve several related reader needs. A section has one objective.
The objectives in use here:

| Section | The reader leaves knowing |
|---|---|
| Overview | what exists, and whether it is relevant to them |
| Requirements | what has to be in place before starting |
| Installation | the steps that reach a working state |
| Configuration | which values exist and what each one changes |
| Verification | whether the result is correct |
| Operations | how to run the system as it stands |
| Troubleshooting | how to diagnose and resolve an observed failure |
| Architecture | how the parts relate, and why the structure holds |
| Decision record | one consequential decision, its trade-offs, its consequence |
| Roadmap | what is planned |
| Changelog | what shipped |
| Known limitations | the exact current gap, named |

A document uses the objectives its readers need, in the order that serves them.
None of these is a required section, and the list is not a template: content is
matched to the objective the section declares. Where text and heading serve
different objectives, one of the two is wrong — a heading is a claim about the
content below it.

## Who You Are Writing For

Every file is read by someone who has no context: they did not follow the
development, they do not know what was tried before, and they are not interested.
They arrived with a goal — install this, decide that, fix the thing in front of
them.

Write for that reader. State what is, and what they can choose.

### What does not belong in configuration files and setup docs

- **History.** What used to be configured, what changed, what broke once.
- **Justification of a decision to whoever reviewed it.** "X rather than Y — one
  source of truth" explains a change to a colleague. The reader needs the value
  to set, not the reasoning of whoever set it last.
- **Self-description.** That the setup is secure, careful, or follows best
  practice. If it does, that shows; saying it costs the reader a line and buys
  nothing.
- **Anything that only makes sense to someone who was there.**

All of it has a home, and none of those homes is a `.env.example`:

| What | Where |
|---|---|
| What changed and when | `CHANGELOG.md` |
| Why a decision was made | `docs/architecture.md`, the stack's `UPSTREAM.md` |
| What went wrong and what it taught | `docs/bugfixes/`, `.ai/errors.md` |
| Deviations from upstream | `UPSTREAM.md` |

### What does belong

- The value to set, and what happens if it is wrong.
- The choice the reader has, where there is one, and what each option costs.
- A link to the official source — the project's own documentation, the registry
  page — so the reader can go deeper without asking anyone.

A comment earns its place by changing what the reader does. If it does not, delete
it.

### Layered, not exhaustive

Answer the common case first and completely. Send the rest onward: a link to
upstream documentation, a deeper page, a reference section. A reader who wants
more will follow a link; a reader who wants to finish will not read three screens
to find one value.

This matters most on the operator site, where the reader chose to be there and
will leave if the first screen is not useful.

### On the operator site, the reader has never seen this repository

They do not know what `LIFECYCLE.md` is, what `baseline-aligned` means, or that
anything is generated. Every sentence that only makes sense to someone who does
is noise on their screen, and it pushes the sentence they needed further down.

Three things this rules out, all of which have had to be removed once already:

| Do not write | Because |
|---|---|
| Where a fact came from — "generated from the repository, not maintained here" | If they care, they follow the link. If they do not, it is a sentence about our tooling on their page |
| A general disclaimer — "we do not vouch for this, evaluate it yourself" | It says nothing specific. State the actual gap instead: *client sync is untested*. A named gap is information; a hedge is noise |
| The same status twice, in a badge and again in prose | The second one is the one that goes stale |

State the facts, then **one sentence naming what specifically has not been
exercised**. Anything a reader might want behind that goes in the FAQ, once.

Put the command before its justification, too. The reader is following steps;
they need to know what to run and what they should see. Why it is the safer of
two options is one short clause, not a paragraph — and if it takes a paragraph,
it belongs in the repository, not here.

**A heading is a claim.** Every site page carried a section called *Quickstart*
that generated six secrets, set file ownership, configured mail and read Docker
subnets. Writing the word did not make it quick; it only told a reader who took
twenty minutes that they were slow. Worse, *quick*start implies a slower,
fuller path exists somewhere — and none did. The section is the installation, so
it is called **Installation**. Name a section for what it contains, and only
promise speed, simplicity or completeness where the content delivers it.

For the shape of this, the useful precedents are Node.js's stability index and
MDN's Baseline widget: one compact line at the top, and the explanation behind a
link.

### A shared tool gets one page; each stack contributes its own section

Where one host-level tool serves every stack — the backup agent, the reverse
proxy, the intrusion detection — the split is:

| Where | What belongs there |
|---|---|
| The tool's own page | Installing it, its own configuration, the concepts a reader needs before any stack makes sense, and how to verify it |
| The stack's page | Only what is specific to that stack — the lines it contributes, whether it needs special handling, what is different when recovering it — with a link back to the tool's page |

The reader arrives from either direction. Someone setting up a stack reaches
"and I want this backed up", follows the link, installs the tool, and returns.
Someone setting up the tool needs the list of stacks that then require attention.
Both paths have to work, so the tool's page carries a list of the stacks and each
stack links back.

What must not happen is the tool's page teaching itself through one stack's
example. It reads as complete and is not: the next stack's operator finds
instructions that name a database and a pause command belonging to something they
do not run.

## Information ownership

Every changing fact has one **canonical owner** — the source that defines it. The
map is the [File Map](../maintenance.md#file-map--single-source-of-truth) in
`docs/maintenance.md`; status facts are mapped in addition by
[`status-model.md`](status-model.md#who-owns-which-fact). Which person or role
keeps a given file current is a separate question, answered by
[maintenance responsibility](../maintenance.md#maintenance-responsibility).

A document that does not own a fact has five legitimate relationships to it, and
one that is prohibited:

| Mode | What it is | Used when |
|---|---|---|
| **Canonical** | The fact is defined here. Every change to it happens here | one source per fact |
| **Use** | The value appears in a step, because the reader needs it to act | a command, a path, a required version |
| **Summary** | One purpose-specific sentence, shorter than the owner's treatment | the reader needs the shape, not the detail |
| **Reference** | A link to the owner, naming what the reader will find there | the detail may be needed, later |
| **Generated** | A representation written from the canonical sources by a script, never by hand | `LIFECYCLE.md` |
| **Duplication** | A second independent version that can drift | prohibited |

`Generated` is a presentation mode, not a competing owner: the generated file
holds no fact of its own, and a wrong value in it is corrected at the canonical
source and regenerated.

Ownership does not oblige repetition. A fact appears in a second document because
that document's reader needs it to reach their result — not because it is
correct, related, or in danger of being overlooked somewhere.

A wrong fact is corrected at its owner. Correcting it at a mirror produces either
nothing, when the mirror is regenerated, or two versions that both read as
authoritative when it is not.

## Current state, plans, and history have separate owners

Current-state documentation states what exists, what to do, what happens, how to
verify it, and where the current gap is. It does not state how the result was
reached, what a work session did, which draft came before, or who proposed the
change.

None of that material is discarded. Each part has an owner:

| Material | Canonical owner |
|---|---|
| Planned work | `ROADMAP.md` |
| Shipped changes | `CHANGELOG.md` |
| Current implementation | the stack's `README.md`, `docs/standards/`, `docs/architecture.md` |
| Deviation from upstream, upgrade rationale | the stack's `UPSTREAM.md` |
| Dated inspection of a state | `docs/audits/` |
| One incident — symptom, cause, fix, lesson | `docs/bugfixes/` |
| What a session established, in sequence | `docs/maintenance-log.md`, `docs/host-session-*.md` |
| Active working state | `.ai/state.md`, `.ai/tasks.md`, `.ai/progress.md` |

The lower half of that table is narrative by purpose: a findings log records how
something was established, including what failed on the way. The exclusion of
development narration governs current-state documentation and does not reach
these.

A reason belongs in current-state documentation when it changes what the reader
does:

| Write | Not |
|---|---|
| Back up the database and the signing keys together. A database restored without them leaves every existing client unable to authenticate. | This note was added after a review found that the signing keys had been overlooked. |

## The relevance test

Applies to every paragraph being written or edited. It is not an instruction to
sweep documents that are not otherwise being touched.

1. Which exact reader question does this paragraph answer?
2. Is that question part of the purpose of this document and this section?
3. Does the answer change an action, a decision, a verification, a diagnosis, or
   a dependency the reader has to understand?
4. Is this the document that owns the fact?
5. Is this current state rather than development narration?
6. Could the paragraph be removed with the reader still reaching the result?

| Answer | Action |
|---|---|
| 2 or 3 is no | remove |
| 4 is no | move to the owner; leave a reference where the reader needs one |
| 5 is no | move to its owner in the table above |
| 6 is yes | remove, or shorten to the part that fails question 6 |

Correct and relevant are separate tests. A sentence that is accurate, related to
the subject, cautious, or already available elsewhere has not yet earned its
place; it earns it by contributing to the result the reader came for. A correct
sentence in the wrong document is a defect in both documents.

## Document Types

Every document has a type. The type determines when it must be updated.

| Type | Update Trigger | Update Window | Examples |
|------|----------------|---------------|----------|
| **Live** | Any relevant commit | Same commit | `README.md`, per-app `README.md`, `UPSTREAM.md` |
| **Policy** | Policy decision changes | Same commit | `SECURITY.md`, `LICENSE` |
| **Reference** | Standard evolves | Same commit | `docs/standards/*.md` |
| **Snapshot** | Event occurred | At event | `docs/bugfixes/<app>-<date>.md` |
| **Plan** | A listed item ships or becomes irrelevant | Same commit | `ROADMAP.md` |
| **Generated** | Its sources change | Same commit, by script | `LIFECYCLE.md` |
| **Draft** | Ongoing iteration | Flexible | Private drafts, work-in-progress docs |

`ROADMAP.md` is a **Plan**, not a Live document: an item that ships leaves the
planned section in the same commit, while the direction it describes is reviewed
periodically rather than per commit.

## Update Triggers

Concrete rules: when X happens, update Y.

### Code Changes

| When | Update |
|------|--------|
| New app added to `apps/` | `README.md` (apps table), `ROADMAP.md` (remove from planned if applicable), new app's `README.md` + `UPSTREAM.md` |
| New core service added to `core/` | `README.md` (core infrastructure table), related standards if patterns changed |
| App version bumped (new image tag) | App's `UPSTREAM.md` (Based on version + `Last verified`) |
| App removed | `README.md`, `ROADMAP.md`, possibly `CHANGELOG.md` |
| New standard in `docs/standards/` | `README.md` (conventions section), cross-refs in other standards |
| Standard evolves (rule change, new pattern) | Affected standards file + every app that uses it |
| Security baseline change | `SECURITY.md`, `docs/standards/security-baseline.md`, all apps |
| Breaking change | `CHANGELOG.md`, relevant app `UPSTREAM.md` |

### Bug Fixes

| When | Update |
|------|--------|
| Bug discovered | `docs/bugfixes/<app>-<date>.md` (OPEN status) |
| Bug fixed | Same bugfix doc (RESOLVED status), app `README.md` Known Issues if user-facing |
| Bug parked (upstream) | Same bugfix doc (PARKED status), note in app README |
| Recurring pattern across bugs | `.ai/errors.md` — the pattern, not the individual incident |

### Process Changes

| When | Update |
|------|--------|
| Commit rules change | `docs/standards/commit-rules.md` |
| Branch model change | `docs/standards/commit-rules.md` + `documentation-workflow.md` |
| Release process change | `CHANGELOG.md`, release notes template |
| Review process change | `CONTRIBUTING.md` |

### Milestones

| When | Update |
|------|--------|
| Stack verified on a host and baseline met | The status owner per [`status-model.md`](status-model.md#who-owns-which-fact), `UPSTREAM.md` `Last verified`, then regenerate `LIFECYCLE.md` |
| Feature completed | `ROADMAP.md` (move from In Progress to Done/remove), `README.md` if user-facing |
| Release tagged | `CHANGELOG.md`, Git tag |

## Freshness Rules

### Always up-to-date (no exceptions)

- `README.md` — first impression, must never mislead
- `SECURITY.md` — contact info, response timeline
- `LICENSE` — legal accuracy
- Per-app `README.md` Setup instructions — users follow these literally

### Can lag briefly (days)

- `ROADMAP.md` direction — reviewed monthly. A shipped item still leaves the
  planned section in the commit that ships it.

### Refreshed periodically (event-based)

- `CHANGELOG.md` — at release
- `docs/bugfixes/*` — at event (lifetime)

## Sync Points

Checkpoints where documentation consistency is verified.

### Per-commit (mandatory)

Before every commit, the AI or contributor asks:

- Does this change affect any Live document?
- Does it invalidate a Reference document (standards)?
- Does it need a Snapshot document (bugfix)?
- Did every paragraph written or edited pass [the relevance test](#the-relevance-test)?

If yes → update in same commit.

### Per-push (recommended)

Before pushing to `main`:

- `README.md` reflects current state
- `ROADMAP.md` reflects current priorities
- All standards are consistent

### Periodic (monthly)

- `ROADMAP.md` review: is it still the actual priority?
- Stale bugfix-docs (OPEN for > 30 days): parked or escalated

### Per release (when applicable)

- `CHANGELOG.md` update
- Standards review
- Cross-doc consistency check

## Checklist for Common Changes

### Checklist: Adding a new app

- [ ] Create `apps/<app>/` directory with compose, env, README, UPSTREAM, gitignore
- [ ] Update `README.md` apps table (alphabetical or grouped)
- [ ] If app was in `ROADMAP.md` as planned → remove from there
- [ ] Bugfix-doc if any issues during bring-up
- [ ] Regenerate `LIFECYCLE.md`

### Checklist: Bumping an image version

- [ ] Change `APP_TAG` in `.env.example`
- [ ] Update `UPSTREAM.md` (Based on version, `Last verified: YYYY-MM-DD (vX.Y.Z)`)
- [ ] Run test-script, document any regressions
- [ ] If breaking change: `CHANGELOG.md` entry

### Checklist: Changing a standard

- [ ] Update the specific standards file
- [ ] Grep repo for old pattern, update every occurrence
- [ ] Cross-ref check in other standards
- [ ] Update `README.md` conventions section if user-facing

### Checklist: Fixing a bug

- [ ] Write bugfix-doc with Symptom/Cause/Fix/Lesson
- [ ] Update app `README.md` Known Issues (if user-facing)
- [ ] Fix in code
- [ ] Commit: fix + bugfix-doc together

## AI Responsibility

When working on changes, the AI must:

1. **Complete the [purpose preflight](#before-drafting-the-purpose-preflight)** — before the first sentence, not afterwards as a justification
2. **Identify doc dependencies** — after a code change, ask: what docs does this affect?
3. **Update in same commit** — not in a follow-up commit "later"
4. **Apply [the relevance test](#the-relevance-test)** to every paragraph written or edited
5. **Flag inconsistencies** — if touching a file reveals outdated docs nearby, mention it to the user
6. **Refuse to commit with known stale docs** — ask user first: "I notice README is out of date, should I fix it as part of this commit?"

### Anti-patterns (AI must avoid)

- "We'll update the docs later" — no
- Committing code without checking if README/ROADMAP still accurate — no
- Updating docs in a separate commit without linking it to the code change — avoid (use same commit when possible)
- Leaving ROADMAP with "Planned" items that are already done — not allowed

Each of the following starts from a correct sentence and puts it where it does
not serve the reader. All of them fail the relevance test:

| Drift | Where it belongs instead |
|---|---|
| How the current result was reached, in a document that states the result | `CHANGELOG.md`, `docs/architecture.md`, the session owners |
| Development history in an installation section | `CHANGELOG.md`, `docs/bugfixes/` |
| Future plans in current-state documentation | `ROADMAP.md` |
| A broad warning in place of the concrete limitation | state the gap, in the same section |
| A hypothetical objection or a second reading nobody asked for | nowhere |
| A subject built out of one word taken from the task | nowhere |
| The author's reasoning where the reader needs the consequence | rewrite as the consequence |
| A fact kept in the wrong document so that it is not lost | its owner, with a reference where the reader needs one |

## Related Standards

- [`writing-style.md`](writing-style.md) — how the text reads once it belongs
- [`status-model.md`](status-model.md) — the two status axes and who owns each status fact
- [`../maintenance.md`](../maintenance.md) — the File Map, maintenance responsibility, and the chains that apply these rules
- [`commit-rules.md`](commit-rules.md) — commit process, branch model
- [`new-app-checklist.md`](new-app-checklist.md) — checklist when adding apps
