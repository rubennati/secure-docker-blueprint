# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-10-15

- **Phase:** pre-1.0. Latest tag `v0.9.4` (2026-10-04), which is where `main`
  stands; what `dev` carries beyond it is `git rev-list --count v0.9.4..dev`, and
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
  Phases 1–3 are merged (#231–#239). Phase 4, the middleware model, is in its
  fourth step: 4.1 and 4.2 merged (#241, #242); 4.3, the cut, prepared on
  `feature/traefik-hard-cut` as five commits awaiting review; 4.4, the
  documentation, next. Phases 5–6 have not started. Decisions D1–D8 of
  2026-10-18 are in [`decisions.md`](decisions.md); every router's before and
  after is
  [`../core/traefik/docs/middleware-model-migration.md`](../core/traefik/docs/middleware-model-migration.md).
- **Current milestone:** v0.10.0 — Measured resource limits. Whether it stays a
  release is open (D4 in the audit): the measurement needs the same host session
  as the verification backlog.
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
  fails the job on a CRITICAL finding not recorded in `.trivy-baseline.json`. It
  is not a required check.
- CI jobs and what each one blocks on: [`quality-gates.md`](quality-gates.md),
  documented per job in `docs/standards/ci.md`. All ten are required on a pull
  request into `dev` and into `main`, and both rulesets require the branch to be
  up to date before merging. CodeQL reports on the same pull requests and is not
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

`APP_TRAEFIK_*` and `acc-tailscale` keep their names — they honestly describe the
current reference implementation, and no maintained second implementation justifies
a migration. A future architectural consideration, not debt.

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
4. **The security chains** — the open decision below; one Traefik pull request
   plus one per moved stack.

## Open decisions

Each is written to be answerable from this file alone: the conflict, the
options, and a recommendation. None blocks the host session.

Settled on 2026-10-15 — D9 of the core audit, recorded in
[`decisions.md`](decisions.md): the commit message format (practice converged on
the standard's `scope:` form; the rules are unchanged), backup repository isolation
(`docs/architecture.md` adopts the trade-off `backup/README.md` states), the
host-installed backup agent (a named exception beside the portability goal in
`docs/architecture.md`), and the commit procedure (the standing rule to ask before
every commit).

**1. Dependency automation** — see
[`../docs/renovate-proposal.md`](../docs/renovate-proposal.md)
`renovate.json` is committed (2026-09-17) and the App is not installed, so nothing
runs. Three sub-questions: explicit `# renovate:` markers vs. normalising 28
outlying comments · Renovate App vs. self-hosted Action · whether `site/`'s
unwatched `package-lock.json` rides along. Now D6 of the core audit, with its
recommendation there.

**The security chains replace what an application sets.** Measured on 2026-09-07 (Traefik v3.6): every value in an `hdr-*` block replaces
the application's own header — Keycloak's and Nextcloud's `no-referrer` become
the weaker browser default under level 3, HSTS loses `includeSubDomains` under
level 2 — and a `customResponseHeaders` removal only takes effect ahead of the
chain, so `business/matomo` and `apps/vaultwarden` still carry an ineffective
one. The presets assume a bare application; the ones shipped set their own.
→ *Recommendation:* a chain family without a header block (`sec-own`,
`sec-own-spa`) plus single-purpose blocks an application appends (`hsts`,
`permissions-policy`, a per-app CSP where upstream names one); the numbered
presets stay for applications that set nothing. Keycloak, Authentik,
Nextcloud, Vaultwarden and Matomo move after a measurement each, and Keycloak
also needs an access policy for the stacks that call it and a router for its
admin paths.

**The rate limits break code-split interfaces as well.** Measured on the test host
on 2026-09-22, with a browser engine and with a replay of each first page load
over one HTTP/2 connection. Open WebUI requests 173 files: under `sec-2` (burst
50) 65 came back `429` and the interface showed an error, under `sec-2-spa` (burst
200) none. Dify's workflow editor requests 291, of them 164 static files: 64 × `429`
under `sec-2`, none under `sec-2-spa`. Windmill requests about 850 and fails under
both — 412 × `429` under `sec-2-spa`. Langfuse (152) and LiteLLM (160) stayed
under the limit. Of the twelve candidate stacks, CISO Assistant (77 files, 14 ×
`429` under `sec-2`) moved to `sec-2-spa`; Twenty requests 412 and serves its
assets with `max-age=0`, so a warm browser revalidates every one — `429` under
both chains, as Windmill; the other interfaces stayed under `sec-2`
(DefectDojo 42 on its dashboard, ERPNext 67 on its desk, calnode's admin
interface 54).
→ *Decided 2026-09-22:* no stack drops to `sec-1` to get past a limit. The
measurements go into the review below.
→ *2026-09-23:* the questions behind this — what the proxy owns, what its limits
are measured against, where the client address comes from with a CDN proxy in
front, and what threat enforcement already covers — are collected in
[`../docs/audits/reverse-proxy-limits-2026-09-23.md`](../docs/audits/reverse-proxy-limits-2026-09-23.md).
→ *2026-09-23:* `rl-spa-xl` (average 100, burst 1000) and `sec-2-spa-xl` exist for
the two interfaces whose first load does not fit 200. The bucket holds one whole
first load; `check-structure.py` fails an `-xl` chain outside `acc-private` or
`acc-tailscale`. Measured 2026-09-23 behind Traefik with TLS with the shipped
`acc-tailscale`: Twenty's interface (412 requests) and Windmill's (about 850)
load under `sec-2-spa-xl` without a single `429`, five loads each. Both ship the
chain now; no other stack uses it.
→ *2026-10-03:* the limits are widened as an interim, so the bucket sizes named
above are the ones in force when each measurement was taken. Now: `rl-soft` 125
requests per second, burst 200 · `rl-spa` 125, burst 500 · `rl-spa-xl` 125, burst
1000 · `rl-hard` 20, burst 40. Sync clients met the sustained rate rather than the
burst — the Nextcloud client runs up to 20 requests in parallel, the Seafile
client three threads in each direction — so `rl-sync` (1000 per second) exists,
in `sec-2-sync` and `sec-3e-sync`, shipped by `apps/seafile`, `apps/seafile-pro`
and `apps/nextcloud`. Not counted on a host yet. Reasoning in
[`decisions.md`](decisions.md), 2026-10-03; the review still decides what each
chain is for.

**Traefik labels and middlewares are reviewed as a whole before v1.0.0** — see
[`../ROADMAP.md`](../ROADMAP.md). They grew stack by stack; 108 stacks route
through Traefik, 105 of them take their chain from `.env` (counted 2026-10-15 —
`traefik.enable=true` over the production compose files, `APP_TRAEFIK_SECURITY=`
over the `.env.example` files). After v1.0.0 a renamed middleware disables the
router of every deployment that names it. Open, besides the two points above:

- **Names.** Fifteen chains put headers, framing and rate limit into one name.
  49 stacks default to `sec-2` and 36 to `sec-3`; `sec-0`, `sec-1`, `sec-1e`,
  `sec-3e` and `sec-3e-spa` are selected by no `.env.example`. `e` reads as
  "embeddable" and permits only the application's own
  origin. `spa` names a kind of application rather than what the chain changes, a
  burst of 200 — the chain file calls the `-spa` chains VPN-only, the block they
  use is described as fit for public applications. `sec-authentik` carries the
  chains' prefix but is an authentication gate, and the label pattern has no slot
  for it.
- **Fit per application**, Nextcloud for one: what an application needs to start
  without errors and stay responsive under a working day's load, and whether
  presets or per-application settings answer that. Every rate-limit figure above
  is a first page load; no stack has a measurement under sustained use.
- **CrowdSec.** 43 of those 101 stacks have no `APP_TRAEFIK_THREAT` slot, so a
  bouncer middleware cannot be attached from `.env`. The profile ladder is in
  [`../core/crowdsec/docs/profiles.md`](../core/crowdsec/docs/profiles.md).
- **Authentik.** Forward auth exists only as a commented-out block in
  `core/traefik/ops/templates/dynamic/integrations.yml.tmpl`.
- **Client address.** Confirmed against Traefik's reference on 2026-10-15: the
  access policies and rate limits evaluate the connecting address, because the
  templates set no `ipStrategy` and no `sourceCriterion`. An office behind one
  NAT address shares one bucket on every path; behind Cloudflare's proxy the
  closed policies refuse every request and one bucket serves every visitor
  behind an edge address, while the access log and the application see the
  client. Owner: `docs/standards/traefik-security.md` → Trusted Proxy Headers;
  the render switch that changes it is D3 in the core audit. Not measured on a
  host.
- **Mail protocols.** Decided 2026-10-03 ([`decisions.md`](decisions.md)): a mail
  stack publishes its SMTP and IMAP ports through an opt-in overlay, and
  `core/traefik` gets no TCP entrypoints. No access policy, chain or bouncer
  middleware applies to those ports; the mail server's own protections do. The
  review does not have to answer it. What each option would have changed:
  [`../docs/audits/candidate-evaluation-2026-10-03.md`](../docs/audits/candidate-evaluation-2026-10-03.md#across-the-list).
- **Already tracked.** First-load counts for the four photo galleries and
  `apps/it-tools` ([`tasks.md`](tasks.md), *Blocked on a host*), the chain for
  Seafile's four path-scoped routers (issue #39), and `acc-private` admitting the
  Docker bridge and host-local sources, which its own description does not say
  (issue #129). `core/portainer`'s first load fits `sec-4` (issue #37). Both open
  issues close through this review rather than beside it.

→ The review may change names and structure, or confirm them.

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
