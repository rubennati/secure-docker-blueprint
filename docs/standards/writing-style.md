# Writing Style

How documentation in this repository reads, at the level of the sentence and the
paragraph.

[`documentation-workflow.md`](documentation-workflow.md) owns purpose, readers,
section contracts, relevance and information ownership — *whether* a sentence
belongs in a given document. This file owns *how* it reads once it does. A
sentence has to pass both; neither file overrides the other.

`scripts/ci/check-prose.py` covers part of what is below —
[Checking](#checking) states which part.

---

## The form

A report. Where something is, what it does, which value to set, what happens if
it is wrong.

Not a record of how the author arrived at it. The reader did not follow the
work, does not know what was expected, and did not ask what the author found
surprising.

| Write | Not |
|---|---|
| `checkNewVersion` contacts `update.traefik.io` with the version and public IP. Set `false`. | Traefik's version check is on by default, which is worth knowing — it turns out the vendor uses it for sales. |
| Two of seven make an outbound call not requested by the operator. | Monitoring was the category most likely to phone home. It is better than expected: only two of seven. |
| `Flexible` encrypts browser→Cloudflare only. The origin leg is plaintext. | **Flexible is the dangerous one.** The padlock tells the user something untrue. |

---

## Seven things that do not go in

Each is drawn from text that was in this repository.

### 1. The author's expectations

Was: *"Monitoring was the category most likely to phone home … It is better than
expected."*

The reader has no prior expectation to be corrected. State the count.

### 2. Justification of the documentation's own design

Was: *"Deliberately **not** a score. A number would compress two things onto one
axis and invite an argument about the weighting."*

The reader wants the data. Why the format was chosen belongs in `CHANGELOG.md`
or `docs/architecture.md`.

### 3. Dramatic emphasis

Was: *"**Flexible is the dangerous one.**"* · *"Two rows deserve attention."* ·
*"worth naming"*

Ranking a row's importance is the reader's job. Give the fact and its
consequence; if one option is unsafe, say what it does.

### 4. Stage directions

Was: *"The trade in one line:"* · *"The short version"* · *"Two things to read
out of it."*

Announcing the shape of the next sentence is a sentence that carries no
information. Write the sentence.

### 5. Aphorism

Was: *"Finding a call proves it exists. Not finding one proves that the searches
ran — nothing more."* · *"a hostname nobody has listed is unlisted, not
protected"*

Symmetry and cadence are not precision. Say which check was run, against what,
and what it does not cover.

### 6. Software with intentions

Was: *"a tool whose job is watching things tends to want to report"* ·
*"the padlock tells the user something untrue"*

Programs do not want, tell, or care. Name the process and the call it makes.

### 7. Evaluation in place of a value

Was: *"genuinely better"* · *"is milder"* · *"is harmless"* · *"worth it, and
not close"*

`uptime-kuma` sends no payload; `changedetection` sends a persistent GUID. Those
two facts let the reader rank them. "Milder" does not.

---

## Address and mood

English in the repository. German only in the exchange with the maintainer.

Whether a text addresses its reader directly follows from what the section is
for, not from a repository-wide preference:

| The reader is | Register |
|---|---|
| Performing steps — installation, operations, troubleshooting, verification | Imperative, and direct address where that makes the action clearer: *run this*, *set it to `false`*, *check that the container reports healthy* |
| Establishing what is true — reference, architecture, policy, status, decision records | Declarative and neutral. The subject is the system, not the reader |

Neither register licenses the other's failure mode. An imperative step still
states what happens when the value is wrong; a declarative reference still names
the action a value causes.

No repository-wide language rule overrides the purpose of a document or a
section. Where the two appear to conflict, the [section
contract](documentation-workflow.md#section-contracts) decides.

## Audience per file

The status model already assigns [one owner per
fact](status-model.md#who-owns-what). This assigns one reader per file.

| File class | Reader | Never contains |
|---|---|---|
| `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md` | someone evaluating the project | maintainer decisions, dated internal changes, record-format notes |
| `<stack>/README.md`, `<stack>/.env.example` | an operator deploying that stack | history, why a past decision was made, session context |
| `<stack>/UPSTREAM.md` | a maintainer upgrading that stack | *(deviations and rationale belong here)* |
| `site/src/content/**` | a customer who has never seen this repository | internal vocabulary in the body — `LIFECYCLE.md`, the internal status axis, checker names; and body text that sends the reader into a maintainer file to finish a task |
| `docs/**` except `docs/standards/` | a maintainer | *(narrative is allowed; findings logs record how something was established)* |
| `docs/standards/**` | a contributor about to write or review | *(rules and their reasons)* |

A closing **Reference** section that links into the repository is not a
violation. It is the layering [documentation-workflow.md](documentation-workflow.md#layered-not-exhaustive)
asks for: answer the common case on the page, send the rest onward. The
distinction is body versus appendix — a customer must be able to finish the task
on the page, and follow a link only to go further.

### The rule that was broken

`status-model.md` states that internal status *"lives in `LIFECYCLE.md`, never in
the README tables"*. The root README nevertheless carried a dated note
explaining that seventeen stacks were downgraded because their verification
predated a record format.

That note is correct, and it belongs in `CHANGELOG.md`. A reader on the GitHub
landing page has no record format.

---

## Internal files are not exempt from register

`docs/bugfixes/` and the host-session findings record how something was
established, including what failed on the way. That is their subject.

The seven items above still apply. A findings log states what was run and what
came back; it does not need aphorism or dramatic emphasis either.

---

## Checking

```bash
python3 scripts/ci/check-prose.py --hints                    # the whole repository
python3 scripts/ci/check-prose.py --changed-only --base HEAD # only what a change touches
```

The full run is the gate: CI executes it in the `Docs QA` job, and a phrase in a
reader-facing file fails it. Maintainer files report the same findings as
warnings — an audit or a findings log quotes wording in order to record it, and
that is the document's subject.

`--changed-only` stays available for reviewing one change locally.

Matching works on prose units rather than lines: a paragraph, a list item or a
block quote is joined before the phrase list is applied, so wrapping a sentence
across two lines no longer hides a phrase. A heading, a table row, a fence or a
blank line ends the unit.

The checker matches an exact phrase list, not a general pattern. It finds the
recurring formulations and nothing else — passing it is not evidence that a file
reads well, only that it avoids the seven known shapes. Purpose, relevance and
whether a fact sits in the document that owns it are review questions, decided
against [`documentation-workflow.md`](documentation-workflow.md).

Add a phrase when it appears twice. A one-off gets fixed in review.
