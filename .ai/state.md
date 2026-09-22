# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-09-22

- **Phase:** pre-1.0. Latest tag `v0.9.1` (2026-09-19), which is where `main`
  stands; `dev` carries a substantial unreleased run beyond it — `git rev-list
  --count v0.9.1..dev` is the number, and it is not repeated here. Work happens on a
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
  What is left of it is upstream requests and host verification — `tasks.md` §6.
- **Current milestone:** v0.10.0 — Measured resource limits. Whether it stays a
  release is open (D4 in the audit): the measurement needs the same host session
  as the verification backlog.
- **Definition of done for v0.10.0:** every `✅` stack's limits come from a
  measurement on a real install rather than from the derivation rule
  (`docs/resource-measurement.md`).
- **The one thing a new session should know:** nothing structural is broken. The
  checkers, the generated views and the site catalogue agree with the tree. What
  is left needs a host, or a decision that is written down and waiting. C1, the missing
  Trivy gate, is closed: `.trivy-baseline.json` records the CRITICAL findings that
  exist and `scripts/ci/trivy-gate.py` fails the scan on any that is not recorded.
  **No finding is marked FIX BEFORE V1 any more** — everything else open is
  evidence, a recorded decision, or standing research coverage.

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
  `docker.n8n.io/n8nio/n8n`, hitting Docker Hub's anonymous pull rate limit.
  Each image's full findings go to a per-run artifact; the job summary carries
  the count-level index (`scripts/ci/trivy-summarize.py`) instead of a raw
  per-image table in the log. The vulnerability database is cached across runs,
  one entry per UTC day; Trivy's own staleness check still governs refreshes.
  CLI pinned to `v0.74.0`. Still `--exit-code 0` — the assessment pass
  `docs/security-verification.md` names as the prerequisite has not run yet.
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
| Dify, Langfuse | 2026-09-19 | pending review |

## v0.8.1 on a host — 2026-09-13

Released from `dev` to `main` and then run on the test host, in that order. Traefik moved
3.6.10 → 3.7.13 with socket-proxy v0.5.0; whoami, Uptime Kuma, changedetection.io,
Nextcloud (34.0.4 in place), Invoice Ninja (5.13.40, migrations) and Cal.diy's database
(17.11) followed. All seven carry a `Last verified` of 2026-09-13. What the run surfaced
and where it went: an orphaned container after a service rename blocks `up -d` and leaves
the app created-not-started (`TROUBLESHOOTING.md` §5.3); the host's rendered Traefik
config carried the CrowdSec integration while the tracked templates did not, so
`render.sh` did not run for the move — it would have dropped both — and an env-gated render is in `tasks.md`; 3.7.12+
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
| Web Application Security | CrowdSec AppSec | implemented, opt-in |
| Network Security / IDS | — | evaluation candidate |

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

Suricata and Coraza are evaluation entries in [`../ROADMAP.md`](../ROADMAP.md) →
"Evaluating"; neither is implemented. SIEM/XDR/SOC platforms are out of scope there.

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
`memory`); no evidenced case for a higher value has come up yet. `live-restore` is in the reference
daemon configuration. `resource-measurement.md` carries a drift procedure — compose
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

The disposable host carried v0.7.0 and v0.8.0. What runs on it next, in this
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

Each is written to be answerable without reading any chat history: the conflict,
the options, and a recommendation. None blocks the host session.

**1. Commit message format** — 1 minute
`docs/standards/commit-rules.md` prescribes `scope: subject`. Recent history uses
conventional commits (`docs(monitoring): …`). Both are defensible; having both is
not.
→ *Recommendation:* correct the standard to match the practice. The practice is
what everyone actually reads.

**2. Backup repository isolation** — 5 minutes
`docs/architecture.md:132` states one repository per app as a rule.
`backup/README.md:176` presents it as a trade-off. The File Map makes
`architecture.md` the owner, so the two disagree and the mirror is winning.
→ *Recommendation:* change it at the owner. The trade-off in `backup/README.md`
is the more honest text — separate repositories multiply the rehearsals, and a
rehearsal nobody runs is worse than a shared repository that has been restored
from.

**3. Host-installed backup agent vs. the portability goal**
`docs/architecture.md` promises "no host-specific assumptions beyond Debian +
Docker". `backup/borgmatic` is installed on the host by design, with the
reasoning in `backup/README.md`.
→ *Recommendation:* record it in `architecture.md` as a named exception with its
reason. The reasoning is sound; only the contradiction is unrecorded.

**4. Commit procedure**
`docs/standards/commit-rules.md` requires asking before every commit; an external
standard would allow an agent to commit to non-`main` branches unprompted.
→ *Recommendation:* keep the local rule. It has caught real mistakes, and the
cost is one question per commit.

**5. Dependency automation** — see
[`../docs/renovate-proposal.md`](../docs/renovate-proposal.md)
Three sub-questions: explicit `# renovate:` markers vs. normalising 28 outlying
comments · Renovate App vs. self-hosted Action · whether `site/`'s unwatched
`package-lock.json` rides along. Nothing runs until these are answered.

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
under the limit.
→ *Decided 2026-09-22:* no stack drops to `sec-1` to get past a limit. The
measurements go into the review below.

**Traefik labels and middlewares are reviewed as a whole before v1.0.0** — see
[`../ROADMAP.md`](../ROADMAP.md). They grew stack by stack; 89 stacks route
through Traefik, 84 of them take their chain from `.env`. After v1.0.0 a renamed
middleware disables the router of every deployment that names it. Open, besides
the two points above:

- **Names.** Twelve chains put headers, framing and rate limit into one name.
  38 stacks default to `sec-2` and 35 to `sec-3`; `sec-0` and `sec-1e` are used
  by none. `e` reads as "embeddable" and permits only the application's own
  origin. `spa` names a kind of application rather than what the chain changes, a
  burst of 200 — the chain file calls the `-spa` chains VPN-only, the block they
  use is described as fit for public applications. `sec-authentik` carries the
  chains' prefix but is an authentication gate, and the label pattern has no slot
  for it.
- **Fit per application**, Nextcloud for one: what an application needs to start
  without errors and stay responsive under a working day's load, and whether
  presets or per-application settings answer that. Every rate-limit figure above
  is a first page load; no stack has a measurement under sustained use.
- **CrowdSec.** 45 of those 84 stacks have no `APP_TRAEFIK_THREAT` slot, so a
  bouncer middleware cannot be attached from `.env`. The profile ladder is in
  [`../core/crowdsec/docs/profiles.md`](../core/crowdsec/docs/profiles.md).
- **Authentik.** Forward auth exists only as a commented-out block in
  `core/traefik/ops/templates/dynamic/integrations.yml.tmpl`.
- **Client address.** The rate limits and access policies do not say which
  address counts, and Traefik's documentation says both then use the connecting
  address: an office behind one NAT address shares one bucket, traffic through
  Cloudflare counts per edge address. The comment in `traefik.yml.tmpl` says
  trusting Cloudflare's forwarded headers gives `ipAllowList` the real client.
  Not measured.

→ The review may change names and structure, or confirm them.

## Active constraints

- **A host to experiment on, not a host at all.** The blueprint's stacks run in
  production; what the open milestones need is a machine that may be broken,
  filled with throwaway data and restored into. That is the single precondition
  behind v0.8.0 and v0.10.0, and it is what v0.7.0 needed before it could close.
- **Real values never enter the repository.** On the host, `.env` carries the real
  domain and real secrets and is gitignored. Committed files use `example.com`
  and documentation IP ranges only. This matters more during a host session than
  at any other time, because that is when real values are at hand.
- Nine major version bumps are pinned but never started, and the stacks still
  carrying the pre-v0.5.1 `Last checked:` field are marked ⚠️ in `LIFECYCLE.md`.
  Both ride along with the host session.
- Public repository: no real domains, IPs, hostnames or personal data; no session
  context or personal attribution in committed content. `.ai/` is committed and
  therefore public — it holds working context, never internal process detail.
  This is the rule, not a description of the tree. `site/` is the named exception
  and still carries the domain, the legal notice and a contact address; the
  direction that removes them is in [`../ROADMAP.md`](../ROADMAP.md), and the
  inventory there is not yet complete.
