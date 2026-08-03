# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-07-31

- **Phase:** pre-1.0. Latest tag `v0.7.0` (2026-07-31). Work happens on `dev`.
- **Current milestone:** v0.8.0 — Monitoring.
- **Definition of done for v0.8.0:** one verified service per axis, and at least
  one alert that arrived on a real device. Not a green dashboard.

## Snapshot

- Stack inventory, per-stack status, pinned version and verification date:
  [`../LIFECYCLE.md`](../LIFECYCLE.md). Read it for any current figure — it is
  generated from the owners in `docs/standards/status-model.md`, and no count is
  repeated in this file. After a status change or a pin, regenerate with
  `python3 scripts/ci/lifecycle-report.py --write`.
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
- CI jobs and what each one blocks on: [`quality-gates.md`](quality-gates.md),
  documented per job in `docs/standards/ci.md`. `Checker coverage`, `Docs QA` and
  `Workflow supply chain` run without blocking until branch protection is updated.

## Immediate next steps

The disposable host carried v0.7.0. What runs on it next, in this order:

1. **v0.8.0** — [`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md).
   Ordered by dependency: the receiver first, then the closed-circuit monitor,
   then the observing ones.
2. **What v0.7.0's session left open** —
   [`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md) Blocks 3
   and 4: UrBackup has never been started, and nine major versions are pinned
   and never run. Neither gated the tag; both still need the host.
3. **Feeding v0.9.0** — start the sampler in
   [`../docs/resource-measurement.md`](../docs/resource-measurement.md) before the
   first stack comes up. Every container started is a measurement opportunity,
   and v0.9.0 cannot be prepared any other way.

Backup's proof layer depends on monitoring: borgmatic's run monitoring points at
`monitoring/healthchecks` and `monitoring/uptime-kuma`. Bring those up before
switching borgmatic's timer on.

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

**7. CPU limits — two standards disagree**
`docs/standards/security-baseline.md` prescribes a `cpus` value per service
profile. `docs/standards/compose-structure.md` states that CPU limits are not
applied by default, because they make a stack slow under load rather than safe,
and that one is set only where a component demonstrably pins a core. The compose
files follow the second. Most services therefore carry no `cpus` value — a
measurement, not the decision. One of the two standards has to yield; the
structure checker enforces neither.

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
