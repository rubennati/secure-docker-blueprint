# v1.0.0 readiness audit

Audit of 2026-09-19 against `dev` at `f9b47fd`. The filesystem and the checkers
are the evidence; every README count, roadmap entry and status claim was compared
with them. Each finding carries its resolution, and the sections below are
rewritten as findings close so this file never describes a fixed problem as a
current one.

## A. Executive state

Secure Docker Blueprint is a catalogue of hardened Compose stacks for
independently useful self-hosted software, plus two reusable deployment patterns
for software built in this repository. Since v0.9.0 (2026-09-17) the Priority 1
capability work has landed on `dev` — twenty-one stacks and both patterns — and
nothing of it is released or verified on a host.

The mechanical contract holds: every structural, baseline, status, link, prose and
workflow check passes on `dev`, both rulesets require all ten CI jobs with
up-to-date branches and no bypass, and no work is stranded on another branch.

What stands between the project and v1.0.0 is not structure. Two things are
confirmed blockers and cannot be closed by editing: **verification** (70 of 84
stacks are `scaffolded`) and **Trivy blocking nothing**. On the operator site,
discovery is incomplete — 36 of the 84 stacks have a dedicated page, and the
rest are reachable only as rows of the licence table ([D](#d-website-parity)) —
which PR 2 addresses; and whether the public pages may keep carrying personal
data is a pending decision (D3) with a possible v1.0 impact. See
[G](#g-remaining-v10-blockers).

## B. Canonical inventory

Derived from the filesystem and `scripts/ci/check-coverage.py`, not from any
README.

| Root | Directories | Stacks | Notes |
|---|---|---|---|
| `core/` | 19 | 19 | 18 with Compose; `host-watchdog` is host-installed |
| `apps/` | 47 | 46 | `_reference` is the structure template, not a stack |
| `business/` | 10 | 10 | |
| `monitoring/` | 7 | 7 | `beszel-agent` is the agent of `beszel` |
| `backup/` | 2 | 2 | `borgmatic` is host-installed; `urbackup` has Compose |
| **Lifecycle-tracked total** | | **84** | 82 with a production Compose file, 2 host-installed |
| `development/` | 2 | 0 | `static-site`, `web-api` — patterns, checked like a stack, never deployed as one |

- **Services:** 166 across the 82 production Compose files. Every one states
  `memory`, `pids_limit` and `memswap_limit`; 163 carry `no-new-privileges` (three
  documented exceptions: Nextcloud `app` and `cron`, JumpServer); 69 drop all
  capabilities, 44 have a read-only root filesystem, 9 set `user:`.
- **Helpers belonging to another stack:** `monitoring/beszel-agent`,
  `core/portainer-agent`, `core/hawser` (agent of `core/dockhand`).
- **Local test stack** (`docker-compose.local.yml`): 74 of 84.
- **Lifecycle state:** 1 `ops-proven` (`backup/borgmatic`), 13 `baseline-aligned`,
  70 `scaffolded`. 26 carry the pre-v0.5.1 `Last checked` stamp, 27 have no
  verification date at all, 17 are pin-drifted. 80 of 84 READMEs have no restore
  section (the model is [`docs/standards/restore.md`](standards/restore.md)).
- **Licence classes:** 70 OSI, 8 mixed, 5 source-available, 1 proprietary; 32 EU,
  41 non-EU, 11 with no single jurisdiction.

### Domains for discovery

Derived from what ships, independent of the directory a stack sits in. Proposed as the
catalogue's grouping (PR 2); CI will fail when a stack has no domain.

Infrastructure · Identity, access and secrets · Security operations · AI and local
AI · Documents and e-signature · Files, wiki and collaboration · Photos ·
Dashboards · Publishing, forms and scheduling · Automation and data · Developer
tools · Business operations · Monitoring · Backup.

## C. Findings

Classes: **V1 BLOCKER** (confirmed against current evidence and the product
promise) · **FIX BEFORE V1** (objective, closable by editing) · **DECISION
REQUIRED** (with its possible v1.0 impact stated) · **CLEANUP** · **POST-V1 / ON
HOLD**. A requirement inherited from the old roadmap is a blocker only where the
current product model still justifies it.

Status is the state after the PR named.

### Git

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| G1 | Local `dev` was 5 commits behind `origin/dev` | `974b7bc` vs `f9b47fd` | CLEANUP | Resolved — fast-forwarded |
| G2 | Five remote branches and eight local branches carry no work `dev` lacks (verified: 0 commits ahead of `origin/dev`); a worktree `sdb-ai` sits on a merged branch | `git rev-list --count origin/dev..<branch>` | CLEANUP | Open — deleted only after the audit and fix sequence is complete and all work is confirmed in `dev`; not part of any PR |
| G3 | Local `docs` branch is 11 commits ahead of nothing on the remote | not on `origin` | — | Left alone; it is the private drafts branch |
| G4 | `origin/main` is 33 commits behind `dev` | `d3d25c1` | — | Intended — the unreleased Priority 1 work |

### Repository truth

| ID | Finding | Evidence | Impact | Class | Status |
|---|---|---|---|---|---|
| R1 | ROADMAP contradicted the rulesets and the product model: it named three required checks as not required; kept a "pick one, deprioritise the rest" section; listed v0.9.0 as current work; carried a 70-line design record and a licence policy that duplicated `provenance.md` | old `ROADMAP.md` vs `gh api …/rulesets` | Reader plans against facts that are false | FIX BEFORE V1 | Resolved — PR 1 |
| R2 | `.ai/state.md` named `v0.8.3` as latest tag and Priority 1 batches 4–6 as not started | `git tag`, merged PRs #106–#114 | Session context misleads | FIX BEFORE V1 | Resolved — PR 1 |
| R3 | `docs/security-verification.md` counted 145 services, 143 exceptions-free, 32 `cap_drop`; reality 166, 163, 69. It also called `no-resources` a warning; it fails CI | `check-structure.py` | A security claim with wrong numbers | FIX BEFORE V1 | Resolved — PR 1 |
| R4 | `docs/sovereignty/provenance.md` described 62 stacks and three source-available licences; the generated data has 84 and five | `sovereignty.json` | Licence caveats for Hemmelig and Orion Belt missing | FIX BEFORE V1 | Resolved — PR 1 |
| R5 | Root README said capabilities are "checked on every pull request"; no checker inspects `cap_drop`. **A documentation defect only, not a missing invariant:** `compose-structure.md` and `security-baseline.md` make `cap_drop`, `read_only` and `user:` conditional ("where the image supports it", "where possible"); only `no-new-privileges` is mandatory. A universal checker would fail on legitimate exceptions or need an exception record per service | standards vs `scripts/ci` | Claim broader than enforcement | FIX BEFORE V1 | Resolved — PR 1 (claim corrected; no checker added) |
| R6 | `apps/README.md` omitted `docling-serve`; used "pick one" wording | grep | Stack not discoverable from its category | CLEANUP | Resolved — PR 1 |
| R7 | `CHANGELOG.md` `[Unreleased]` named none of the 21 stacks or 2 patterns | grep | Release history incomplete | CLEANUP | Resolved — PR 1 |
| R8 | LIFECYCLE showed ShellHub's Valkey tag as its pin; `UPSTREAM.md` of IT-Tools, Monica and Easy!Appointments named a version other than the pinned one | `.env.example` vs `UPSTREAM.md` | Generated status column wrong | FIX BEFORE V1 | Resolved — PR 1 (checker fixed, regression test added) |
| R9 | `docs/status-model-proposal.md` — decided and applied, referenced nowhere | `git grep` | Second, stale statement of the status model | CLEANUP | Resolved — PR 1 (removed) |
| R10 | `.ai/domains/architecture.md` said AI & Local AI has no stack | file | Stale session context | CLEANUP | Resolved — PR 1 |
| R11 | `renovate.json` is committed, the Renovate app is not installed, no pin carries a `# renovate:` marker, and `docs/renovate-proposal.md` describes it as pending | 30 Dependabot PRs, 0 Renovate | Dormant configuration and a proposal nobody has closed | DECISION REQUIRED | Open |
| R12 | Three stacks have `COMPOSE_PROJECT_NAME` differing from the directory (`lycheeorg`, `monicahq`, `paperless-ngx`) | `check-structure.py` `identity-source` | Renaming either side breaks existing deployments' volume and network names | DECISION REQUIRED | Open |
| R13 | `docs/host-session-*.md`, `docs/site-review-2026-08-03.md` and four files under `docs/audits/` are dated working records | file headers | Accumulated history in `docs/` | CLEANUP | Open — kept as evidence; a decision on archiving is not needed for v1.0 |
| R14 | `check_env()` reads only `.env.example`, so image tags in the other 81 committed `*.env*.example` files are never checked — 80 `.env.local.example` plus `core/orion-belt/.env.agent.example`. Measured: **0 would violate the tag rule today**, so this is coverage that is absent rather than a defect being hidden. The same measurement surfaced a separate question — 42 local pins lag their production pin (e.g. `apps/homepage` prod `v2.3.0` / local `v1.13.2`) | `git ls-files`, `BAD_TAG` applied to each | A checker claiming tag coverage it does not have | CLEANUP | Open — generalisation shown, not adopted; the 42-pin drift is a separate decision |

### Stacks

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| S1 | 70 of 84 stacks are `scaffolded`; 26 legacy stamps, 27 undated, 17 pin-drifted; none states why it stays there. The promise is that a fork deploys without the author's mental model, and a state resting on no evidence breaks it | `LIFECYCLE.md` | **V1 BLOCKER** — confirmed | Open — needs host sessions; D1 decides how a reason is recorded, not whether one is needed |
| S2 | 80 of 84 READMEs have no restore section; `docs/standards/restore.md` carries the model | generated Restore column | DECISION REQUIRED | Open — D2 |
| S3 | `cap_drop`, `read_only` and non-root `user` are conditional controls, applied to 69, 44 and 9 of 166 services and not CI-enforced. A later option, not a gap: a non-failing coverage report or per-service exception records | `security-verification.md` §4–5 | POST-V1 / ON HOLD | Open |
| S4 | ShellHub pins a release candidate | `core/shellhub/UPSTREAM.md` | CLEANUP — documented limitation, revisit at the first stable tag | Open |
| S5 | Structure checks otherwise clean: no `:latest`, no plaintext secrets, no datastore on `proxy-public`, 13 published-port services all by design, 7 socket mounts all documented exceptions | `check-structure.py`, `check-baseline.py` | — | No finding |

### Operator site

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| W1 | 48 of 84 stacks have no dedicated page, among them all seven monitoring stacks, both backup stacks and every Priority 1 stack; 33 of them appear only as a row in the licence table | [D](#d-website-parity) | FIX BEFORE V1 | Resolved — catalogue and corrected text |
| W2 | Applications index says "around sixty stacks" and points to GitHub for the rest | `applications/index.md` | FIX BEFORE V1 | Resolved — catalogue and corrected text |
| W3 | `llms.txt` states no local single-machine path is documented; the Infrastructure page documents it | `pages/llms.txt.ts`, `infrastructure/index.md` | FIX BEFORE V1 | Resolved — catalogue and corrected text |
| W4 | Navigation mirrors the directories (Infrastructure = `core/`, Applications = `apps/`); no route by problem | `astro.config.mjs` | FIX BEFORE V1 | Resolved — Catalogue section |
| W5 | Parity between repository and site is a manual list and fell 48 stacks behind | W1 | FIX BEFORE V1 | Resolved — generated catalogue, checked in CI |
| W6 | The old gate demanded a choosing page for every capability with more than one option. That does not follow from the current model — overlap is allowed and nothing is ranked — and a page per capability invites a winner. The model needs complete discovery (W1) and, where alternatives differ in a way the catalogue cannot show, a short comparison. One choosing page exists (`applications/choosing`) | site tree | Superseded by W1 plus proportionate comparison; not a blocker | Open — PR 2 gives every domain a role column; further comparison is editorial |
| W7 | Legal notice, privacy statement, domain and `security.txt` carry personal data in a public, forkable repository. Possible v1.0 impact: v1.0 asserts a forkable template and a fork inherits the imprint; whether that blocks depends on D3 | design in `.ai/decisions.md` | DECISION REQUIRED | Open — D3 |
| W8 | The catalogue states a licence and an origin, which is not enough to choose software. Four facts are collapsed or absent: the **licence**, the **use rights** it grants, the **edition** a security-relevant feature sits in, and the **commercial model**. So the site cannot answer whether OIDC, audit logs or HA are paywalled, or whether deploying a stack into a customer's infrastructure is permitted — separate questions with separate answers, and decision support the catalogue implies it gives | `sovereignty.json` carries `license`, `license_class`, `origin` and nothing else; `catalogue.json` carries neither | PRE-V1 CANDIDATE | Open — scope in [Licensing, use rights, editions](#licensing-use-rights-editions-and-feature-gates); belongs with the site information-architecture work, not before it |

### CI and automation

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| C1 | Trivy image scan runs `--exit-code 0` on every severity, so the security baseline has no gate on known-vulnerable images | `trivy.yml` | **V1 BLOCKER** — confirmed | Open — approach decided in `.ai/decisions.md` (image findings as facts); the first scan data is the input |
| C2 | Nothing compared the site with the repository | W5 | FIX BEFORE V1 | Resolved — `site-catalogue.py --check` in the `Status model` job |
| C3 | The site workflow triggers only on `site/**`, so a repository change cannot break the site build unseen | `site.yml` | CLEANUP | Resolved — parity runs in main CI |
| C4 | Trivy image scanning runs on pull requests to `main` and weekly, not on pull requests to `dev` | `trivy.yml` | — | By design, stated in its header |
| C5 | Workflows: 33 action references pinned, all with `permissions:`; ten required jobs match the ruleset names exactly | `check-workflows.py`, `gh api` | — | No finding |

## D. Website parity

Counted on the production build of `dev`, over the 84 lifecycle-tracked stacks:

| Measure | Definition | Stacks |
|---|---|---|
| Dedicated page | a page named for the stack — 7 infrastructure and 29 application guides | 36 |
| Named in prose | its directory name occurs in a rendered page other than the licence table | 51 |
| Row in the licence table only | listed with licence and origin, no description, no link | 33 |
| Linked to the repository | a link to `github.com/…/<category>/<stack>` from any page | 39 |
| Searchable by name | its directory name occurs in the search index; the licence table is not indexed | 54 |
| Completely absent | none of the above | 0 |

Every stack is at least named in the licence table, which is why none is
absent; that table is a sovereignty view, not a way to find or understand a
product, so it does not count towards discovery.

**Canonical parity definition for PR 2:** a stack is represented when the
generated catalogue carries an entry for it — name, domain, one-line role,
description, upstream link, pinned version, lifecycle state and a link to its
repository directory — and that entry is in the search index. A dedicated page
is not required. `site-catalogue.py --check` fails when a lifecycle-tracked
stack lacks an entry, when an entry has no stack, or when the generated data is
stale.

Stacks with no dedicated page (48): `core/` hawser, host-watchdog, infisical,
jumpserver, orion-belt, portainer, portainer-agent, shellhub, step-ca, teleport,
warpgate, zot; `apps/` collabora, dependency-track, dfir-iris, docling-serve,
euro-office, greenmail, hemmelig, librephotos, lycheeorg, monicahq, ollama,
opencanary, photoview, privatebin, qdrant, threat-dragon, unifi, velociraptor,
vllm, whoami, windmill, yopass; `business/` dolibarr, kimai, matomo, opensign,
zammad; `monitoring/` all seven; `backup/` borgmatic, urbackup.

Site pages with no matching stack: none. Stale claims for PR 2: the "around
sixty stacks" sentence on the applications page and the `llms.txt` note that no
local path is documented. LibreChat is not in the repository and so is not
listed.

## Licensing, use rights, editions and feature gates

Scope for W8. The 89 stacks are not researched or filled here.

**Four layers, kept apart.** Collapsing them is the current defect.

1. **Licence** — what governs the software: MIT, Apache-2.0, GPL, AGPL, BSL, Elastic,
   Sustainable Use, proprietary, or open-core mixtures. Already recorded.
2. **Use rights** — never one "commercial use" field. Per right, from the upstream
   terms and not from marketing copy: personal self-hosting · internal organisational
   use · installing it into a customer's own infrastructure · operating it as a managed
   service for a customer · offering it as SaaS · resale or white-label · modification ·
   redistribution · source-availability obligations for modifications. Values:
   `allowed` · `restricted` · `requires commercial terms` · `unclear from published
   terms` · `not applicable`.
3. **Edition** — not the licence. Open-source software may still reserve features for a
   paid edition. Record only what upstream actually gates, and only where it is
   security- or operations-relevant: native OIDC · SAML · LDAP/AD · SCIM ·
   edition-dependent MFA · RBAC and granular permissions · audit logs · enterprise
   policy controls · HA, clustering or multi-node. A feature is not "Enterprise"
   because the name sounds like it. **Native application SSO and putting Authentik
   forward-auth in front of an application are different capabilities** and must not be
   recorded as one.
4. **Commercial model** — durable fields rather than volatile prices: `free
   self-hosted` · `paid add-on` · `per-user subscription` · `paid self-hosted edition` ·
   `commercial licence` · `quote only` · `no paid edition`, each with the official
   licensing or pricing link. A price that ever reaches the site data carries currency,
   billing unit, billing period, date checked and source — an undated price is not a
   repository fact.

**Source of truth.** Evaluate extending the per-stack `UPSTREAM.md` first, with
`sovereignty-report.py` / `sovereignty.json` and `site-catalogue.py` generating the
views, before considering any new file. One canonical per-stack owner, generated
secondary views — no second hand-kept table.

**On the site.** Each product exposes the four facts compactly, plus the official
links. One reusable page explains the concepts — MIT, GPL, AGPL, source-available,
open-core — so no product page repeats them, and states plainly that *licence is not
edition is not pricing*, and why **installing software for a customer** and
**running it as a hosted service for them** can have different licence consequences.
Factual decision support, not legal advice.

No ratings, no traffic lights, no recommended winner. The operator decides.

## E. Roadmap reconciliation

| Item | Verdict | Reason |
|---|---|---|
| v0.9.0 direction paragraph | Move | Shipped; the tag and CHANGELOG own it |
| v0.10.0 measured limits | Keep, shortened; **D4** | Still needs host measurements; whether it remains a release is a decision |
| v1.0 repository list — clean install per app | Keep | Still the largest open item (S1) |
| — no `scaffolded` without a reason | Keep | Same |
| — no `__REPLACE_ME__` in a verified file | Remove | Enforced by the sentinel job and the baseline-aligned criteria |
| — CI baseline complete | Update | Only the Trivy gap remains; the three "not required" checks are required |
| — secrets generation / rotation standard | Remove | Shipped in v0.9.0 (`docs/standards/secrets.md`) |
| — licence review | Remove | Satisfied: all 84 carry `License` and `Origin` (CI-checked) and every non-OSI stack's restriction is named in its field; the policy moved to `provenance.md` |
| — status freshness system | Remove | Shipped and CI-enforced |
| — status model end to end | Remove | Shipped and CI-enforced |
| v1.0 site list | Keep, two changed | "Choosing page per multi-option capability" is replaced by complete discovery of every stack by name and domain, checked against the repository, plus comparison where alternatives need it; "every claim agrees" stays |
| Continuous — app testing | Keep, lists shortened | Pin/major detail is generated in `LIFECYCLE.md` |
| Continuous — Cal.diY hardening | Keep | Own track |
| Continuous — operator site | Keep | |
| Personal data on the public site | Keep as summary, move design | Design record to `.ai/decisions.md`; impact on v1.0 pending D3 |
| Choice-matrix categories | Remove | Contradicts the catalogue model; overlap is allowed, nothing is deprioritised |
| Category planned lists | Keep as pointers | Category READMEs own them |
| Project-management evaluation | Move | Post-v1 / on hold |
| Suricata, Coraza | Move | Post-v1 / on hold |
| Licence policy | Move | Duplicated `provenance.md`; now lives there |
| Configuration tiering, evaluation criteria, deploy script, runtimes, MCP | Keep, condensed | Concepts without timeline |
| Out of scope | Keep | All still valid; acme-certs, OCRmyPDF, orchestration, SIEM |
| Priority 2 (LiteLLM, Open WebUI, agentgateway, Dify, Langfuse) | Add | On hold, previously only in `.ai/state.md` |

## F. Implementation plan

| PR | Scope | Status |
|---|---|---|
| 1 | Repository truth — this report, ROADMAP, state, counts, provenance, CHANGELOG, lifecycle pin fix, `UPSTREAM` drift | Prepared |
| 2 | Operator site — generated catalogue for all 84 stacks by name and domain, sidebar, stale-claim fixes, `site-catalogue.py --check` in CI | Done |
| 3 | Reconciliation — re-run inventory and comparisons, mark findings resolved | Not started |

## G. Remaining v1.0 blockers

**Confirmed V1 blockers** — cannot be closed by editing:

1. **S1 — verification depth.** Host sessions, per stack, until each is verified
   once or carries a stated reason it is not.
2. **C1 — Trivy blocking.** Assess the existing CRITICAL findings once, then set
   `exit-code: 1` for them.

**Decision required, possible v1.0 impact:** W7 / D3 — personal data on the
public site. If the site is part of the v1.0 promise of a forkable template,
D3 must be decided and implemented first.

**Fix before v1.0, objective:** W1 — every stack discoverable on the site
(closed by the catalogue). Comparison text beyond the catalogue's role column is editorial and not
a blocker.

**Post-v1.0 / on hold:** S3 coverage reporting; Priority 2 applications.

## Decisions required

| ID | Question | Recommendation |
|---|---|---|
| D1 | Is "every stack verified or carrying a reason" the v1.0 gate for all 84, or for a defined subset? | Keep the gate; make the reason mandatory and short, per stack, in `UPSTREAM.md`, so a `scaffolded` stack at v1.0 is a stated fact rather than an omission |
| D2 | Must each stack README link the restore standard, or is the standard plus the Backup section enough? | Link it — one line per README, mechanical |
| D3 | Adopt the encrypted-personal-data design for the site, and does an unresolved D3 block v1.0? | Adopt it; if it is not implemented, v1.0 should say so rather than ship a template that publishes its author's imprint |
| D4 | Does v0.10.0 remain a release, or does measurement become continuous, applied when a stack is verified? | Continuous — the measurement needs the same host session as S1 |
| D5 | Install Renovate or delete `renovate.json` and its proposal? | Delete — Dependabot already covers Actions and npm, and no pin carries a marker |
| D6 | Resolve the three project-name mismatches by editing `.env.example` or the directory? | Neither before v1.0 — a rename breaks live deployments; record it as an exception |
