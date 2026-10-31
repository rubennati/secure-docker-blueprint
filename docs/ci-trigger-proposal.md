# Proposal — when a check runs, and why

**Status: a decision document, not a configuration.** Nothing here changes a
workflow. The workflows run as [`standards/ci.md`](standards/ci.md) and
[`security-verification.md`](security-verification.md) describe them; the
open draft pull request #302, which adds triggers to `trivy.yml`, stays a
draft until the decisions below are taken, and is then reworked or closed.
The decisions go into [`../.ai/decisions.md`](../.ai/decisions.md) first; a
workflow changes only after that.

Written on 2026-10-31, after a day that ran the image scan eight times —
roughly four and a half hours of scanning for one tree — because the
question "where does the expensive check belong?" had never been written
down for this repository, only answered for the ten fast jobs.

## What this repository runs today

Six workflows. Durations are the last six completed runs of each, read from
the Actions API on 2026-10-31.

| Workflow | Fires on | Takes | Decides a merge? |
|---|---|---|---|
| `ci.yml` — ten checkers | pull request to `dev` or `main`; push to `main`; by hand | about a minute | yes: all ten required on both branches |
| `trivy.yml` — IaC scan and image CVE scan | pull request to `main`; push to `main`; Monday 04:00 UTC; by hand | 23 to 39 minutes, 200 images pulled | yes on `main`: both jobs required; no on `dev` |
| `codeql.yml` | pull request and push, `dev` and `main`; Monday 05:00 UTC | about a minute | no: reporting only, by decision |
| `scorecard.yml` | push to `main`; Monday 05:30 UTC; branch-protection change | seconds | no |
| `site.yml` — build and publish the operator site | pull request and push to `main`, only when `site/` changed | about a minute | build yes; publish is CD, `main` only |
| `cloudflare-ips.yml` | pull request touching the range file; Monday 06:17 UTC; by hand | seconds | yes, when it runs |

Both rulesets require a pull request, the ten jobs, and an up-to-date branch;
neither has a bypass actor. The up-to-date rule means that when several pull
requests are open, each merge re-runs the others' checks. For the ten
one-minute jobs that is the price of testing the integration that lands; for
a 35-minute scan it would be the same price times thirty-five.

## What GitHub decides, and what the maintainer decides

GitHub fixes three things. A `schedule` fires on the default branch only, from
the workflow file on that branch. A `pull_request` run checks a merge
preview, not the commit that later lands. Minutes on a public repository are
not billed. Everything else — which events, which branches, what is required,
what runs twice — is this repository's choice, and the unbilled minutes are
why most public projects run far more than they need: nothing pushes back.

The choices this repository has already made, and keeps: transparency (the
badges, the Security tab, published scan results, the baseline in the tree),
required checks on both branches, no bypass, no post-merge run on `dev`
because the pull-request run already tested what lands. The choice it has
not written down is the one this document is for: where an expensive check
belongs.

## Four classes of check

Every check answers one question, and the answer changes for one reason. The
reason says when the check has to run, and when running it again adds
nothing.

1. **Deterministic checks of the tree.** Same input, same answer, in
   seconds: structure, compose validation, security baseline, links, prose,
   status model, the secret scan of the new commits. They decide a merge, so
   they run on every pull request, and on nothing else — a schedule would
   re-answer a question nothing has changed. This is `ci.yml`, and it is
   already built on this rule.

2. **Checks whose answer changes with time.** The image CVE scan, CodeQL,
   Scorecard: a tree that passed yesterday can fail today because a CVE was
   published, a query pack updated, a criterion moved. These belong on a
   schedule, on every branch the maintainer reads a verdict for, and
   otherwise nowhere — a commit rarely changes their answer, the calendar
   does. Today the image scan has a schedule for `main` only. `dev` carries
   pins ahead of `main` for weeks during the upstream programme, and no
   schedule looks at them.

3. **Expensive checks that decide a merge.** The image scan as a required
   check on the pull request to `main`: no pin reaches the published branch
   with a CRITICAL finding the baseline does not record. The relevance step
   of 2026-10-23 keeps it to pull requests that can change the scan. The
   same scan on a pull request to `dev` decides nothing, because the `dev`
   ruleset does not require it; it would only cost. That is what #302 adds,
   and what this document advises against.

4. **Checks on demand.** `workflow_dispatch`, on any branch, when someone
   needs the answer now: a batch of pin moves measured on its own branch
   before it merges, the whole-history secret scan before a tag, a re-run
   after a registry quota reset. Runs 173 and 182 of 2026-10-31 were this
   class. It costs one run per real question and needs no trigger.

| Check | Class | Runs today | Fits the class? |
|---|---|---|---|
| ten `ci.yml` jobs | 1 | every pull request | yes |
| IaC scan (`trivy config`) | 1, seconds | with the image scan | yes, as a companion; it uploads SARIF for `main` |
| image CVE scan | 2, 3, 4 | pull request to `main`, push to `main`, Monday `main`, by hand | class 2 is missing `dev`; the push run on `main` exists for the badge |
| CodeQL | 2 | every pull request and push, plus Monday | runs more than its class needs; cheap, so tolerated |
| Scorecard | 2 | push to `main`, Monday | yes |
| site build | 1 | when `site/` changed | yes |
| site publish | CD | push to `main` | yes |
| Cloudflare ranges | 2 | Monday, and when the file changes | yes |

## The costs, measured on one day

The image scan pulls about 200 images from Docker Hub, ghcr.io, quay.io and
others, anonymously. Docker Hub meters anonymous pulls per address and
refused the two Langfuse images on two of the day's runs and n8n on another;
public ECR refused Teleport on three. Each full run is 23 to 39 minutes of a
runner and roughly 200 image pulls. On 2026-10-31 the scan ran eight times:
a re-run of the stale weekly run, two runs by hand, two on the pull request
to `main` (the second after the baseline changed), two pushes to `main`, one
on the draft #302. Six of the eight answered a real question; the two
`main` pushes repeated the pull-request result on a tree that had just
passed, and only the badge gained from them.

Two more costs are not minutes. A red check that nobody reads teaches people
to ignore red; the stale weekly run was red for three weeks before anyone
looked. And every anonymous pull against a registry quota that a maintainer
does not control is a run that can fail for reasons outside the tree.

## Options

Each option is scored on the four dimensions the maintainer named: security
(does a finding reach the published branch unseen?), risk (what breaks or
misleads?), sustainability (runs per week, pulls per week), transparency
(what can an outsider verify?).

**A. #302 as drafted** — pull request to `dev` (relevance-gated) and Thursday
on `dev`, on top of today. Security: highest, every batch measured at once.
Risk: a non-required red on `dev` that people learn to ignore. Sustainability:
one full run per pin-moving pull request into `dev` — during the programme,
one per batch, plus the Thursday run. Transparency: unchanged.

**B. Monday `main`, Thursday `dev`, pull request to `main`, nothing on pull
requests to `dev`.** Security: a new CVE meets `dev`'s pins within seven
days; no pin reaches `main` unscanned. Risk: a batch is measured up to a
week after it merged, and the baseline record comes as its own pull request.
`dev` is not deployed from, so the week is accepted. Sustainability: one run
per week more than today. Transparency: the Thursday run's summary is
public like every run.

**C. B plus the scan by hand on a batch's branch before it merges.** Same as
B, with the measurement moved to where the batch is prepared: whoever moves
pins starts the scan on the branch, reads the gate, records the baseline on
the same branch, and the pull request into `dev` arrives measured. Costs one
run per batch, started by a person who wants the answer, not by an event.
This is what the programme's rule 2 should say.

**D. Scan "every hour if the branch moved".** No native trigger; it needs a
schedule that stores the last scanned commit and exits when nothing changed.
State to maintain, for an answer the Thursday run gives a few days later.
Not recommended.

**E. Drop the push run on `main`.** The push run repeats the pull-request
scan on a tree that just passed; its one product is the badge showing a run
of the tree that landed rather than the weekly run of the tree before it.
If the badge may show the weekly run, this run goes. If the badge is a
promise about the tree that landed, it stays. A transparency decision, not a
security one.

**Recommendation: C, and E decided explicitly.** Measured on the day above,
C would have run the scan three times instead of eight.

## Beyond the triggers

The day's trouble was not the trigger. The weekly run on `main` was red for
three weeks because `main` did not move and nobody was charged with reading
it; the Dependabot alerts were open for a month for the same reason. A
trigger is a sensor; what was missing is who reads it. Three things belong
to that, each its own decision:

- **Who reads a red scheduled run, and by when.** A duty with a name and a
  deadline — "the maintainer, within the week" is enough — recorded where the
  weekly run is described.
- **Following upstream releases.** The programme in
  [`audits/upstream-version-inventory-2026-10-31.md`](audits/upstream-version-inventory-2026-10-31.md)
  moves pins by hand in batches; [`renovate-proposal.md`](renovate-proposal.md)
  has waited since July for the one action that makes detection automatic.
  Both are the same decision seen twice.
- **A state for a stack that must not move.** The status model has
  `scaffolded`, `verified`, `baseline-aligned`, `ops-proven`. It has no
  state for "upstream has a known problem; hold this pin and say so" — the
  Dify plugin daemon and SeaSearch holds of batch 2 live in `UPSTREAM.md`
  prose because there is nowhere else. [`standards/status-model.md`](standards/status-model.md)
  is where such a state would be defined.

## Open decisions

1. **Which option — A, B, C or something else?** Recommendation: C.
2. **Keep the push run on `main` (E)?** Recommendation: keep it only if the
   badge is meant as a statement about the tree that landed; otherwise drop
   it and let the weekly run carry the badge.
3. **Make the two scan jobs required on `dev`?** Recommendation: no. A
   required 35-minute check on the integration branch, with the up-to-date
   rule, is the cost this document exists to avoid; `main` keeps the gate.
4. **CodeQL on every push to `dev` and `main`, or on pull requests and the
   schedule only?** Cheap today, so no urgency; but it is class 2 running as
   class 1. Recommendation: pull requests and the schedule, when the
   workflow is next touched.
5. **The Thursday run and the IaC scan.** A `dev` run uploads no SARIF — the
   upload would attach `dev`'s findings to `main`'s commit — so the IaC job
   skips that day. Recommendation: accept; the pull request into `dev`
   covers `dev`'s IaC through `check-baseline.py`, and the SARIF is a `main`
   record.
6. **The three process decisions above** — the reader of red, the Renovate
   activation, the hold state. Each is a register entry of its own.

## Sequencing

1. The maintainer answers 1 to 5; the answers go into
   [`../.ai/decisions.md`](../.ai/decisions.md) as one entry with these
   dimensions stated.
2. [`standards/ci.md`](standards/ci.md) gains the four classes as the rule
   that assigns a check to a trigger — today it states the rule for class 1
   only — and [`security-verification.md`](security-verification.md) names
   the triggers the decision leaves.
3. `trivy.yml` changes once, to what was decided; #302 is reworked to that
   or closed. The programme's rule 2 names the trigger the decision chose.
4. The process decisions (6) follow at their own pace; none of them blocks
   the first three.

## Validation evidence

- Triggers: read from the six workflow files on `dev` at 8d71f3a.
- Durations: the last six completed runs per workflow from the Actions API
  on 2026-10-31 — `ci.yml` about a minute, `trivy.yml` 23 to 39 minutes,
  the others under a minute.
- The eight scans of 2026-10-31: runs 163 (re-run), 173, 177, 178, 179,
  181, 182 and the run on the draft #302, from the same API.
- Registry refusals: the gate summaries of runs 163, 173, 177 and 182
  (n8n once, Langfuse twice, Teleport three times, MinIO always).
- The three-week red: runs 150, 154 and 163, all on the tree of 2026-10-04.
