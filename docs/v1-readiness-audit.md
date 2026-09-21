# Stabilization audit

State of `dev` at `24dd7a2`, 2026-09-20. The filesystem and the checkers are the
evidence; every count, roadmap entry and status claim here was compared with them.

This file is the findings register for the stabilization programme. A finding
carries its resolution and the pull request that closed it, and the descriptive
sections are rewritten as findings close, so nothing here describes a fixed
problem as a current one. A resolved finding keeps the figures it was found with —
those are the record of what was wrong. Open findings carry current figures.

Actionable work lives in GitHub Issues, strategy in `ROADMAP.md`, present state in
`.ai/state.md`. This file holds what none of those owns: the evidence behind a
finding and why it is still open.

## A. Executive state

Secure Docker Blueprint is a catalogue of hardened Compose stacks for
independently useful self-hosted software, plus two reusable deployment patterns
for software built in this repository. Since v0.9.0 (2026-09-17) the Priority 1
capability work has landed on `dev` — twenty-one stacks and both patterns — and
nothing of it is released or verified on a host.

The mechanical contract holds: every structural, baseline, status, link, prose and
workflow check passes on `dev`, both rulesets require all ten CI jobs with
up-to-date branches and no bypass, and no work is stranded on another branch.

Three pull requests closed the mechanical half of it. **#124** made opt-in compose
overlays deployment variants that are merge-validated rather than files nothing
looked at. **#125** gave GitHub Issues ownership of the work they describe and
separated the deployable scope from the wider checker scope. **#126** made the
local evaluation path discoverable on all 79 stacks that have one and corrected
the site's prerequisite semantics.

What remains is not structural. **Verification is the largest item**: 75 of 89
stacks are `scaffolded`, and a state resting on no evidence needs a host, not an
edit. **Trivy still blocks nothing.** Everything else open is either a decision
only the maintainer can take or work deliberately deferred — see
[G](#g-remaining-work).

## B. Canonical inventory

Derived from the filesystem and `scripts/ci/check-coverage.py`, not from any
README.

| Root | Directories | Stacks | Notes |
|---|---|---|---|
| `core/` | 19 | 19 | 18 with Compose; `host-watchdog` is host-installed |
| `apps/` | 51 | 50 | `_reference` is the structure template, not a stack |
| `business/` | 10 | 10 | |
| `monitoring/` | 8 | 8 | `beszel-agent` is the agent of `beszel` |
| `backup/` | 2 | 2 | `borgmatic` is host-installed; `urbackup` has Compose |
| **Lifecycle-tracked total** | | **89** | 87 with a production Compose file, 2 host-installed |
| `development/` | 2 | 0 | `static-site`, `web-api` — patterns, checked like a stack, never deployed as one |

- **Services — two scopes, never mixed (#125).** The deployable stacks and the
  wider set the checkers parse are counted separately: the difference is
  `apps/_reference` and the two `development/` patterns, which are validated and
  never deployed. Both scopes and every per-control figure are generated into
  [`security-coverage.md`](security-coverage.md) — the numbers that used to
  stand here are what R15 removed, so they are not restated.
- **Opt-in overlays:** 6, each merge-validated as its own deployment variant
  through `docker compose config` (#124). Five affect services and get the full
  baseline; one redefines only networks. None is counted as a stack or a service —
  several are alternatives to each other.
- **Helpers belonging to another stack:** `monitoring/beszel-agent`,
  `core/portainer-agent`, `core/hawser` (agent of `core/dockhand`).
- **Local test stack** (`docker-compose.local.yml`): 79 of 89, every published port bound to loopback. All 79 carry a `## Try it locally` section (#126).
- **Lifecycle state:** 1 `ops-proven` (`backup/borgmatic`), 13 `baseline-aligned`,
  75 `scaffolded`. 26 carry the pre-v0.5.1 `Last checked` stamp, 32 have no
  verification date at all, 17 are pin-drifted. 85 of 89 READMEs have no restore
  section (the model is [`docs/standards/restore.md`](standards/restore.md)).
- **Licence classes:** 71 OSI, 32 EU. Generated and CI-checked; the full split is
  in `docs/sovereignty/provenance.md`.
- **Site:** all 89 in the generated catalogue across 14 domains, each searchable by
  product name and linked to its repository directory; 36 additionally have a
  written guide.

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
| G2 | Three local `chore/*` branches remain after their pull requests merged, each with 0 unique commits | `git rev-list --count <branch> --not origin/dev origin/main` | CLEANUP | Resolved — deleted in the closing pass; the local-only `docs` branch (11 unique commits, independent history) is kept |
| G3 | Local `docs` branch is 11 commits ahead of nothing on the remote | not on `origin` | — | Left alone; it is the private drafts branch |
| G4 | `origin/main` is 33 commits behind `dev` | `d3d25c1` | — | Intended — the unreleased Priority 1 work |

### Repository truth

| ID | Finding | Evidence | Impact | Class | Status |
|---|---|---|---|---|---|
| R1 | ROADMAP contradicted the rulesets and the product model: it named three required checks as not required; kept a "pick one, deprioritise the rest" section; listed v0.9.0 as current work; carried a 70-line design record and a licence policy that duplicated `provenance.md` | old `ROADMAP.md` vs `gh api …/rulesets` | Reader plans against facts that are false | FIX BEFORE V1 | Resolved — #115 |
| R2 | `.ai/state.md` named `v0.8.3` as latest tag and Priority 1 batches 4–6 as not started | `git tag`, merged PRs #106–#114 | Session context misleads | FIX BEFORE V1 | Resolved — #115 |
| R3 | `docs/security-verification.md` counted 145 services, 143 exceptions-free, 32 `cap_drop`; reality 166, 163, 69. It also called `no-resources` a warning; it fails CI | `check-structure.py` | A security claim with wrong numbers | FIX BEFORE V1 | Resolved — #115 |
| R4 | `docs/sovereignty/provenance.md` described 62 stacks and three source-available licences; the generated data has 84 and five | `sovereignty.json` | Licence caveats for Hemmelig and Orion Belt missing | FIX BEFORE V1 | Resolved — #115 |
| R5 | Root README said capabilities are "checked on every pull request"; no checker inspects `cap_drop`. **A documentation defect only, not a missing invariant:** `compose-structure.md` and `security-baseline.md` make `cap_drop`, `read_only` and `user:` conditional ("where the image supports it", "where possible"); only `no-new-privileges` is mandatory. A universal checker would fail on legitimate exceptions or need an exception record per service | standards vs `scripts/ci` | Claim broader than enforcement | FIX BEFORE V1 | Resolved — #115 (claim corrected; no checker added) |
| R6 | `apps/README.md` omitted `docling-serve`; used "pick one" wording | grep | Stack not discoverable from its category | CLEANUP | Resolved — #115 |
| R7 | `CHANGELOG.md` `[Unreleased]` named none of the 21 stacks or 2 patterns | grep | Release history incomplete | CLEANUP | Resolved — #115 |
| R8 | LIFECYCLE showed ShellHub's Valkey tag as its pin; `UPSTREAM.md` of IT-Tools, Monica and Easy!Appointments named a version other than the pinned one | `.env.example` vs `UPSTREAM.md` | Generated status column wrong | FIX BEFORE V1 | Resolved — #115 (checker fixed, regression test added) |
| R9 | `docs/status-model-proposal.md` — decided and applied, referenced nowhere | `git grep` | Second, stale statement of the status model | CLEANUP | Resolved — #115 (removed) |
| R10 | `.ai/domains/architecture.md` said AI & Local AI has no stack | file | Stale session context | CLEANUP | Resolved — #115 |
| R11 | `renovate.json` is committed, the Renovate app is not installed, no pin carries a `# renovate:` marker, and `docs/renovate-proposal.md` describes it as pending | 30 Dependabot PRs, 0 Renovate | Dormant configuration and a proposal nobody has closed | DECISION REQUIRED | Open |
| R12 | Three stacks have `COMPOSE_PROJECT_NAME` differing from the directory (`lycheeorg`, `monicahq`, `paperless-ngx`) | `check-structure.py` `identity-source` | Renaming either side breaks existing deployments' volume and network names | DECISION REQUIRED | Open |
| R13 | `docs/host-session-*.md`, `docs/site-review-2026-08-03.md` and four files under `docs/audits/` are dated working records | file headers | Accumulated history in `docs/` | CLEANUP | Open — kept as evidence; a decision on archiving is not needed for v1.0 |
| R14 | `check_env()` read only `.env.example` and matched only `<NAME>_TAG`, so 84 committed `*.env*.example` files and the 12 `<NAME>_IMAGE` pins were never checked. Measured: **0 violated the tag rule**. The same measurement surfaced the separate question of 41 local pins lagging production | `git ls-files`, `BAD_TAG` applied to each | A checker claiming tag coverage it does not have | CLEANUP | **Closed** — the tag rule reads every example file and both pinning styles; `local-pin-drift` now enforces that a local stack pins what production ships, and all 41 pins are synchronised (D7) |
| R15 | The hardening coverage figures in `docs/security-verification.md` were maintained by hand and went stale twice in three days — corrected to 166 services on 2026-09-19, already wrong at 205 on 2026-09-20 because four stacks landed in between. Every one is derivable from the compose files the checkers already parse | the table's own numbers against `check-structure.py --list` | A security document whose numbers are usually wrong | CLEANUP | **Closed** — `scripts/ci/security-coverage.py` counts them from the compose files into [`security-coverage.md`](security-coverage.md), verified in CI. `security-verification.md` keeps the descriptions and links to the figures |

### Stacks

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| S1 | 75 of 89 stacks are `scaffolded`; 26 carry a legacy stamp, 32 have no verification date, 17 are pin-drifted, and none states why it stays there. The promise is that a fork deploys without the author's mental model, and a state resting on no evidence breaks it | `LIFECYCLE.md` | **NEEDS HOST EVIDENCE** — the largest remaining item | Open — D1 decides how a reason is recorded, not whether one is needed |
| S2 | 85 of 89 READMEs have no restore section; `docs/standards/restore.md` carries the model | generated Restore column | DECISION REQUIRED | Open — D2 |
| S3 | `cap_drop`, `read_only` and non-root `user` are conditional controls and not CI-enforced — the current coverage of each is in [`security-coverage.md`](security-coverage.md). A later option, not a gap: per-service exception records. The non-failing coverage report R15 also called for now exists | `security-verification.md` §4–5 | POST-V1 / ON HOLD | Open — narrowed to the exception records |
| S4 | ShellHub pins a release candidate | `core/shellhub/UPSTREAM.md` | CLEANUP — documented limitation, revisit at the first stable tag | Open |
| S5 | Structure checks otherwise clean: no `:latest`, no plaintext secrets, no datastore on `proxy-public`, 13 published-port services all by design, 7 socket mounts all documented exceptions | `check-structure.py`, `check-baseline.py` | — | No finding |

### Operator site

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| W1 | 48 of 84 stacks have no dedicated page, among them all seven monitoring stacks, both backup stacks and every Priority 1 stack; 33 of them appear only as a row in the licence table | [D](#d-website-parity) | FIX BEFORE V1 | Resolved — #119 |
| W2 | Applications index says "around sixty stacks" and points to GitHub for the rest | `applications/index.md` | FIX BEFORE V1 | Resolved — #119 |
| W3 | `llms.txt` states no local single-machine path is documented; the Infrastructure page documents it | `pages/llms.txt.ts`, `infrastructure/index.md` | FIX BEFORE V1 | Resolved — #119 |
| W4 | Navigation mirrors the directories (Infrastructure = `core/`, Applications = `apps/`); no route by problem | `astro.config.mjs` | FIX BEFORE V1 | Resolved — #119 |
| W5 | Parity between repository and site is a manual list and fell 48 stacks behind | W1 | FIX BEFORE V1 | Resolved — #119, `site-catalogue.py --check` in CI |
| W6 | Comparison pages beyond the catalogue's role column | site tree | POST-V1 / ON HOLD | Superseded by W1 — the catalogue gives every domain a role column, and the model neither ranks nor names a winner. Further comparison is editorial, not a defect |
| W7 | Legal notice, privacy statement, domain and `security.txt` carry personal data in a public, forkable repository. Possible v1.0 impact: v1.0 asserts a forkable template and a fork inherits the imprint; whether that blocks depends on D3 | design in `.ai/decisions.md` | DECISION REQUIRED | Open — D3 |
| W8 | The catalogue states a licence and an origin, which is not enough to choose software. Five facts are collapsed or absent: the **licence**, the **use rights** it grants, the **edition** a security-relevant feature sits in, the **commercial model**, and the **operational footprint** a stack brings with it. So the site cannot answer whether OIDC, audit logs or HA are paywalled, whether deploying a stack into a customer's infrastructure is permitted, or whether one of two comparable products is a single container and the other brings a database, a cache and workers — separate questions with separate answers, and decision support the catalogue implies it gives | `sovereignty.json` carries `license`, `license_class`, `origin` and nothing else; `catalogue.json` carries neither | PRE-V1 CANDIDATE | **Partly closed** — layer 5, the operational footprint, is derived from the compose files into `catalogue.json` and shown on the catalogue page; no field to fill and none to keep current. Layers 2–4 have a schema and a checker — `Use restrictions`, `Edition gating` and `Commercial model` in `UPSTREAM.md`, each rejected without a source and a checked date — and four stacks are filled from upstream's own terms. The rest need the same reading, one stack at a time. Scope in [Catalogue decision facts](#catalogue-decision-facts) |

### CI and automation

| ID | Finding | Evidence | Class | Status |
|---|---|---|---|---|
| C1 | Trivy's image scan runs `--exit-code 0` on every severity, so the security baseline has no gate on known-vulnerable images | `trivy.yml` | **FIX BEFORE V1** — confirmed | Open — needs the one-off CRITICAL assessment; the approach is recorded in `.ai/decisions.md` |
| C2 | Nothing compared the site with the repository | W5 | FIX BEFORE V1 | Resolved — `site-catalogue.py --check` in the `Status model` job |
| C3 | The site workflow triggers only on `site/**`, so a repository change cannot break the site build unseen | `site.yml` | CLEANUP | Resolved — parity runs in main CI |
| C4 | Trivy image scanning runs on pull requests to `main` and weekly, not on pull requests to `dev` | `trivy.yml` | — | By design, stated in its header |
| C5 | Workflows: 33 action references pinned, all with `permissions:`; ten required jobs match the ruleset names exactly | `check-workflows.py`, `gh api` | — | No finding |

## D. Website parity

Resolved. Measured on the production build of `dev` @ `24dd7a2`:

| Measure | Stacks |
|---|---|
| In the generated catalogue, searchable by product name, linked to its repository directory | **89 / 89** |
| Additionally carries a written guide | 36 |
| Site pages with no matching stack | 0 |

**The parity definition CI enforces:** a stack is represented when the generated
catalogue carries an entry for it — name, domain, one-line role, description,
upstream link, pinned version, lifecycle state and a repository link — and that
entry is in the search index. A written guide is not required.
`site-catalogue.py --check` fails when a lifecycle-tracked stack has no entry,
when an entry names no stack, or when `catalogue.json` is stale, so the site
cannot silently fall behind the repository again.

Discovery runs on two axes: by product name through search, and by problem
through the 14 domains, which are independent of the directory a stack sits in.
The sidebar keeps Infrastructure and Applications as a secondary technical view —
those are the existing guides, whose URLs are deliberately stable.

Every page whose stack has a local path leads with `## Try it locally`, and none
states Traefik or a domain as an application prerequisite (#126).

## Catalogue decision facts

Scope for W8 — five factual layers, one model. No stack is researched or filled here.

**Five layers, kept apart.** Collapsing them is the current defect.

**The licence does not decide which stacks need layers 2–4.** A source-available or
mixed licence is the obvious prompt, but an OSI-licensed project can still reserve
OIDC, SAML, audit logs or HA for a paid edition, and can still sell support or a
hosted tier. Scoping the work by `license_class` would miss exactly those
and leave the catalogue implying a completeness it does not have. Which stacks need
maintained facts is its own question, answered per stack.

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

   **Implemented for layers 2 to 4.** The three fields live in `UPSTREAM.md` beside the
   licence, each as `<statement> — <source url> · checked YYYY-MM-DD`, and
   `site-catalogue.py --check` rejects one without provenance or with a commercial model
   outside the vocabulary. No price is recorded: the source link is where an amount is
   read. An absent field means the stack was not researched, never that it has nothing to
   declare — a stack checked and found to gate nothing records `none`. Filled so far: **seventeen of 91**, listed in `.ai/tasks.md`. Unresolved and left
   unrecorded rather than inferred: `apps/hemmelig`, whose README and `LICENSE` file
   disagree, and `apps/collabora`, whose limits no reachable upstream page states.

   The research has corrected the repository as often as it has extended it:
   `apps/nocodb` was recorded as AGPL-3.0 after upstream relicensed to the Sustainable
   Use License, `core/dockhand` told operators internal business use was free where the
   licence requires a Commercial Licence for it, and `core/teleport`'s container images
   have not been Apache-2.0 since version 16. None of the three carried a signal that a
   filter would have caught.

5. **Operational footprint** — how much machinery a stack brings, as facts rather
   than a verdict. Two products solving one problem at very different weights is a
   reason for both to exist here, not a reason to rank them.

   The shape is one line: `2 services · MariaDB · CPU only` beside
   `3 services · PostgreSQL + Redis · CPU only`. That separates
   `apps/easyappointments` from `apps/caldiy` without any editorial judgement.

   **Done.** `scripts/ci/site-catalogue.py` derives it into `catalogue.json` and the
   catalogue page renders one line per stack — `2 services · MariaDB` beside
   `3 services · PostgreSQL + Redis`, `1 service · GPU required` for `apps/vllm`,
   `GPU optional` for `apps/ollama` from its overlay. Nothing is typed and nothing
   needs keeping current. Measured against the tree while scoping this, and
   unchanged by the implementation:

   | Fact | Source | State |
   |---|---|---|
   | Runtime service count | the stack's own compose files | derivable; one-shot containers are distinguishable by `restart: "no"`, of which the tree has one |
   | Required infrastructure — PostgreSQL, MariaDB/MySQL, Redis/Valkey, Memcached, object storage, Elasticsearch, ClickHouse, RabbitMQ | service images | derivable; 47 of 87 stacks need no database at all |
   | GPU required | `deploy.resources.reservations.devices` in production compose | derivable — `apps/vllm` today |
   | GPU optional | the same, declared only in an overlay | derivable now that overlays are discovered — `apps/ollama` today |

   **Not derivable, and must not be faked.** Upstream's published minimum or
   recommended memory, and any storage requirement that materially affects a
   deployment, need explicit per-stack metadata with a source. Real idle, typical and
   peak figures need a host, which is the same evidence
   [`resource-measurement.md`](resource-measurement.md) governs — record them only
   where this repository has actually measured them.

   **A memory ceiling is not a consumption figure.** `resource-measurement.md` already
   states the ceilings in the tree are derived by rule and deliberately generous.
   Publishing one as "RAM required" would turn a safety boundary into a false fact.

**Source of truth.** One model for all five layers, not a second metadata system
per dimension. Evaluate extending the per-stack `UPSTREAM.md` first, with
`sovereignty-report.py` / `sovereignty.json` and `site-catalogue.py` generating the
views, before considering any new file. Where the repository already knows a fact —
every footprint fact in the table above — generate it from the compose files rather
than recording it by hand; explicit metadata is for what only upstream can answer.

**On the site.** Each product exposes the five facts compactly, plus the official
links. One reusable page explains the concepts — MIT, GPL, AGPL, source-available,
open-core — so no product page repeats them, and states plainly that *licence is not
edition is not pricing*, and why **installing software for a customer** and
**running it as a hosted service for them** can have different licence consequences.
Factual decision support, not legal advice.

No ratings, no traffic lights, no recommended winner, and no "lightweight" or "heavy"
label. A shorter form may be shown only if it is derived mechanically from these facts
and the facts stay visible beside it. The operator decides.

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
| — licence review | Remove | Satisfied: every stack carries `License` and `Origin`, CI-checked, and each non-OSI stack's restriction is named in its field; the policy moved to `provenance.md` |
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

## F. What the stabilization programme did

| PR | What it changed |
|---|---|
| [#115](https://github.com/rubennati/secure-docker-blueprint/pull/115) | Repository truth: roadmap restructured around what blocks v1.0, stale counts corrected at their owners, licence policy moved to `provenance.md`, lifecycle pin reader fixed, this report added |
| [#119](https://github.com/rubennati/secure-docker-blueprint/pull/119) | Generated site catalogue — all 89 stacks across 14 domains, from `Domain` and `Role` in each `UPSTREAM.md`, with `site-catalogue.py --check` in CI |
| [#124](https://github.com/rubennati/secure-docker-blueprint/pull/124) | Opt-in overlays became deployment variants: merged with their stack through `docker compose config` and judged on the effective result. Six were previously checked by nothing, and the gap had hidden two overlays Compose refused outright, three services without ceilings, a Compose tag that made a file invisible, and a pin that resolved to an empty tag |
| [#125](https://github.com/rubennati/secure-docker-blueprint/pull/125) | GitHub Issues took ownership of the work they describe; the single-maintainer review policy became an explicit decision; the deployable scope (205 services) was separated from the checker universe (209) and every hardening figure restated against it |
| [#126](https://github.com/rubennati/secure-docker-blueprint/pull/126) | The local evaluation path became discoverable on all 79 stacks that have one, under one name — `Try it locally`. 26 site pages stopped presenting Traefik and a domain as application prerequisites. `unlisted-stack` now fails when a stack is missing from its category README |

Issues closed on that evidence: #34, #35 (#125), #43, #44 (#126).

## G. Remaining work

Nothing below is a structural defect. Each is host evidence, a decision, or work
deliberately deferred.

**Needs a host — no edit can close these**

| | Owner |
|---|---|
| 75 of 89 stacks `scaffolded` (S1) — the largest item | this file, D1 |
| Beszel per-container metrics through the socket proxy | [#36](https://github.com/rubennati/secure-docker-blueprint/issues/36) |
| Portainer first load against `rl-hard`'s burst of 40 | [#37](https://github.com/rubennati/secure-docker-blueprint/issues/37) |
| Seafile's four path-scoped routers | [#39](https://github.com/rubennati/secure-docker-blueprint/issues/39) |
| What images tolerate `cap_drop`, `read_only`, non-root (S3) | [#40](https://github.com/rubennati/secure-docker-blueprint/issues/40) |
| Trivy's one-off CRITICAL assessment before it can block (C1) | this file |

**Needs a decision from the maintainer**

| | Where |
|---|---|
| Seafile Pro: back up the search index or document it as rebuilt | [#45](https://github.com/rubennati/secure-docker-blueprint/issues/45) |
| Renovate: install it or remove the dormant configuration (R11) | D5 |
| Three project-name mismatches, where a rename moves live volumes (R12) | D6 |
| Personal data on the public site (W7) | D3 |
| Restore sections: 85 of 89 READMEs have none (S2) | D2 |

**Deferred by design, scoped but not built**

- **W8** — catalogue decision facts, five layers, scoped in
  [Catalogue decision facts](#catalogue-decision-facts). Layer 5, the operational
  footprint, is generated. Layer 1, the licence, already existed and the site shows
  its class. What is left is layers 2–4 — use rights per right, edition gating, and
  the commercial model — none of which is derivable: each needs the upstream terms
  read for one stack at a time, with the source recorded beside the answer.
- **R13** — dated working records under `docs/`. Kept as evidence.
- **S4** — ShellHub pins a release candidate, which upstream publishes as its only
  tag. Revisit at the first stable release.
- **A one-command local workflow and a production deployment lifecycle** — both
  design questions, neither started. #126 normalised the local surface enough that
  the first can now be designed against a real contract: one invocation shape,
  loopback-only ports, and a known set of exceptions. The second still has open
  architecture questions — how a server records which blueprint release it runs,
  deployment order, blueprint updates versus upstream image updates, and rollback.
- **Priority 2 applications** — on hold.

## Decisions required

| ID | Question | Recommendation |
|---|---|---|
| D1 | Is "every stack verified or carrying a reason" the v1.0 gate for all 89, or for a defined subset? | Keep the gate; make the reason mandatory and short, per stack, in `UPSTREAM.md`, so a `scaffolded` stack at v1.0 is a stated fact rather than an omission |
| D2 | Must each stack README link the restore standard, or is the standard plus the Backup section enough? | Link it — one line per README, mechanical |
| D3 | Adopt the encrypted-personal-data design for the site, and does an unresolved D3 block v1.0? | Adopt it; if it is not implemented, v1.0 should say so rather than ship a template that publishes its author's imprint |
| D4 | Does v0.10.0 remain a release, or does measurement become continuous, applied when a stack is verified? | Continuous — the measurement needs the same host session as S1 |
| D5 | Install Renovate or delete `renovate.json` and its proposal? | Delete — Dependabot already covers Actions and npm, no pin carries a `# renovate:` marker, and no Renovate pull request has ever been opened |
| D6 | Resolve the three project-name mismatches by editing `.env.example` or the directory? | Neither before v1.0 — a rename breaks live deployments; record it as an exception |
| D7 | Should a local pin track its production pin by default? | **Decided — yes, enforced.** No exception list was needed: joining on the image repository rather than the variable name makes the legitimate cases fall out. `apps/vllm` runs the CPU build locally and is never compared; a service the local stack does not run is simply absent. 41 pins synchronised, Version Chain step 4 added |
