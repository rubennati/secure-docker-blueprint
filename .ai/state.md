# Current State

> If this file conflicts with git (branch, commits, tags), trust git.

**Last updated:** 2026-07-28

- **Phase:** pre-1.0. Latest tag `v0.6.0` (2026-06-04). Work happens on `dev`.
- **Current milestone:** v0.7.0 — Backup.
- **Definition of done for v0.7.0:** one restore performed and written down. Not
  when the configuration validates, not when the timer runs, not when an archive
  exists.

## Snapshot

- 59 stacks tracked. 39 `ready`, 20 `preview`, **0 `ops-ready`** — no stack has
  restore evidence, which is exactly what v0.7.0 changes. Numbers come from
  `LIFECYCLE.md`; regenerate rather than editing them here.
- Backup architecture designed (`backup/README.md`): five layers, host-installed
  agent, snapshot/backup/archive kept distinct.
- `backup/borgmatic/` — configuration, systemd timer, setup and restore playbook.
  Host-installed, no Compose stack. Never exercised on a host.
- `backup/urbackup/` — client and endpoint backup, bridge networking with the web
  interface behind Traefik, host-networking overlay opt-in. Never started.
- Status model unified (`docs/standards/status-model.md`); `LIFECYCLE.md` generated
  by `scripts/ci/lifecycle-report.py`; both structure and status enforced in CI.
- CI: 10 jobs, all green. Seven are required on `main`; `Checker coverage`,
  `Docs QA` and `Workflow supply chain` run without blocking until branch
  protection is updated.

## Immediate next steps

A disposable host is being prepared. Both remaining milestones run on it, in
this order:

1. **v0.7.0** — [`../docs/host-session-v0.7.0.md`](../docs/host-session-v0.7.0.md).
   Blocks 1 and 2 (first backup, restore rehearsal) are the milestone; the rest
   shares the precondition but does not gate the tag.
2. **v0.8.0** — [`../docs/host-session-v0.8.0.md`](../docs/host-session-v0.8.0.md).
   Ordered by dependency: the receiver first, then the closed-circuit monitor,
   then the observing ones.
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

**2. Two troubleshooting documents** — 5 minutes
`TROUBLESHOOTING.md` (root, 400+ lines) and `docs/standards/troubleshooting.md`
(470 lines) both open with symptom catalogues and overlap substantially.
→ *Recommendation:* root file becomes the operator-facing index of common
failures; the standards file keeps the systematic inside-out debugging method.
Whichever way, one of the two must stop being a catalogue.

**3. Backup repository isolation** — 5 minutes
`docs/architecture.md:132` states one repository per app as a rule.
`backup/README.md:176` presents it as a trade-off. The File Map makes
`architecture.md` the owner, so the two disagree and the mirror is winning.
→ *Recommendation:* change it at the owner. The trade-off in `backup/README.md`
is the more honest text — separate repositories multiply the rehearsals, and a
rehearsal nobody runs is worse than a shared repository that has been restored
from.

**4. Host-installed backup agent vs. the portability goal**
`docs/architecture.md` promises "no host-specific assumptions beyond Debian +
Docker". `backup/borgmatic` is installed on the host by design, with the
reasoning in `backup/README.md`.
→ *Recommendation:* record it in `architecture.md` as a named exception with its
reason. The reasoning is sound; only the contradiction is unrecorded.

**5. Neutral language scope**
The "documentation addresses no one personally" rule is clear for German drafts.
Whether it governs the English documentation has never been stated, and the
English text is inconsistent as a result.
→ *Recommendation:* apply it to both. It is already the majority style.

**6. Commit procedure**
`docs/standards/commit-rules.md` requires asking before every commit; an external
standard would allow an agent to commit to non-`main` branches unprompted.
→ *Recommendation:* keep the local rule. It has caught real mistakes, and the
cost is one question per commit.

**7. Dependency automation** — see
[`../docs/renovate-proposal.md`](../docs/renovate-proposal.md)
Three sub-questions: explicit `# renovate:` markers vs. normalising 28 outlying
comments · Renovate App vs. self-hosted Action · whether `site/`'s unwatched
`package-lock.json` rides along. Nothing runs until these are answered.

**8. What belongs in `core/`**
The test in `docs/architecture.md:34` asks whether the stack breaks the
deployment, controls Docker, or provides shared identity, certificates, DNS or
WAF. `core/onlyoffice`, `core/euro-office` and `core/collabora` are document
servers — nothing breaks without them, so they fail that test.
→ *Recommendation:* apply the existing test rather than write a new rule. This is
a structural change, so it belongs after the host session, not before.

## Active constraints

- **A host to experiment on, not a host at all.** The blueprint's stacks run in
  production; what the open milestones need is a machine that may be broken,
  filled with throwaway data and restored into. That is the single precondition
  behind v0.7.0, v0.8.0 and v0.9.0 — three milestones, one blocker.
- **Real values never enter the repository.** On the host, `.env` carries the real
  domain and real secrets and is gitignored. Committed files use `example.com`
  and documentation IP ranges only. This matters more during a host session than
  at any other time, because that is when real values are at hand.
- Nine major version bumps are pinned but never started; 22 stacks still carry the
  pre-v0.5.1 `Last checked:` field. Both ride along with the host session.
- Public repository: no real domains, IPs, hostnames or personal data; no session
  context or personal attribution in committed content. `.ai/` is committed and
  therefore public — it holds working context, never internal process detail.
