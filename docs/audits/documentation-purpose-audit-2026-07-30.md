# Documentation Purpose Audit — 2026-07-30

Repository-wide review of documentation purpose, information architecture,
ownership and cross-surface consistency. Analysis only: no documentation outside
this file was changed.

---

## 1. Executive summary

The repository's documentation governance is sound and, since the Phase 1–4
work, internally consistent. The register is disciplined: a repository-wide
search for vague warnings, hedging and marketing claims returns almost nothing.
The generated chain from `UPSTREAM.md` / `.env.example` → `LIFECYCLE.md` →
`site/src/data/lifecycle.json` → the site's `StackStatus` component is a working
example of ownership without repetition.

Four systemic problems remain, and they are not register problems:

1. **The root `README.md` Quick Start does not work.** Three defects in six
   commands: a placeholder clone URL, secret files the target stack never reads,
   and base64 passwords for a stack whose password goes into a connection string
   — the exact failure `TROUBLESHOOTING.md` 2.3 documents. This is the first
   command sequence a new reader runs (F-01, **P0**).
2. **`.ai/state.md` carries hand-typed counts of generated facts and is wrong.**
   It reports 39 `ready` / 20 `preview` where the generated owner reports 21 / 38
   (F-02, **P1**). It is step 2 of the documented start sequence, so every
   session begins from a stale number.
3. **The operator site states a repository-wide default the configuration does
   not hold.** `/project/` lists `cap_drop: ALL` among "what the compose files
   are set to, across services"; the owning standard classifies capability drop
   as *Recommended*, and 30 of 124 services set it (F-03, **P1**).
4. **`ROADMAP.md` owns "Direction" but carries shipped history and session
   narration**, duplicating `CHANGELOG.md` and pointing readers at maintainer
   host-session runbooks (F-05, F-06, **P2**).

Two documents have no stated relationship to each other: `TROUBLESHOOTING.md`
and `docs/standards/troubleshooting.md` cover the same subject, neither links to
the other, and the root `README.md` links to neither (F-08, F-09).

**24 findings: 1 × P0, 5 × P1, 12 × P2, 6 × P3.** The recommended first batch is
five packages, beginning with the Quick Start correction and the removal of
hand-typed counts from `.ai/`.

---

## 2. Audit objective

Determine, for each documentation-bearing file and its material sections,
whether the content helps the intended reader reach the stated purpose of that
document or section, and whether each changing fact has one canonical owner that
the rest of the repository respects.

Out of objective: grammar, tone and length as such. Length is treated as a
symptom only where a purpose or ownership defect explains it.

---

## 3. Binding standards used

| Standard | What it decided in this audit |
|---|---|
| [`docs/standards/documentation-workflow.md`](../standards/documentation-workflow.md) | Section contracts, the six-question relevance test, the six ownership modes, current-state vs. plan vs. history |
| [`docs/standards/writing-style.md`](../standards/writing-style.md) | One reader per file class, address and mood, the seven register forms |
| [`docs/maintenance.md`](../maintenance.md) | File Map — canonical owner per fact; maintenance responsibility per file |
| [`docs/standards/status-model.md`](../standards/status-model.md) | Which source owns a status, a pin, a verification date |
| [`AGENTS.md`](../../AGENTS.md) | The eight documentation hard rules and the mandatory reading list |
| [`.ai/routing.md`](../../.ai/routing.md) | The documentation route actually defined by the repository |
| [`.ai/quality-gates.md`](../../.ai/quality-gates.md) | Which check is a gate and which is an inventory |

The repository's own documentation route was followed rather than a new one:
`AGENTS.md` → `.ai/routing.md` *Documentation route* → the three canonical owners
→ `.ai/domains/documentation.md` as the operative summary that owns nothing.

---

## 4. Method and criteria

1. **Preflight** — branch, working tree, presence of the Phase 1–4 anchors.
2. **Inventory** — every tracked `.md` / `.mdx` / `.mdc` file outside `inbox/`,
   grouped into families; representative files classified in full.
3. **Ownership analysis** — every repeated changing fact traced to its File Map
   owner and classified as canonical / use / summary / reference / generated /
   prohibited duplication.
4. **Purpose analysis** — the categories A–U from the audit brief, evidenced by
   grep patterns across all families rather than by files already suspected.
5. **Verification of every claim before recording it.** Two candidate findings
   were dropped this way: an apparent 18 % capability-drop coverage (the file
   glob had included `inbox/`, correct figure 24 %), and an apparently dead
   `/faq/#what-do-the-status-labels-mean` anchor (the FAQ generates its anchors
   from question text; the anchor resolves).
6. **Paragraph relevance review** on the material findings.
7. **Prose-check interpretation** — the checker's output as input, classified per
   finding rather than treated as a task list.

---

## 5. Repository documentation inventory

236 tracked documentation files outside `inbox/`.

| Family | Count | Primary reader | Document type | Update trigger |
|---|---|---|---|---|
| Root governance and entry (`README`, `ROADMAP`, `CHANGELOG`, `TROUBLESHOOTING`, `SECURITY`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `LICENSE`) | 10 | someone evaluating or adopting the project | Live / Plan / Policy | any user-visible change |
| `LIFECYCLE.md` | 1 | maintainer and operator | Generated | its sources change |
| Category READMEs (`business`, `monitoring`, `backup`, `site`) | 4 | someone choosing within a category | Live | a stack is added, removed or re-verified |
| Stack READMEs | 62 | an operator deploying that stack | Live | any change to that stack |
| `UPSTREAM.md` | 60 | a maintainer upgrading that stack | Live | version bump, deviation change |
| `CONFIG.md` | 1 | an operator configuring a complex stack | Live | option change |
| `docs/standards/` | 15 | a contributor about to write or review | Reference | the standard evolves |
| `docs/` (architecture, maintenance, sovereignty, host-session, verification, measurement, proposals) | 13 | a maintainer | Reference / Snapshot | varies per file |
| `docs/bugfixes/` | 20 | a maintainer diagnosing a recurrence | Snapshot | at the event |
| `docs/audits/` | 1 (+ this file) | a maintainer | Snapshot | at the event |
| `.ai/` | 15 | an AI session and the maintainer | State / operative summary | per session |
| AI adapters (`AGENTS.md`, `CLAUDE.md`, Copilot, Cursor) | 4 | an AI tool | Reference | governance change |
| `.github/` templates and guidance | 5 | a contributor opening a PR | Reference | process change |
| `site/src/content/docs/` | 18 | a customer who has never seen this repository | Live | the guided path changes |
| `site/README.md` | 1 | a contributor editing the site | Reference | site convention change |

### Representative full classifications

Files whose sections carry materially different purposes are classified per
section.

**`README.md`**

```text
Path:                 README.md
Primary readers:      someone evaluating the project; someone adopting it for the first time
Document type:        Live
Primary purpose:      what this repository is, what it contains, and how to reach a first working state
Section purposes:     Features/Security Model = overview · Quick Start = installation ·
                      Requirements = prerequisites · What's Included = catalogue with status ·
                      Project Structure/Conventions = orientation · Roadmap/Contributing/License = reference
Canonical facts here: public status symbol for core/ and apps/ (per File Map); repository layout
Facts used elsewhere: status definitions (status-model.md) · standards (docs/standards/) ·
                      direction (ROADMAP.md) · per-stack setup (stack README)
Update trigger:       any user-visible change, same commit
Concerns:             F-01 (P0), F-04, F-07, F-09, F-18
```

**`ROADMAP.md`**

```text
Path:                 ROADMAP.md
Primary readers:      someone deciding whether the project is going where they need
Document type:        Plan
Primary purpose:      what is planned, and what is deliberately not
Section purposes:     Shipped = history (contested) · Since v0.6.0 = history + narration (contested) ·
                      Direction = plan · Backlog/Evaluating = plan · Out of scope = boundary
Canonical facts here: direction and planned work; licence policy; scope boundaries
Facts used elsewhere: shipped work (CHANGELOG.md) · per-stack status (README/category README)
Update trigger:       an item ships or becomes irrelevant → same commit; direction reviewed monthly
Concerns:             F-05, F-06, F-11
```

**`TROUBLESHOOTING.md`**

```text
Path:                 TROUBLESHOOTING.md
Primary readers:      an operator with a failing stack in front of them
Document type:        Live
Primary purpose:      recognise an observed symptom and reach its fix
Section purposes:     1–8 = symptom → cause → fix · "Lessons Learned" (title) = history
Canonical facts here: the symptom catalogue and its fixes
Facts used elsewhere: incident detail (docs/bugfixes/) · debugging method (standards/troubleshooting.md)
Update trigger:       a new reproducible symptom is established
Concerns:             F-08, F-09, F-10
```

**Stack README family** (62 files, `apps/nextcloud/README.md` as reference)

```text
Primary readers:      an operator deploying that stack
Document type:        Live
Primary purpose:      reach a working, verified, backed-up instance of this stack
Section purposes:     Setup = installation · Verify = verification · Security model = reference ·
                      Known issues = current limitations · Backup = operations
Canonical facts here: per-app setup; known issues; backup procedure for that stack
Facts used elsewhere: pinned version (.env.example) · status (root or category README) ·
                      baseline rules (security-baseline.md) · deviations (UPSTREAM.md)
Update trigger:       any change to that stack, same commit
Concerns:             F-13, F-14, F-16, F-19
```

**`site/src/content/docs/**`** (18 pages)

```text
Primary readers:      a customer who has never seen this repository
Document type:        Live
Primary purpose:      follow a guided path to a working service without reading the source
Section purposes:     framing · Installation · Verify · Going further · Troubleshooting · Updates · Reference
Canonical facts here: the guided sequence itself, and the authored per-stack "not exercised" note
Facts used elsewhere: status/version/date (generated, via StackStatus) · commands (stack README)
Update trigger:       the guided path changes
Concerns:             F-03, F-15, F-17, F-20, F-21, F-22
```

**`.ai/` family** (15 files)

```text
Primary readers:      an AI session; the maintainer between sessions
Document type:        State (state, tasks, progress) / operative summary (domains, rules, routing)
Primary purpose:      resume work without re-deriving context
Canonical facts here: open decisions, active constraints, session state
Facts used elsewhere: everything else — by declaration, `.ai/` owns no repository fact
Update trigger:       per session (Session Chain step 4)
Concerns:             F-02 (P1), F-12, F-23
```

---

## 6. Existing strengths

Recorded because later work should preserve these patterns, not because the
audit needs balance.

| Strength | Evidence |
|---|---|
| **Generation instead of repetition, end to end** | `UPSTREAM.md` + `.env.example` + README status → `lifecycle-report.py` → `LIFECYCLE.md` → `site/src/data/lifecycle.json` → `<StackStatus>`; CI fails on drift. No status, version or date on the operator site is retyped |
| **Named limitations instead of hedging** | `site/.../seafile-pro.mdx:207` states the exact gap ("No backup or restore procedure has been tested … Do not treat this installation as production-ready") rather than a generic disclaimer |
| **Register discipline is real** | Repository-wide searches for "production-ready", "battle-tested", "may potentially", "should carefully evaluate", "at your own risk" return one legitimate qualified use each and no marketing claims |
| **Reference done correctly** | `README.md` *Roadmap* is one sentence and a link — the pattern the ownership model asks for |
| **The FAQ anchor chain works** | `<StackStatus>` links to `/faq/#what-do-the-status-labels-mean`; the FAQ generates that anchor from the question text |
| **`no-new-privileges` claim is supported** | 122 of 124 services; the two exceptions are registered in `check-baseline.py` with justifications |
| **Per-stack backup sections are specific** | 58 of 59 stacks; the non-obvious cases (three Seafile databases, Vaultwarden `rsa_key*`, Immich vector extension) are stated rather than implied |

---

## 7. Systemic findings

| # | Systemic problem | Mechanism | Findings |
|---|---|---|---|
| S1 | **Hand-typed copies of generated facts** in files that name the generator as owner in the same paragraph | Nothing regenerates the prose sentence, and no checker reads it | F-02, F-12 |
| S2 | **The highest-traffic path is the least verified** | Stack READMEs are exercised on hosts; the root Quick Start is read by newcomers and by nobody who already knows the stack | F-01, F-04 |
| S3 | **Claims aggregated across services** on the customer surface, where the owning standard grades per service | A summary compresses "Required" and "Recommended" into one list | F-03, F-18 |
| S4 | **Two documents on one subject with no declared split** | Both were correct when written; neither references the other, so the split lives only in `.ai/state.md` as an open decision | F-08, F-09, F-10 |
| S5 | **History accumulating inside plan documents** | A plan document is the convenient place to record what happened, and nothing moves it out | F-05, F-06, F-11 |
| S6 | **Maintainer working state reachable from reader-facing documents** | Links added while the working file was the freshest source | F-06, F-07 |

---

## 8. Information-owner analysis

### 8.1 Validated owner map

| Fact | Canonical owner | Correct dependants | Verified |
|---|---|---|---|
| Status definitions | `docs/standards/status-model.md` | README legend, `LIFECYCLE.md`, site FAQ | ✅ consistent |
| Public status — `core/`, `apps/` | root `README.md` | `LIFECYCLE.md`, `lifecycle.json`, site | ✅ `lifecycle-report.py --check` passes |
| Public status — `business/`, `monitoring/`, `backup/` | category README | root README, `LIFECYCLE.md` | ✅ passes |
| Pinned version | `<stack>/.env.example` | `LIFECYCLE.md`, site `StackStatus` | ⚠️ one manual copy — F-15 |
| Last verified date | `<stack>/UPSTREAM.md` | `LIFECYCLE.md`, site | ⚠️ field format split — F-13 |
| Security baseline rules | `docs/standards/security-baseline.md` | every compose; README Security Model; site `/project/` | ❌ F-03, F-18 |
| Shipped work | `CHANGELOG.md` | — | ❌ F-05 |
| Direction | `ROADMAP.md` | category READMEs reference | ✅ |
| Per-app setup | `<stack>/README.md` | root README one-liner; site guide | ⚠️ F-01 contradicts it |
| Symptom → fix | `TROUBLESHOOTING.md` | — | ❌ no declared split with the standards file — F-08 |
| Stack counts / progress numbers | `LIFECYCLE.md` (generated) | `.ai/state.md` claims to derive | ❌ F-02 |
| Legacy stamp count | measurable from `UPSTREAM.md` | `.ai/state.md`, `.ai/risks.md` | ❌ F-12 |
| Documentation rules | `documentation-workflow.md` + `writing-style.md` | `AGENTS.md`, `.ai/*`, `site/README.md` | ✅ post-Phase 3 |

### 8.2 Repetition classified

| Repeated fact | Where | Mode | Verdict |
|---|---|---|---|
| Status symbol per stack | root README ↔ category README ↔ `LIFECYCLE.md` | canonical + generated | correct |
| Version pin | `.env.example` → `LIFECYCLE.md` → site badge | generated | correct |
| Version `5.13.26` | `site/.../invoiceninja.mdx:102` | **prohibited duplication** | F-15 |
| Baseline defaults | `security-baseline.md` → README Security Model → site `/project/` | summary, one of them unsupported | F-03 (site), F-18 (README framing) |
| Shipped releases | `CHANGELOG.md` ↔ `ROADMAP.md` *Shipped* | **prohibited duplication** | F-05 |
| Stack counts | `LIFECYCLE.md` → `.ai/state.md` | **prohibited duplication** | F-02 |
| Legacy stamp count | measurement → `.ai/state.md`, `.ai/risks.md` | **prohibited duplication** | F-12 |
| Vaultwarden secret procedure | stack README ↔ site guide ↔ root Quick Start | two agree, one contradicts | F-01 |
| SLA response times | `SECURITY.md` → site `/project/` | summary | correct — values match |
| Backup procedure per stack | stack README ↔ `UPSTREAM.md` | already caught by `backup-docs-split` WARN | correct |
| Troubleshooting symptoms | `TROUBLESHOOTING.md` ↔ `docs/standards/troubleshooting.md` | undeclared overlap | F-08 |

### 8.3 Facts with no clear owner

| Fact | Currently stated in | Missing |
|---|---|---|
| Which of the two troubleshooting documents owns a symptom | both | a declared split; no File Map row exists for either |
| How many stacks carry the legacy verification field | `.ai/state.md`, `.ai/risks.md`, measurable from disk | no owner; the checker reports it only for ✅ stacks, so the two prose copies cannot be validated |
| Which stacks the operator site covers, and why those | site sidebar (hand-maintained), `astro.config.mjs` | no source; adding a guide requires editing navigation by hand with nothing checking coverage |

---

## 9. Root and category documentation findings

### F-01 — Root Quick Start cannot be followed (**P0**)

```text
Finding ID:        F-01
File:              README.md
Heading:           ## Quick Start (lines 35–60)
Issue category:    Missing actionable result / wrong procedure (N, S, U)
Affected reader:   someone adopting the project, running its first commands
Section purpose:   reach a first working state
Observed content:  `git clone https://github.com/your-user/secure-docker-blueprint.git`
                   … `mkdir -p .secrets`
                   `openssl rand -base64 32 | tr -d '\n' > .secrets/db_pwd.txt`
                   `openssl rand -base64 32 | tr -d '\n' > .secrets/db_root_pwd.txt`
Why it deviates:   Three independent defects in one block.
                   (a) `your-user` is a placeholder; the repository is `rubennati/…`,
                       named correctly three times elsewhere in the same file.
                   (b) `apps/vaultwarden` reads `DB_PASSWORD` / `DB_ROOT_PASSWORD`
                       from `.env`. `grep -rn db_root_pwd apps/vaultwarden/` returns
                       nothing; `.secrets/db_pwd.txt` appears only in that stack's
                       borgmatic example, whose own text states "The credential file
                       does not exist yet." The reader creates two unused files and
                       leaves the values the stack needs unset.
                   (c) base64 for a stack whose password is embedded in
                       `DATABASE_URL` — the failure `TROUBLESHOOTING.md` 2.3
                       documents ("Avoid `openssl rand -base64` for DSN passwords").
                       The stack README (:59–61) and the site guide (:45–46) both
                       use `openssl rand -hex 32` written into `.env`.
Correct destination: the procedure owned by `apps/vaultwarden/README.md`
Recommended action:  replace the example with the stack's own procedure, or point
                     to it; fix the clone URL
Severity:          P0    Effort: S    Risk: Low
Dependencies:      none — the correct text already exists in two places
```

### F-04 — "Quick Start" promises a shorter path that does not exist (P2)

`README.md:35`. Per the section contract established in Phase 2, `Quickstart` is
reserved for an optional, objectively shorter entry beside a full installation.
The README has no fuller path; this block is the installation. Category P
(incorrect section contract). The identical correction was already applied to
the site convention in `site/README.md`. Effort XS, Risk Low.

### F-07 — Reader-facing files link to maintainer working state (P2)

`ROADMAP.md:82` and `:144` send the reader to `docs/host-session-v0.7.0.md`;
`CHANGELOG.md:27` and `:34` describe `docs/host-session-plan.md` and
`docs/host-session-v0.8.0.md` as shipped items. Those are ordered runbooks for
the maintainer's next session. Category G (working-state leakage). The reader of
a roadmap needs the milestone and its precondition, not the run order.
Effort S, Risk Low.

### F-09 — `TROUBLESHOOTING.md` is unreachable from the root README (P2)

`grep -n "TROUBLESHOOTING" README.md` returns nothing. A 470-line symptom
catalogue, maintained across seven bugfix cycles, is reachable only from
`.ai/routing.md` — an internal file — and from the site's per-stack
troubleshooting sections. Category T (information scent). Effort XS, Risk Low.

### F-18 — README Security Model frames graded rules as uniform (P2)

`README.md:61` — "Every service in this blueprint **enforces**:" over a table
whose rows then qualify themselves ("where the image supports it", "where
possible"). Measured: `no-new-privileges` 122/124, `cap_drop` 30/124,
`read_only: true` 17/124. The rows are accurate; the framing sentence is not.
Category U. Effort XS, Risk Low.

### F-24 — Category coverage is uneven and unexplained (P3)

`business/`, `monitoring/`, `backup/` have category READMEs that own their
stacks' status; `core/` and `apps/` deliberately do not. The exception is
recorded in `docs/maintenance.md` and `status-model.md` — correctly — but a
reader of the root README meets 47 `core/` and `apps/` rows with no category
page and no statement that none exists. Category N. Effort XS, Risk Low.

---

## 10. Stack documentation findings

### F-13 — Two verification-field formats across 60 `UPSTREAM.md` files (P2)

Measured: 29 files carry only `Last verified`, 30 only the pre-v0.5.1
`Last checked`, 1 carries both. `LIFECYCLE.md` marks the legacy field ⚠️, and
`lifecycle-report.py` reports `legacy-stamp` **only for stacks claiming ✅** —
which is why the run is currently at 0 warnings while 30 files still carry the
old field. The format is a documented ✅ criterion, so the split is a real
maintenance signal that the checker cannot see for 🚧 stacks. Effort M (per-app
judgement, not a rewrite), Risk Low, depends on host-session evidence.

### F-14 — 18 of 62 stack READMEs have no verification section (P2)

No heading matching verify / check that / smoke test / health. The section
contract for a stack README includes "determine whether the result is correct";
without it the operator has an installation and no success criterion. Category O
(missing verification). Effort L (spread across 18 stacks — split per category),
Risk Low.

### F-16 — Two stack files send the reader to a branch a normal clone lacks (P2)

`apps/adminer/README.md:90` — "reference compose and rationale live under
`docs/apps/adminer/setup-notes.md` on the repository's `docs` branch";
`apps/adminer/UPSTREAM.md:23` — "preserved in the `docs` branch notes". The
operative summary in `.ai/domains/documentation.md` forbids exactly this ("No
links from public files to material a normal clone does not contain"). Category
M (meta-documentation) plus a dead end. Effort XS, Risk Low.

`docs/standards/commit-rules.md:10` and `:366` also name the `docs` branch, but
as a rule about where German drafts go — that is the branch model itself, in the
document that owns it. Not a defect.

### F-19 — Development narration inside stack READMEs (P3)

`apps/nextcloud/README.md:554` — "Confirmed on the running instance rather than
assumed." The operator needs the value and its effect; how it was established
belongs to the host-session findings. Sampled pattern, not a sweep. Effort XS
per occurrence, Risk Low.

### F-25 — `CONFIG.md` is referenced as a pattern but exists once (P3)

`CONTRIBUTING.md:13` and `.github/pull_request_template.md` both name `CONFIG.md`
as an expected artefact for complex apps; one exists
(`apps/paperless-ngx/CONFIG.md`). Either the expectation or the inventory is out
of date. Effort XS (decide and state), Risk Low.

---

## 11. Roadmap, changelog, lifecycle and status findings

### F-02 — `.ai/state.md` publishes stale counts of a generated fact (**P1**)

```text
Finding ID:        F-02
File:              .ai/state.md
Heading:           ## Snapshot (line 15)
Issue category:    Prohibited duplication of a changing fact
Affected reader:   every AI session — step 2 of the documented start sequence
Section purpose:   where the project is right now
Observed content:  "59 stacks tracked. 39 `ready`, 20 `preview`, **0 `ops-ready`** …
                    Numbers come from `LIFECYCLE.md`; regenerate rather than
                    editing them here."
Why it deviates:   `LIFECYCLE.md:7`, the generated owner, reports
                   "59 stacks: 0 ops-ready · 21 ready · 38 preview".
                   The mirror is wrong by 18 stacks and names its own owner in
                   the same paragraph. Nothing regenerates prose, and no checker
                   reads it.
Canonical owner:   LIFECYCLE.md (generated from the status-model sources)
Recommended action: replace the counts with a reference; keep the qualitative
                    statement that no stack is ops-ready if it is needed there
Severity:          P1    Effort: XS    Risk: Low
Dependencies:      none
```

### F-05 — `ROADMAP.md` carries a second changelog (P2)

Lines 9–46, seven `### vX.Y.Z — … (date)` sections with prose summaries of what
shipped. The File Map assigns shipped work to `CHANGELOG.md` and direction to
`ROADMAP.md`. Two hand-maintained versions of the same changing history.
Category F (changelog leakage) + prohibited duplication. A short "shipped so far"
line with a link is a legitimate summary; seven dated prose sections are an
independent version. Effort S, Risk Low.

### F-06 — "Since v0.6.0 — work outside the plan" is session narration in a plan (P2)

`ROADMAP.md:47–60`. "Between 2026-06-04 and 2026-07-26 the repo grew in
directions this document did not name. **Recorded here so the milestones below
stay honest.**" That sentence explains the author's reason for writing the
section — category C (author reasoning) — and the table records shipped work —
category B/F. The reader of a roadmap needs what is planned. Effort S, Risk Low.

### F-11 — Roadmap entries carry per-stack version status (P3)

`ROADMAP.md:144` lists nine pending major bumps and states "Each is marked `🚧`
in `docs/maintenance.md`". Version state per stack is owned by `.env.example` and
surfaced by `LIFECYCLE.md`; `docs/maintenance.md` is the process document, not
the status owner. A summary is legitimate here; the specific ownership claim is
not. Effort XS, Risk Low.

### F-12 — Two files repeat an unverifiable count (P2)

`.ai/state.md:121` and `.ai/risks.md:10` both state "22 stacks" carry the legacy
verification stamp. Measured on disk: 30 files carry only `Last checked`, 31
including the mixed one. The checker reports 0 because its rule is scoped to ✅
stacks. Three numbers, no owner. Effort XS, Risk Low. Depends on F-13 for the
decision about what the number should mean.

---

## 12. Architecture, standards, maintenance, audit and bugfix findings

### F-08 — Two troubleshooting documents, no declared split (P2)

```text
Finding ID:        F-08
Files:             TROUBLESHOOTING.md (470 lines) · docs/standards/troubleshooting.md (472 lines)
Issue category:    Competing sources of truth (Q, S4)
Affected reader:   an operator with a failing stack; a contributor debugging
Purpose (root):    recognise a symptom, reach its fix
Purpose (standard): a layered inside-out debugging method
Observed content:  overlap measured by term — Tailscale 5 / 20 occurrences,
                   IPv6 5 / 11, 403 4 / 8, Mixed Content 1 / 4. The standards
                   file carries "Common router problems" and "Certificate
                   problems" catalogues alongside its method.
Why it deviates:   Neither document references the other. `grep` across both,
                   the root README and `docs/standards/` finds no cross-link;
                   the only place the pair is named together is `.ai/routing.md`
                   and an open decision in `.ai/state.md`. Neither has a File Map
                   row, so no owner is defined for a symptom.
Recommended action: declare the split at both headers and add a File Map row;
                    move whichever catalogue is duplicated to the symptom owner
Severity:          P2    Effort: M    Risk: Medium (both files are actively used)
Dependencies:      resolves open decision 2 in .ai/state.md
```

### F-10 — `TROUBLESHOOTING.md` title promises two contracts (P3)

"Troubleshooting **& Lessons Learned**". Diagnosis and history are different
section objectives with different owners (`docs/bugfixes/`, `.ai/errors.md`).
Category P. Effort XS, Risk Low. Best done with F-08.

### F-20 — `docs/maintenance.md` mixes process with a dated snapshot (P3)

The "Dependency Sweep — 2026-07-26" section (lines ~200–247) is a point-in-time
inventory inside a document whose purpose is the process. The Progress Log below
it is declared as an owner by the standard and is not a defect; the sweep
snapshot has the shape of `docs/audits/` content. Effort S, Risk Low.

### F-21 — Four host-session documents with overlapping purposes (P3)

`docs/host-session-plan.md`, `-findings.md`, `-v0.7.0.md`, `-v0.8.0.md`. Plan,
findings and two ordered runs; the plan file also contains "Rules established
this session" and a backlog. Maintainer files, so narrative is permitted — but a
maintainer returning after a gap has four candidate entry points and no stated
order. Effort S (a header line each), Risk Low.

---

## 13. AI-workspace and instruction findings

### F-23 — Adapter files do not carry the documentation entry (P3)

`CLAUDE.md`, `.github/copilot-instructions.md` and `.cursor/rules/00-project.mdc`
each carry four rules, one of which is documentation-related ("Update
documentation in the same change set"). Since Phase 3 the eight hard rules live
in `AGENTS.md`, which those files point to. This is the designed layering and
not a contradiction; it is recorded because a tool that loads only its own
adapter never sees rules 1–8. Deliberate trade-off — the alternative is
duplication across four files. **No action recommended**; recorded so the
decision is visible.

`.ai/tasks.md:52` still lists the troubleshooting-overlap decision as open, which
is consistent with `.ai/state.md`. Consistent, not a finding.

---

## 14. Operator-site findings

### F-03 — `/project/` states an unsupported cross-service default (**P1**)

```text
Finding ID:        F-03
File:              site/src/content/docs/project/index.md
Heading:           ## The defaults
Issue category:    Unsupported claim (U) + cross-surface inconsistency (S)
Affected reader:   a customer deciding whether to adopt the Blueprint
Section purpose:   what the compose files are set to, across services
Observed content:  "- `cap_drop: ALL` and `no-new-privileges`, plus `read_only`
                    where the image runs under it"
Why it deviates:   Measured across the 56 tracked stack compose files (124
                   services): no-new-privileges 122 (98 %, two registered
                   exceptions) — supported. cap_drop 30 (24 %). read_only 17
                   (14 %), and that row carries its own qualifier so it holds.
                   The owning standard, security-baseline.md, lists
                   no-new-privileges under "Required for Every Service" and
                   capability drop under "Recommended". The site presents a
                   graded rule as a uniform default.
Canonical owner:   docs/standards/security-baseline.md
Recommended action: state the required default as required and the recommended
                    ones as what they are, or drop cap_drop from the list
Severity:          P1    Effort: XS    Risk: Low
Dependencies:      shares its cause with F-18 (README framing)
```

### F-15 — A version number typed by hand on the site (P2)

`site/src/content/docs/applications/invoiceninja.mdx:102` contains `:5.13.26`.
It matches `business/invoiceninja/.env.example` today. Every other version on
the site is generated through `StackStatus`; this one can drift silently at the
next bump. Category: prohibited duplication. Effort XS, Risk Low.

### F-17 — `/operations/` promises a scope it does not carry (P3)

The page states "The recurring work of keeping a running stack healthy" and then
offers one link, to backup and restore. Update handling, log rotation,
certificate renewal and monitoring exist in the repository and are not named,
not even as absent. Category N. Effort S, Risk Low.

### F-22 — Site coverage has no source and no checker (P2)

Four of 59 stacks have guides; three core services; the selection lives in
`astro.config.mjs` as a hand-written sidebar. Adding a stack to the repository
changes nothing on the site, and nothing reports the gap — the same class of
blind spot that `check-coverage.py` was written for on the repository side.
Category S. Effort M, Risk Medium (touches build tooling — out of scope for a
documentation batch, recorded for sequencing).

---

## 15. Navigation and information-scent findings

| # | Finding | Evidence | Severity |
|---|---|---|---|
| F-09 | The symptom catalogue is not linked from the front page | `grep -n TROUBLESHOOTING README.md` → no match | P2 |
| F-26 | The site home page title is a slogan, not a result | `site/.../index.mdx` `title: "Running the service is the easy part. Operating it is the challenge."` — this string becomes the browser tab, the sitemap entry and the `llms.txt` line for the home page | P3 |
| F-27 | Sidebar groups follow the repository taxonomy | "Core Infrastructure" and "Applications" are the repository's directory split; a customer arrives with "I want a password manager", not with "I need a core service". The `/project/` page states this taxonomy is deliberately absent from guides, and the navigation reintroduces it | P3 |
| F-24 | 47 stacks have no category page; the front page does not say so | root README `### Core Infrastructure` / `### Applications` tables | P3 |

---

## 16. Cross-surface consistency findings

| Subject | Repository | Site | Verdict |
|---|---|---|---|
| Vaultwarden secret generation | stack README `openssl rand -hex 32` → `.env` | identical | ✅ agree; the **root README** contradicts both — F-01 |
| Status, version, verification date | owners per status-model | generated via `StackStatus` | ✅ single chain |
| Baseline defaults | graded Required / Recommended | flat list | ❌ F-03 |
| Invoice Ninja version | `.env.example` | hand-typed `:5.13.26` | ❌ F-15 |
| Security response times | `SECURITY.md` 7 / 14 days | `/project/` 7 / 14 days | ✅ agree |
| Limitations | per-stack Known Issues | per-stack authored note | ✅ same shape, different wording — correct per surface |
| Troubleshooting | two documents, undeclared split | per-stack sections linking to `/core/traefik/#troubleshooting` | ⚠️ the site's transition into the repository is clear; the repository's internal split is not — F-08 |

---

## 17. Prose-check interpretation

`python3 scripts/ci/check-prose.py` → 63 occurrences, 27 blocking, 36 warnings.
Distribution: evaluation in place of a value 17, self-justification 15, stage
direction 9, dramatic emphasis 6, author's expectation 6, software with
intentions 5, aphorism 5.

The differential gate is green: no line changed in the working tree carries a
finding.

Sample classified by cause rather than by phrase:

| Occurrence | Classification | Consequence |
|---|---|---|
| `CHANGELOG.md:30, :31, :37` — "deliberately not", "rather than assumed", "the point is that" | **7 — false positive by document purpose.** The hint text ("belongs in CHANGELOG.md") fires inside `CHANGELOG.md`; a changelog entry legitimately states what a change did and did not do | leave; the checker's file classification, not the text, is the mismatch |
| `site/.../sovereignty/index.mdx` — 7 findings on one page, incl. "Two things to read out of it" | **2 — purpose drift.** Density on one page indicates an essayistic register on a customer surface, not seven slips | treat as one page-level package, not seven replacements |
| `site/.../operations/backup.mdx:29` — "That last one surprises people" | **3 — author-centric writing** on the customer surface | delete the clause |
| `apps/nextcloud/README.md:554` — "Confirmed on the running instance rather than assumed" | **5 — the sentence is unnecessary** in a stack README; provenance belongs to the host-session findings | delete (F-19) |
| `apps/nextcloud/README.md:556` — "The one value worth knowing is …" | **1 — local wording** | rephrase when the paragraph is next touched |
| `apps/_reference/README.md:111` — "Both secret patterns appear in one place, which is the point" | **1 — local wording.** The fact serves the reader; the trailing clause does not | trim the clause |
| `core/crowdsec/README.md:243` — "rather than a default nobody looked at" | **1 — local wording** | rephrase |
| `backup/borgmatic/README.md` — 2 findings | **4 — misplaced rationale**, pending inspection of the surrounding paragraph | unresolved pending verification |

The 14 site findings and the 3 changelog findings account for 17 of the 27
blocking occurrences. Neither group should be resolved by phrase substitution:
one is a page-register question, the other is a checker-classification question.

---

## 18. Prioritised finding register

| ID | Title | Cat. | Sev | Eff | Risk | Files |
|---|---|---|---|---|---|---|
| F-01 | Root Quick Start cannot be followed | N/S/U | **P0** | S | Low | `README.md` |
| F-02 | `.ai/state.md` stale generated counts | dup | **P1** | XS | Low | `.ai/state.md` |
| F-03 | Site states unsupported cross-service default | U/S | **P1** | XS | Low | `site/.../project/index.md` |
| F-05 | Roadmap carries a second changelog | F | P1 | S | Low | `ROADMAP.md` |
| F-08 | Two troubleshooting documents, no split | Q | P1 | M | Med | both troubleshooting files, `docs/maintenance.md` |
| F-12 | Unverifiable legacy-stamp count in two files | dup | P1 | XS | Low | `.ai/state.md`, `.ai/risks.md` |
| F-04 | "Quick Start" section contract | P | P2 | XS | Low | `README.md` |
| F-06 | Session narration in the roadmap | B/C | P2 | S | Low | `ROADMAP.md` |
| F-07 | Reader-facing links into host-session files | G | P2 | S | Low | `ROADMAP.md`, `CHANGELOG.md` |
| F-09 | Symptom catalogue unlinked from README | T | P2 | XS | Low | `README.md` |
| F-13 | Two verification-field formats | drift | P2 | M | Low | 31 × `UPSTREAM.md` |
| F-14 | 18 stack READMEs without verification | O | P2 | L | Low | 18 stack READMEs |
| F-15 | Hand-typed version on the site | dup | P2 | XS | Low | `site/.../invoiceninja.mdx` |
| F-16 | `docs`-branch dead ends in a stack | M | P2 | XS | Low | `apps/adminer/*` |
| F-18 | README baseline framing | U | P2 | XS | Low | `README.md` |
| F-22 | Site coverage has no source | S | P2 | M | Med | `astro.config.mjs`, site content |
| F-10 | Title promises two contracts | P | P3 | XS | Low | `TROUBLESHOOTING.md` |
| F-11 | Per-stack version status in the roadmap | dup | P3 | XS | Low | `ROADMAP.md` |
| F-17 | `/operations/` scope vs. content | N | P3 | S | Low | `site/.../operations/index.md` |
| F-19 | Development narration in stack READMEs | B | P3 | XS | Low | sampled stack READMEs |
| F-20 | Dated sweep inside the process document | P | P3 | S | Low | `docs/maintenance.md` |
| F-21 | Four host-session entry points | T | P3 | S | Low | `docs/host-session-*.md` |
| F-24 | 47 stacks without a category page | N | P3 | XS | Low | `README.md` |
| F-25 | `CONFIG.md` expectation vs. inventory | N | P3 | XS | Low | `CONTRIBUTING.md`, PR template |
| F-26 | Site home title is a slogan | T | P3 | XS | Low | `site/.../index.mdx` |
| F-27 | Sidebar follows repository taxonomy | T | P3 | M | Med | `astro.config.mjs` |
| F-23 | Adapters carry no documentation entry | — | — | — | — | recorded, no action |

**Totals: 1 × P0 · 5 × P1 · 12 × P2 · 9 × P3** (F-23 recorded without severity).

---

## 19. Dependency map

```text
F-01 (Quick Start)          → independent, unblocks nothing, blocked by nothing
F-04, F-09, F-18, F-24      → same file as F-01; batch to avoid three edits to README.md

F-02 ─┬→ F-12 (both are hand-typed counts in .ai/; one decision covers both)
      └→ depends on nothing; LIFECYCLE.md already generated

F-13 (field format) ────────→ F-12 (defines what the count means)
                            → needs host-session evidence per app; do not batch with F-02

F-05 ─┬→ F-06 (same file, same cause)
      ├→ F-07 (roadmap half)
      └→ F-11
      CHANGELOG.md half of F-07 rides along

F-08 ─┬→ F-10 (same file family)
      └→ requires a File Map row → touches docs/maintenance.md (owner)

F-03 ←→ F-18   same claim on two surfaces; fix the owner reading first, then both

F-15 ────────→ independent
F-22 ────────→ blocks nothing; enables a future site-coverage checker
F-27, F-26 ──→ site navigation; do after F-22 decides what the site covers
F-14 ────────→ 18 files; split per category, no dependencies
```

---

## 20. Implementation packages

### PKG-1 — Repair the root README entry path

```text
Package ID:     PKG-1
Title:          Repair the root README entry path
Problem solved: The first commands a new reader runs cannot work
Reader impact:  Someone adopting the project reaches a working Traefik + first app
Files in scope: README.md
Canonical owner affected: apps/vaultwarden/README.md (the procedure), root README (the pointer)
Out of scope:   the What's Included tables, Project Structure, Conventions;
                any change to apps/vaultwarden itself
Dependencies:   none
Steps:          1. Correct the clone URL to the repository's own path
                2. Replace the Vaultwarden secret block with the stack's own
                   procedure (hex into .env) or a pointer to it
                3. Rename the section to Installation (F-04)
                4. Reword the Security Model framing to match the graded standard (F-18)
                5. Add one link to TROUBLESHOOTING.md where a failing first run would
                   send the reader (F-09)
                6. State that core/ and apps/ are documented per service, not per
                   category (F-24)
Verification:   run the corrected block end to end on a clean clone;
                check-links.py; check-prose.py --changed-only --base HEAD
Acceptance:     every command in the section executes as written; no `.secrets/`
                file is created that the target stack does not read
Effort: S   Risk: Low   Resolves: F-01, F-04, F-09, F-18, F-24
```

### PKG-2 — Remove hand-typed counts from `.ai/`

```text
Package ID:     PKG-2
Title:          Remove hand-typed counts of generated facts from .ai/
Problem solved: Every session starts from numbers that contradict the generated owner
Reader impact:  An AI session reads a correct snapshot or none
Files in scope: .ai/state.md, .ai/risks.md
Canonical owner affected: LIFECYCLE.md (generated)
Out of scope:   the open-decision list; anything the counts are used to argue
Dependencies:   none
Steps:          1. Replace the stack counts in state.md with a reference to LIFECYCLE.md
                2. Replace the "22 stacks" claim in state.md and risks.md with either a
                   reference to the measurable source or a qualitative statement
                3. Leave the ops-ready = 0 statement if the milestone argument needs it
Verification:   compare every remaining number in .ai/ against its owner;
                lifecycle-report.py --check; check-prose.py --changed-only
Acceptance:     no count in .ai/ that a generator owns
Effort: XS   Risk: Low   Resolves: F-02, F-12
```

### PKG-3 — Align the baseline claim on both surfaces

```text
Package ID:     PKG-3
Title:          State the security baseline as graded, on both surfaces
Problem solved: A customer-facing page claims a default 30 of 124 services hold
Reader impact:  A reader evaluating the Blueprint can rely on what the list says
Files in scope: site/src/content/docs/project/index.md (+ README.md if PKG-1 has not run)
Canonical owner affected: docs/standards/security-baseline.md
Out of scope:   changing any compose file; changing the standard itself
Dependencies:   PKG-1 covers the README half; run PKG-3 after or fold the README line in
Steps:          1. Read the Required / Recommended split at the owner
                2. Restate the site list so required and recommended are distinguishable
                3. Re-measure before publishing the numbers, if numbers are used
Verification:   npm run build in site/; the measurement command in section 24
Acceptance:     no statement on either surface that the configuration does not support
Effort: XS   Risk: Low   Resolves: F-03, F-18 (if not already in PKG-1)
```

### PKG-4 — Return the roadmap to direction

```text
Package ID:     PKG-4
Title:          Return ROADMAP.md to planned work
Problem solved: A plan document carries a second changelog and session narration
Reader impact:  Someone assessing direction is not reading release history
Files in scope: ROADMAP.md, CHANGELOG.md (link removal only)
Canonical owner affected: CHANGELOG.md (shipped work)
Out of scope:   rewriting CHANGELOG entries; changing milestone content or order
Dependencies:   none
Steps:          1. Replace the seven Shipped sections with a short summary and a link
                2. Remove "Since v0.6.0 — work outside the plan"; anything not already
                   in CHANGELOG.md moves there first
                3. Remove links to docs/host-session-*.md from ROADMAP and CHANGELOG;
                   state the precondition instead of the runbook
                4. Correct the ownership claim at line 144
Verification:   check-links.py; confirm no shipped item lost — diff the removed
                sections against CHANGELOG before deleting
Acceptance:     ROADMAP contains no dated shipped section and no link to a
                host-session file
Effort: S   Risk: Low   Resolves: F-05, F-06, F-07, F-11
```

### PKG-5 — Declare the troubleshooting split

```text
Package ID:     PKG-5
Title:          Declare which troubleshooting document owns a symptom
Problem solved: Two 470-line documents on one subject, no cross-reference, no owner
Reader impact:  An operator with a symptom lands in the right document first
Files in scope: TROUBLESHOOTING.md, docs/standards/troubleshooting.md, docs/maintenance.md
Canonical owner affected: to be established — this package creates the File Map row
Out of scope:   merging the documents; rewriting either catalogue
Dependencies:   resolves open decision 2 in .ai/state.md — confirm the decision first
Steps:          1. Confirm the intended split with the maintainer
                2. Add a scope line to the top of both files, in both directions
                3. Add one File Map row naming the owner of a symptom
                4. Retitle TROUBLESHOOTING.md if "Lessons Learned" no longer applies
                5. Move only the entries that genuinely duplicate
Verification:   check-links.py; grep both files for the sampled overlap terms and
                confirm each appears under one owner
Acceptance:     each document states what the other holds; the File Map names one owner
Effort: M   Risk: Medium   Resolves: F-08, F-10
```

### Later packages (not scheduled here)

PKG-6 verification sections for the 18 stack READMEs, split per category ·
PKG-7 `UPSTREAM.md` field-format convergence, tied to host-session evidence ·
PKG-8 site version de-duplication and `/operations/` scope · PKG-9 site coverage
source and navigation labels · PKG-10 the `docs`-branch dead ends in
`apps/adminer` · PKG-11 the sovereignty pages' register.

---

## 21. Recommended first batch

**PKG-1, PKG-2, PKG-3, PKG-4, PKG-5** — in that order.

| Package | Why first |
|---|---|
| PKG-1 | The only P0. It is the first thing a new reader executes, the correct text already exists in two other files, and it is one file with no dependencies |
| PKG-2 | Removes wrong numbers from the file every session reads second. XS effort, and it prevents the next session from reasoning off a stale snapshot |
| PKG-3 | The only unsupported claim on the customer surface. XS effort once the owner is read |
| PKG-4 | Structural: it restores the plan/history boundary that four findings share, and it removes the reader-facing links into maintainer working files |
| PKG-5 | The one systemic ownership gap where no owner exists at all. Placed last in the batch because it needs a maintainer decision before any edit |

Together they resolve the P0, four of the five P1s, and six P2s across five
independent document families. None requires a repository sweep; the largest is
one file plus a File Map row. Each establishes a pattern the later packages
reuse: correct at the owner, reference instead of copy, state the graded rule as
graded, keep history out of plans.

Excluded from the first batch, with reasons: the 18 missing verification sections
(large, no dependencies, better after PKG-1 sets the pattern), the `UPSTREAM.md`
field split (needs host evidence), the site navigation work (needs the coverage
decision in F-22 first), and every prose-register item (symptom, not cause).

---

## 22. Explicit non-goals

- No documentation outside this file was changed, and none should be changed as
  part of the audit.
- No standard, governance rule or File Map row was created or modified.
- The 27 blocking prose findings were not fixed and are not a package.
- No repository sweep, no README family rewrite, no site rework.
- Length was not treated as a defect. Three long files (`TROUBLESHOOTING.md`,
  `docs/maintenance.md`, stack READMEs above 500 lines) were examined and are
  recorded only where a purpose or ownership defect applies.
- Phase 5 was not started.

---

## 23. Open factual questions

| # | Question | Blocks |
|---|---|---|
| 1 | Which troubleshooting document should own a symptom, and which the method? | PKG-5 |
| 2 | Should the legacy `Last checked` field be converted per app, or should the checker's rule widen beyond ✅ stacks? | F-13, PKG-7 |
| 3 | Is the site's four-stack coverage a deliberate selection or a snapshot of what was written first? | F-22, PKG-9 |
| 4 | Is `CONFIG.md` still an expected artefact for complex apps, or was the pattern superseded by the stack README? | F-25 |
| 5 | Does `apps/adminer`'s `docs`-branch material still exist, and should the reference be removed or replaced? | F-16 |
| 6 | Is the "Since v0.6.0" content already fully represented in `CHANGELOG.md`? | PKG-4 step 2 |

Unverified within this audit: whether `backup/borgmatic/README.md`'s two prose
findings indicate misplaced rationale or local wording — the surrounding
paragraphs were not read in full. Recorded as unresolved rather than guessed.

---

## 24. Commands and checks used

```bash
# Preflight
git rev-parse --abbrev-ref HEAD && git status --short

# Inventory
git ls-files '*.md' '*.mdx' '*.mdc' | grep -v '^inbox/'

# Ownership drift
python3 scripts/ci/lifecycle-report.py --check
grep -n '^[0-9]* stacks' LIFECYCLE.md          # generated owner
grep -n 'stacks tracked' .ai/state.md          # mirror

# Verification-field split
for f in $(git ls-files '*/UPSTREAM.md'); do grep -l 'Last checked' "$f"; done | wc -l

# Baseline claim (56 compose files, 124 services)
git ls-files '*docker-compose.yml' | grep -E '^(core|apps|business|monitoring|backup)/' \
  | grep -v '^apps/_reference'                 # then parse services with PyYAML
python3 scripts/ci/check-baseline.py

# Quick Start verification
grep -rn 'db_root_pwd' apps/vaultwarden/       # no match
grep -nE 'openssl|hex|base64' apps/vaultwarden/README.md site/src/content/docs/applications/vaultwarden.mdx

# Register
python3 scripts/ci/check-prose.py
python3 scripts/ci/check-prose.py --hints
```

PyYAML is absent from the system interpreter; `check-structure.py`,
`check-coverage.py` and the service-level measurement ran in a temporary
virtual environment outside the repository. No repository dependency was
changed.

---

## Remediation status — 2026-07-30

Appended after the work. Everything above is the audit as written on the day; it
is not edited to read as though the defects never existed.

**Audited commit:** `d2fd9cf` · branch `dev`, worktree and index clean.

### What was implemented

Nine commits, in the order they landed:

| Commit | Change group |
|---|---|
| `270290b` | PKG-1 — the root README entry path |
| `2497216` | PKG-2 — generated lifecycle facts decoupled from `.ai/` |
| `bae8c48` | PKG-3 — the security baseline stated by its actual scope |
| `3048ced` | PKG-4 — the roadmap returned to remaining work |
| `a2e43ad` | PKG-5 — symptom index and diagnostic method separated |
| `c323316` | Repository-side pass — contradictions, missing shipped history, AI working state |
| `a70923c` | Operator-site pass — navigation, scope, copied version |
| `7d60be5` | Register pass — the 27 blocking and 32 of the warning findings |
| `d2fd9cf` | Checker and CI — per-unit matching, full-repository gate, 24 regression tests |

### Status of every finding

Verified against the current tree, not against which files changed.

| # | Status | Evidence today | Addressed by |
|---|---|---|---|
| F-01 | **Resolved** | No `your-user`, `db_root_pwd` or `rand -base64` in `README.md`; the Traefik sequence ran end to end on a clean copy | `270290b` |
| F-02 | **Resolved** | No stack count in `.ai/state.md`; it references `LIFECYCLE.md` | `2497216` |
| F-03 | **Resolved** | `/project/` groups required, conditional and per-stack controls; no cross-service claim the configuration does not hold | `bae8c48` |
| F-04 | **Resolved** | `## Installation`; no `## Quick Start` | `270290b` |
| F-05 | **Resolved** | No dated shipped section in `ROADMAP.md`; all seven releases verified present in `CHANGELOG.md` before removal | `3048ced` |
| F-06 | **Resolved** | No "Since v0.6.0" section; all five rows verified in `CHANGELOG.md` | `3048ced` |
| F-07 | **Resolved** | No `host-session` link in `ROADMAP.md`; the precondition is stated instead | `3048ced` |
| F-08 | **Resolved** | Both troubleshooting documents state their own scope and the other's; two File Map rows name the owners | `a2e43ad` |
| F-09 | **Resolved** | `README.md` links `TROUBLESHOOTING.md` where a failing first run sends the reader | `270290b` |
| F-10 | **Resolved** | Title is `# Troubleshooting`; history is pointed to `docs/bugfixes/` | `a2e43ad` |
| F-11 | **Resolved** | Per-stack status references `LIFECYCLE.md`, not the process document | `3048ced` |
| F-12 | **Resolved** | No legacy-stamp count anywhere in `.ai/` | `2497216` |
| F-13 | **Deferred — host evidence** | 30 `UPSTREAM.md` still carry only `Last checked` | — |
| F-14 | **Deferred — low priority** | 18 stack READMEs still have no verification section | — |
| F-15 | **Resolved** | No hardcoded image version in site content; the command reads `APP_TAG` from the operator's `.env` | `a70923c` |
| F-16 | **Resolved** | No `docs`-branch pointer in `apps/adminer/`; the instruction replaced it | `c323316` |
| F-17 | **Resolved** | `/operations/` states what it covers, what sits with each service, and what is not covered yet | `a70923c` |
| F-18 | **Resolved** | `README.md` Security Model carries a Scope column matching the graded standard | `270290b` |
| F-19 | **Superseded** | Covered by the register pass; the sampled sentence was deleted rather than reworded. No prose finding remains in any stack README | `7d60be5` |
| F-20 | **Deferred — low priority** | The dated dependency sweep still sits in `docs/maintenance.md` | — |
| F-21 | **Deferred — low priority** | Four `docs/host-session-*.md` files, no stated order | — |
| F-22 | **Deferred — decision required** | The reader-facing half is done: `/applications/` states that guides cover a selection and links the repository list. A mechanism reporting which stacks lack a guide is a generated-data system and a product decision | partly `a70923c` |
| F-23 | **Not a defect** | Deliberate layering: the eight hard rules live in `AGENTS.md`, which every adapter points to. Duplicating them across four files was the alternative | — |
| F-24 | **Resolved** | `README.md` states that `core/` and `apps/` are documented per service | `270290b` |
| F-25 | **Not a defect** | Re-checked: `CONTRIBUTING.md` calls `CONFIG.md` "encouraged … but not required" and the PR template says "if app has non-trivial configuration". Both conditional, both accurate | — |
| F-26 | **Resolved** | Page title names the result; the slogan remains as the on-screen hero heading | `a70923c` |
| F-27 | **Resolved** | Sidebar groups are reader goals; page titles keep the repository's terms | `a70923c` |

**19 resolved · 2 not a defect · 1 superseded · 1 host evidence · 3 low priority ·
1 decision required.**

### Decisions that remain

None can be derived from the repository. All are carried in `.ai/state.md`.

| Subject | Conflict |
|---|---|
| CPU limits | `security-baseline.md` prescribes a `cpus` per profile; `compose-structure.md` states they are not applied by default and the compose files follow that. One standard has to yield |
| Backup repository isolation | `docs/architecture.md` states one isolated repository per app as a rule; `backup/README.md` presents it as an option and recommends starting with one host-level configuration |
| Host-installed backup agent | `docs/architecture.md` promises no host-specific assumptions; `backup/borgmatic` is installed on the host by design, and the exception is unrecorded at the owner |
| Commit message format | The standard prescribes `scope: subject`; every recent commit uses conventional commits |
| Dependency automation | The three questions in `docs/renovate-proposal.md` |
| What belongs in `core/` | Three document servers fail the test `docs/architecture.md` states |
| Site coverage (F-22) | Which stacks should get a guide, and whether a checker should report the gap |

### Work needing a host

- **F-13** — converting a stack's `Last checked` to `Last verified: DATE (vX.Y.Z)`
  asserts the evidence is real. That is a judgement per app, made where the stack
  runs.
- The v0.7.0 restore, the v0.8.0 monitoring verification and the v0.9.0
  measurements are milestones rather than audit findings; `ROADMAP.md` owns them.

### Prose warnings that remain

`check-prose.py` reports **0 blocking and 16 warnings**. All sit in records:

| Where | Count | Why it stays |
|---|---|---|
| This audit file | 11 | The interpretation table quotes each finding verbatim. Rewriting the quotes removes the evidence |
| `docs/host-session-findings.md` | 3 | A findings log's subject is how something was established |
| `docs/maintenance.md` | 1 | A dated Progress Log row — rewriting it edits the record |
| `docs/standards/compose-structure.md` | 1 | States the CPU-limit decision; wording follows from the open decision above |

### Branch protection

`Docs QA` must be configured as a **required check** for the full prose gate to
prevent a merge. Until then the job reports without blocking, together with
`Checker coverage` and `Workflow supply chain`. This is a repository setting, not
a file in here.

### Verification at closeout

| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts/ci` | 24 tests, OK |
| `check-prose.py` | 0 blocking · 16 warnings · exit 0 |
| `check-prose.py --hints` | exit 0 |
| `markdownlint-cli2` | 0 issues |
| `check-links.py` | 223 files, 0 broken links |
| `check-baseline.py` | 56 files, no violations |
| `lifecycle-report.py --check` | 59 stacks, 0 failures |
| `check-structure.py` | 58 apps, 0 failures, 0 warnings |
| `check-coverage.py` | 0 failures, 1 known warning (`backup/borgmatic`) |
| `check-workflows.py` | 4 workflows, 0 failures |
| `npm run build --prefix site` | 19 pages |
| `git diff --check` | clean |

No test fixture, build output or generated artefact is tracked.

### Is the remediation complete?

**Yes for everything the repository could decide.** Every P0 and P1 finding is
resolved, the reader-facing prose inventory is empty and gated, and the two
findings that looked like defects were disproved rather than quietly closed.

**No for six decisions and one host session.** Those are listed above, each with
the conflict written so it can be answered without reading this file. They were
not closed by choosing an answer, because choosing would have meant deciding
architecture, security policy or product scope on the audit's behalf.
