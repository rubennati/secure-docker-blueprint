# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-10-31

- **Phase:** pre-1.0. Latest tag `v0.9.5` (2026-10-30), which is where `main`
  stands; what `dev` carries beyond it is `git rev-list --count v0.9.5..dev`, and
  it is not repeated here. Work happens on a
  short-lived branch and reaches `dev` through a pull request; `dev` reaches
  `main` the same way. Both branches reject a direct push.
- **Last completed:** the stabilization programme, in two runs. The first was PRs
  #115, #119, #124, #125, #126. The second closed R14 and R15, built and corrected
  W8's system, and wrote the production deployment lifecycle
  ([`../docs/standards/deployment-lifecycle.md`](../docs/standards/deployment-lifecycle.md)).
  What each changed, what remains and why:
  [`../docs/v1-readiness-audit.md`](../docs/v1-readiness-audit.md) → *What the
  stabilization programme did* and *Remaining work*. Actionable items are GitHub
  Issues; [`tasks.md`](tasks.md) holds only what no issue owns.
- **Also completed (2026-09-21/22):** the candidate batches A–G (#140, #145, #146,
  #150, #153, #156, #159, #160, #161, #162) —
  twelve stacks added as a recorded exception to the application hold
  ([`decisions.md`](decisions.md), 2026-09-21), six held as evaluation entries,
  and one fix they surfaced in `business/akaunting`. Evidence per product:
  [`../docs/audits/candidate-evaluation-2026-09-21.md`](../docs/audits/candidate-evaluation-2026-09-21.md).
  Host verification ran on 2026-09-22: `Last verified` for nine, three recorded
  with a limitation; what is left is upstream requests and follow-ups —
  `tasks.md` §6.
- **Also completed (2026-09-24):** the candidate batches H–V, decided on
  2026-09-22 as a second recorded exception to the hold
  ([`decisions.md`](decisions.md)). Sixteen stacks landed, one per pull request,
  each `scaffolded`. Batch V added none: Coraza's condition — a maintained Traefik
  integration — is not met, and the capability is already here because CrowdSec's
  AppSec engine is Coraza, so what was missing was documentation; Suricata's two
  remaining questions need a host that can be flooded without consequence. Both in
  `decisions.md`, 2026-09-24. What was not added and why:
  [`../docs/audits/candidate-evaluation-2026-09-22.md`](../docs/audits/candidate-evaluation-2026-09-22.md).
  Moving the sixteen from `scaffolded` to `baseline-aligned` is S1, `tasks.md` §2.
- **Decided (2026-10-03):** three mail servers — Stalwart, docker-mailserver and
  jeboehm/docker-mailserver — as a third recorded exception to the hold
  ([`decisions.md`](decisions.md)). Mailu is held until a release carries the fix
  for CVE-2026-86008. `apps/stalwart`, `apps/docker-mailserver` and
  `apps/mailserver-jeboehm` are in, each `scaffolded`, with the mail ports
  published by an opt-in overlay. Evidence:
  [`../docs/audits/candidate-evaluation-2026-10-03.md`](../docs/audits/candidate-evaluation-2026-10-03.md).
  What a host still has to establish for each is `tasks.md` §8.
- **Audited (2026-10-15):** the core layer — Traefik, CrowdSec, the update path and
  this working memory — has its findings register in
  [`../docs/audits/core-v1-readiness-2026-10-15.md`](../docs/audits/core-v1-readiness-2026-10-15.md):
  66 findings with evidence, a programme in phases 0–6, and twelve decisions, all
  taken on 2026-10-15 and 2026-10-16 and recorded in [`decisions.md`](decisions.md).
  Phases 1–4 are merged: 1–3 as #231–#239; Phase 4, the middleware model, as
  4.1 and 4.2 (#241, #242), 4.3, the cut (#258, 2026-10-23), and 4.4, the
  documentation (#262–#264, 2026-10-24). Phases 5–6 have not started. Decisions
  D1–D8 of 2026-10-18 are in [`decisions.md`](decisions.md); every router's
  before and after is
  [`../core/traefik/docs/middleware-model-migration.md`](../core/traefik/docs/middleware-model-migration.md).
- **Released: v0.9.5** — the middleware model and its documentation, a
  breaking change with a migration (decided 2026-10-23,
  [`decisions.md`](decisions.md)). The targeted test decided on 2026-10-25 ran
  on 2026-10-30: the migration from v0.9.4 on a disposable installation, by
  [`../core/traefik/docs/middleware-model-migration.md`](../core/traefik/docs/middleware-model-migration.md)
  §4, with no abort condition met. The proofs its §5 lists stay open for a
  later host session, and so does a host with a global IPv6 address
  (`core/traefik/README.md`, *Not verified on a host*, item 8); the release
  says so.
- **Decided (2026-10-31): the ingress target architecture**, after an audit of the
  whole ingress path and a lab run with three stacks
  ([`../docs/audits/ingress-architecture-2026-10-31.md`](../docs/audits/ingress-architecture-2026-10-31.md)):
  an edge network per installed stack as the default for new installations, the
  shared network as a documented choice, `access-trusted` with declared ranges
  in place of `access-lan`, a stated auth posture per stack, exposure derived and
  shown — DEC-075 to DEC-078 and an addendum to DEC-063 in
  [`decisions.md`](decisions.md). An eight-step programme follows
  ([`tasks.md`](tasks.md) §11); step 1, the guards, is this branch. No existing
  installation changes until it declares something.
- **Current milestone:** v0.10.0 — Measured resource limits. Whether
  it stays a release is open (D4 in the audit): the measurement needs the same
  host session as the verification backlog.
- **Definition of done for v0.10.0:** every `✅` stack's limits come from a
  measurement on a real install rather than from the derivation rule
  (`docs/resource-measurement.md`).
- **The one thing to know first:** nothing structural is broken. The
  checkers, the generated views and the site catalogue agree with the tree. What
  is left needs a host, or a decision that is written down and waiting. C1, the missing
  Trivy gate, is closed: `.trivy-baseline.json` records the CRITICAL findings that
  exist and `scripts/ci/trivy-gate.py` fails the scan on any that is not recorded.
  **No finding of the stabilization audit is marked FIX BEFORE V1 any more** —
  everything else open there is evidence, a recorded decision, or standing research
  coverage. The core audit of 2026-10-15 opens its own, listed in that file by phase.

## Snapshot

- Stack inventory, per-stack status, pinned version and verification date:
  [`../LIFECYCLE.md`](../LIFECYCLE.md). Read it for any current figure — it is
  generated from the owners in `docs/standards/status-model.md`, and no count is
  repeated in this file. After a status change or a pin, regenerate with
  `python3 scripts/ci/lifecycle-report.py --write`.
- Monitoring verified on a host on 2026-09-08 (v0.8.0): ntfy, Healthchecks,
  Uptime Kuma, Beszel and changedetection.io, each with an alert that reached a
  phone outside the tailnet. ntfy is public and read-only on its topics, the
  operator's side stays behind the VPN. Proof table in `monitoring/README.md`.
- Backup architecture designed (`backup/README.md`): five layers, host-installed
  agent, snapshot/backup/archive kept distinct.
- `backup/borgmatic/` — configuration, systemd timer, setup and restore playbook.
  Host-installed, no Compose stack. Backed up from and restored from on
  2026-07-29; the rehearsal is logged in `backup/borgmatic/RESTORE.md`. Where a
  repository lives is the adopter's configuration, not this repository's debt —
  append-only enforcement is the one documented mechanism a local rehearsal
  cannot establish.
- `backup/urbackup/` — client and endpoint backup, bridge networking with the web
  interface behind Traefik, host-networking overlay opt-in. Never started.
- Status model unified (`docs/standards/status-model.md`); `LIFECYCLE.md` generated
  by `scripts/ci/lifecycle-report.py`; both structure and status enforced in CI.
- Local test stacks: `docker-compose.local.yml` wherever a stack shows something
  run alone, so an application can be tried before any server exists. Shape in
  `docs/standards/compose-structure.md`, coverage in the generated Local column.
- Trivy scans every image the checkers discover rather than a hand-kept list, and
  reports images it could not pull instead of passing over them — currently
  Langfuse's two images, each acknowledged in `.trivy-baseline.json` for Docker
  Hub's anonymous pull rate limit, and MinIO, whose images are withdrawn.
  Each image's full findings go to a per-run artifact; the job summary carries
  the count-level index (`scripts/ci/trivy-summarize.py`) instead of a raw
  per-image table in the log. The vulnerability database is cached across runs,
  one entry per UTC day; Trivy's own staleness check still governs refreshes.
  CLI pinned to `v0.74.0`. Trivy's own exit code stays 0; `scripts/ci/trivy-gate.py`
  fails the job on a CRITICAL finding not recorded in `.trivy-baseline.json`. Both
  scan jobs are required checks on `main` since 2026-09-25
  ([`decisions.md`](decisions.md#dec-070)).
- CI jobs and what each one blocks on: [`quality-gates.md`](quality-gates.md),
  documented per job in `docs/standards/ci.md`. All ten are required on a pull
  request into `dev` and into `main`, which requires the two image-scan jobs as
  well — twelve in all; both rulesets require the branch to be up to date before
  merging. CodeQL reports on the same pull requests and is not
  a required check.

## Priority 1 functional expansion — complete 2026-09-19

Custom Development, AI/Local AI, Document/Data Processing, PAM/bastion,
secret-sharing and security-tooling capabilities, each landed as its own pull
request. What each stack found that changed its shape is in that stack's
`UPSTREAM.md`; what belongs to the architecture is in `docs/architecture.md`.

| Batch | Landed | PR |
|---|---|---|
| `development/` domain, `static-site`, `web-api` | 2026-09-18 | #106 |
| `apps/docling-serve` | 2026-09-18 | #107 |
| `apps/greenmail`, `apps/windmill` | 2026-09-18 | #108 |
| `apps/qdrant`, `apps/ollama`, `apps/vllm` | 2026-09-18 | #109 |
| optional host watchdogs | 2026-09-18 | #111 |
| PAM/bastion alternatives | 2026-09-19 | #112 |
| secret sharing, Threat Dragon | 2026-09-19 | #113 |
| zot, step-ca, OpenCanary, Dependency-Track, DFIR-IRIS, Velociraptor | 2026-09-19 | #114 |
| LiteLLM, Open WebUI, agentgateway | 2026-09-19 | #116 |
| Dify, Langfuse | 2026-09-19 | #117 |

## v0.8.1 on a host — 2026-09-13

Released from `dev` to `main` and then run on the test host, in that order. Traefik moved
3.6.10 → 3.7.13 with socket-proxy v0.5.0; whoami, Uptime Kuma, changedetection.io,
Nextcloud (34.0.4 in place), Invoice Ninja (5.13.40, migrations) and Cal.diy's database
(17.11) followed. All seven carry a `Last verified` of 2026-09-13. What the run surfaced
and where it went: an orphaned container after a service rename blocks `up -d` and leaves
the app created-not-started (`TROUBLESHOOTING.md` §5.3); the host's rendered Traefik
config carried the CrowdSec integration while the tracked templates did not, so
`render.sh` did not run for the move — it would have dropped both; the switch, `CROWDSEC_BOUNCER_ENABLED`, landed on 2026-09-14 and that host was migrated the same day; 3.7.12+
warns per entrypoint that `aliasHeadersStrategy` is unset (recorded in `UPSTREAM.md`).
Still unverified from the sweep: `core/dnsmasq`, `apps/homepage`, `apps/librephotos` and
the pins of stacks that host does not run.

## Capability architecture — established 2026-09

The blueprint is described as **capabilities** with at most one maintained
**reference implementation** each. `docs/architecture.md` owns the model; stack
READMEs stay product documentation. The directory split by access pattern is
unchanged — the capability model is a layer above it.

| Capability | Reference | State |
|---|---|---|
| Foundation (Host thin · Docker · Network · Secrets · Backup · Updates · Lifecycle) | the standards | prerequisite |
| Reverse Proxy | Traefik | implemented |
| Identity & Access | Authentik | implemented, per app |
| Threat Detection & Remediation | CrowdSec | implemented |
| Web Application Security | CrowdSec AppSec, whose engine is Coraza | implemented, opt-in |
| Network Security / IDS | — | evaluation candidate, deferred 2026-09-24 |

Three states are kept apart: **implemented**, **documented alternative**,
**evaluation candidate**. Controls follow exposure, not a numbered ladder. An
application does not intrinsically require Traefik — it requires the reverse-proxy
capability when served over a network.

### CrowdSec

"Phase 1 / 2 / 3" is retired from current documentation. The model is **Core**, and
two independent remediation points below it — **Reverse-Proxy Remediation** and
**Host-Firewall Remediation**. Neither depends on the other. Core detects and serves
decisions and blocks nothing on its own.

**Verified on a live host:** set-only behaviour and its IPv4/IPv6 asymmetries, the
prepare/cleanup lifecycle including restart, the four-condition readiness gate,
fail-open of the scope companion, the shape of the scoped FORWARD rules (one rule
per family, ingress-interface match, no INPUT chain, no management-interface rule),
restart ordering with enforcement active, structural management-plane exclusion, and
the outbound half of `ct original`.

**Blocked, not defective:** enforcement against real traffic. Five tests need one
prerequisite the test host lacked — a second machine whose traffic the operator
controls, reachable over both the management network and the public internet:
peer-initiated management-path adverse test, controlled public IPv4 drop, controlled
public IPv6 drop, inbound/mid-session `ct original`, guarded reboot acceptance.
Tracked in [`tasks.md`](tasks.md) → "Blocked on a host"; sequence and evidence in
`core/crowdsec/docs/firewall-bouncer.md` → "Verification status".

**Known limitation.** `crowdsec-firewall-bouncer 0.0.25-5+b11` enforces individual
IPv4 and IPv6 source-IP decisions correctly. A CIDR/range decision degrades silently
to its network address, and interval-capable nftables sets cannot be populated by
this version at all — so `flags interval` must not be set. Version-specific;
re-evaluate on upgrade. Owner: `core/crowdsec/UPSTREAM.md`.

### Traefik certificates

The dashboard follows the selected certificate strategy instead of always requesting
its own certificate. Coverage is validated as the real relationship between
`TRAEFIK_DASHBOARD_HOST` and `ACME_WILDCARD_DOMAIN`. The shipped `.env.example`
preselects no strategy and validation stops until one is chosen — three strategies
are supported and none is prescribed. Migration is forward-looking only: Traefik
renews every certificate in its ACME storage regardless of router references and
documents no way to retire one.

### Names kept as they are

`APP_TRAEFIK_*` and `TAILSCALE_CIDR_*` keep their names — the variables honestly
describe the current reference implementation, and no maintained second
implementation justifies a migration; the policy itself is `access-vpn` since the
middleware model, and the rename of the CIDR variables to `VPN_CIDR_*` is deferred
to a change of its own (D7, 2026-10-18). A future architectural consideration, not
debt.

Suricata and Coraza were decided on 2026-09-24 ([`decisions.md`](decisions.md)):
neither becomes a stack — CrowdSec's AppSec engine is Coraza, and Suricata waits for
a host that can be flooded without consequence. What stands and why:
[`../ROADMAP.md`](../ROADMAP.md#added--the-held-candidates). SIEM/XDR/SOC platforms
are out of scope there.

## Mission scope — established 2026-09

The mission now covers custom applications alongside existing self-hosted
open-source software. Three-layer distinction (physical layout, conceptual
domain, website navigation) and what stays out of scope: `docs/architecture.md`
→ "Physical layout, conceptual domains and navigation"; reasoning in
`decisions.md`.

That path now has a standard — `docs/standards/custom-application.md`, derived
from `business/vikunja` and `apps/caldiy`, the two stacks that already build
their own image. It owns source, build, image identity and verification only;
everything after the image is unchanged. Four binding rules, and practices seen
in only one of the two shapes are recorded as non-binding. Still absent: a
first-party application, source with no upstream.

## Host resilience — policy in place 2026-09, mechanism deferred

An OnlyOffice process on a derived deployment took a host down; the stack's own 4G
ceiling would have contained the resident-memory half of it, so that part reads as
deployment drift rather than a gap. The investigation found three real ones, and
this phase closes the policy side of them.

**In place.** Swap is bounded per service: `memswap_limit` equal to `memory` means no
swap and is the default, a higher value is a justified exception, and unset is no
longer acceptable — Docker otherwise grants as much swap again as the memory limit,
which is how a container inside its cap still pages a host into uselessness.
`security-baseline.md` owns the requirement, `compose-structure.md` the values.
`no-resources` and `no-swap-policy` are both FAIL in `check-structure.py` —
Every production service states `memswap_limit`, all at the default (equal to
`memory`); no evidenced case for a higher value has come up yet. `live-restore` is in the daemon
configuration the operator site documents (`site/src/content/docs/getting-started/server-setup.mdx`);
no stack in this repository ships a `daemon.json`. `resource-measurement.md` carries a drift procedure — compose
config against `docker inspect` against cgroup state — and the corrected meaning of
`reservations.memory`, which is a reclaim preference and never a guarantee.
`TROUBLESHOOTING.md` §4.6 covers the swap-pressure symptom.

**Deferred.** The host reserve is approved as an invariant — workload pressure must
not consume what management and recovery need — and its mechanism is not installed.
The candidate is a separate cgroup hierarchy for workloads with memory protection on
the management slice; it needs a rehearsal on a disposable host first, and what that
rehearsal must establish is in `docs/architecture.md`. Tracked in
[`tasks.md`](tasks.md).

**v0.10.0 work.** Per-workload memory and swap calibration, from measurement.

**Monitoring follow-up.** Alerts on `OOMKilled`, restart-count growth, swap usage and
memory PSI — none covered by the thresholds v0.8.0 verified. Tracked in
[`tasks.md`](tasks.md), not started here.

## Immediate next steps

The disposable host carried v0.7.0, v0.8.0 and v0.8.1 (2026-09-13), then the
candidate sessions of 2026-09-21 to 2026-09-23. What runs on it next, in this
order:

0. **Finish CrowdSec host-firewall acceptance** once a controllable second client
   exists — see the blocker above. Nothing else in CrowdSec is waiting.
1. **Switch borgmatic's run monitoring on** — it points at
   `monitoring/healthchecks`, which now exists and has been proven in a closed
   circuit. This is what turns a silent backup timer into an alert.
2. **What v0.7.0's session left open** —
   [`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md) Blocks 3
   and 4: UrBackup has never been started, and nine major versions are pinned
   and never run. Neither gated a tag; both still need the host.
3. **Feeding v0.10.0** — start the sampler in
   [`../docs/resource-measurement.md`](../docs/resource-measurement.md). Every
   container started is a measurement opportunity, and v0.10.0 cannot be
   prepared any other way. Five monitoring stacks are already running.
4. **The middleware model on a host** — after the migration test that precedes
   v0.9.5, the proofs
   [`../core/traefik/docs/middleware-model-migration.md`](../core/traefik/docs/middleware-model-migration.md)
   §5 lists.

## Open decisions

What still needs a decision, and since when, is read from the register at the
top of [`decisions.md`](decisions.md): *Needs the maintainer* lists each such
entry and links it. This section keeps the context behind those questions and
the measurements that shaped the settled ones.

Each is written to be answerable from this file alone: the conflict, the
options, and a recommendation. None blocks the host session.

Settled on 2026-10-15 — D9 of the core audit, recorded in
[`decisions.md`](decisions.md): the commit message format (practice converged on
the standard's `scope:` form; the rules are unchanged), backup repository isolation
(`docs/architecture.md` adopts the trade-off `backup/README.md` states), the
host-installed backup agent (a named exception beside the portability goal in
`docs/architecture.md`), and the commit procedure (the standing rule to ask before
every commit).

**1. Dependency automation** — decided 2026-10-15 as
[DEC-057](decisions.md#dec-057), D6 of the core audit: Renovate detects upstream
releases, every pin carries a marker, proposals arrive as pull requests and
nothing is adopted automatically. Not started — `renovate.json` is committed
(2026-09-17), no pin carries a `# renovate:` marker and the App is not installed,
so nothing runs. Of the three sub-questions this item held, the entry settles the
first (explicit markers rather than normalising the 28 outlying comments);
Renovate App vs. self-hosted Action and whether `site/`'s unwatched
`package-lock.json` rides along are implementation questions it leaves open.
[`../docs/renovate-proposal.md`](../docs/renovate-proposal.md) remains the design.

**The Traefik middleware model — settled.** The review this section announced ran
on 2026-10-17/18 ([`../docs/audits/traefik-architecture-review-2026-10-17.md`](../docs/audits/traefik-architecture-review-2026-10-17.md))
and its eight decisions ([`decisions.md`](decisions.md), 2026-10-18) were applied
as Phase 4.3 of the core audit (#258, 2026-10-23): four positions on every router
— access, limit, headers, auth — threat enforcement and compression on the
entrypoint, three header profiles, each starting with the HSTS base, one TLS
standard, no alias. Phase 4.4 (#262–#264, 2026-10-24) brought the standards, the
core and stack documentation and the site to the model; `check-prose.py` fails
on a retired name in current documentation since then, records excepted. What
the measurements led to, router by router, is
[`../core/traefik/docs/middleware-model-migration.md`](../core/traefik/docs/middleware-model-migration.md).

The measurements that shaped it, in the order taken, with the values before the
model: 2026-09-07 (Traefik v3.6) — a header block replaces the application's own
header, and a header removal placed after the chain has no effect; 2026-09-22 —
the first loads of Open WebUI (173 requests), Windmill (about 850), Twenty (412),
Langfuse (152) and LiteLLM (160) against buckets of 50, 200 and 500, with the
`429` counts per bucket; 2026-09-23 — Twenty and Windmill load under a bucket of
1000 without a `429`, five loads each; 2026-10-03 — the interim counters
(125/200, 125/500, 125/1000, 20/40, and 1000/1000 for sync clients, after the
Nextcloud client's 20 parallel requests and the Seafile client's three threads per
direction); 2026-10-15 — 108 stacks route through Traefik, 105 take their values
from `.env`; 2026-10-18 — the lab proofs of the model (entrypoint order, TLS
inheritance, compression on streams, HSTS placement, four applications' own
headers, the forged-header test). Still open, owned by the migration document's
last section: the `429` count per public stack under the bucket of 500, the
office servers' and Nextcloud's own headers, and every host proof.

## Active constraints

- **A host to experiment on, not a host at all.** What the open milestones need
  is a machine that may be broken, filled with throwaway data and restored into.
  Every verification this repository records came from such a throwaway
  installation; none of its stacks is a production system this repository
  operates. That is the single precondition behind v0.8.0 and v0.10.0, and it
  is what v0.7.0 needed before it could close.
- **Real values never enter the repository.** On the host, `.env` carries the real
  domain and real secrets and is gitignored. Committed files use `example.com`
  and documentation IP ranges only. This matters more during a host session than
  at any other time, because that is when real values are at hand.
- Nine major version bumps are pinned but never started, and the stacks still
  carrying the pre-v0.5.1 `Last checked:` field are marked ⚠️ in `LIFECYCLE.md`.
  Both ride along with the host session.
- Public repository: the rule is
  [`../docs/standards/commit-rules.md`](../docs/standards/commit-rules.md#public-content)
  — no real domains, IPs, hostnames or personal data; no session context or
  personal attribution in committed content; what CI enforces of it is listed
  there. `.ai/` is committed and therefore public — it holds working context,
  never internal process detail. This is the rule, not a description of the
  tree. `site/` is the named exception
  and still carries the domain, the legal notice and a contact address; the
  direction that removes them is in [`../ROADMAP.md`](../ROADMAP.md), and the
  inventory there is not yet complete.
