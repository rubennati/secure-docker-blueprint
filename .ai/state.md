# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-09-08

- **Phase:** pre-1.0. Latest tag `v0.8.0` (2026-09-08). Work happens on a
  short-lived branch and reaches `dev` through a pull request; `dev` reaches
  `main` the same way. Both branches reject a direct push.
- **Current milestone:** v0.9.0 — Measured resource limits.
- **Definition of done for v0.9.0:** every `✅` stack's limits come from a
  measurement on a real install rather than from the derivation rule
  (`docs/resource-measurement.md`).

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
  reports images it could not pull instead of passing over them. Still
  `--exit-code 0`.
- CI jobs and what each one blocks on: [`quality-gates.md`](quality-gates.md),
  documented per job in `docs/standards/ci.md`. All ten are required on a pull
  request into `dev` and into `main`, and both rulesets require the branch to be
  up to date before merging. CodeQL reports on the same pull requests and is not
  a required check.

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
3. **Feeding v0.9.0** — start the sampler in
   [`../docs/resource-measurement.md`](../docs/resource-measurement.md). Every
   container started is a measurement opportunity, and v0.9.0 cannot be
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

**6. What belongs in `core/`**
The test in `docs/architecture.md:34` asks whether the stack breaks the
deployment, controls Docker, or provides shared identity, certificates, DNS or
WAF. `core/onlyoffice`, `core/euro-office` and `core/collabora` are document
servers — nothing breaks without them, so they fail that test.
→ *Recommendation:* apply the existing test rather than write a new rule. This is
a structural change, so it belongs after the host session, not before.

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

## Active constraints

- **A host to experiment on, not a host at all.** The blueprint's stacks run in
  production; what the open milestones need is a machine that may be broken,
  filled with throwaway data and restored into. That is the single precondition
  behind v0.8.0 and v0.9.0, and it is what v0.7.0 needed before it could close.
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
