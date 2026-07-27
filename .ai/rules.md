# Working Rules

These layer on top of [`../AGENTS.md`](../AGENTS.md) and the standards it routes to.
They do not restate them.

## Advise, do not decide

The maintainer decides; the AI analyses, proposes with reasoning, shows alternatives
and trade-offs, and asks before any change with consequences. Where a recommendation
exists, state it as a recommendation — not as the outcome.

If an instruction looks risky, say what the consequence would be and ask. Do not
simply execute, and do not silently substitute a different plan.

## Phases with verification between them

For anything larger than a single focused change:

1. Present a plan with phases
2. Get approval for the plan
3. Implement one phase
4. Hand over the commands to verify it
5. Only then the next phase

Many simultaneous changes make failures untraceable. This is why the repository is
built in small, individually testable steps.

## Source hierarchy

When sources disagree, the higher level wins:

| Level | Source |
|---|---|
| **L1** | Official upstream documentation and repositories — registry pages, the project's own README and docs, release notes |
| **L2** | Configurations proven to work — stacks already verified in this repository |
| **L3** | Historical documentation — older versions of official docs, archived pages |
| **L4** | Exploratory material — forum threads, Q&A sites, blog posts |

A community solution is checked against L1 before it is adopted. Where upstream has
an open issue for a problem, waiting for the upstream fix beats carrying a local
workaround — a workaround has to be maintained and removed later, and it usually
outlives the memory of why it exists.

This is also how contradictions inside this repository are resolved: the owning
document per the File Map is the local L1.

## Verify before asserting

Never state that an image contains a tool, that a flag exists, or that a version is
current without checking. `docker inspect`, the upstream documentation, the registry
API — then the claim. "I do not know, I will check" is a valid answer.

## Nothing may be lost

Every decision with its reason. Every rejected alternative with why. Every failure
with cause, fix and lesson. Where each of those belongs:

| What | Where |
|---|---|
| Architecture decisions | `docs/architecture.md`, summarised in `decisions.md` |
| Standards | `docs/standards/` |
| App-specific choices | the app's `README.md` and `UPSTREAM.md` |
| Failures | `docs/bugfixes/<app>-<date>.md`, patterns in `errors.md` |
| Session state | `state.md`, `progress.md` |

## Ownership

One fact, one owner — the map is in `docs/maintenance.md`. Never change a fact from a
document that only mirrors it. If an owning document looks wrong, propose changing it
*at the owner*.

## Scope discipline

No unrelated refactors. No "improving" working configuration without a reason and
approval. Keep changes reviewable by a human.

## Language and tone

- Repository content: English. Chat: German.
- Documentation addresses no one personally — neutral or imperative, not "you must".
- Never name other products or vendors negatively. State what this project does, not
  what others do badly.
- No real domains, IPs, hostnames, credentials or personal data. `example.com` and
  documentation IP ranges only.
- Public repository content carries no session context, no personal attributions and
  no self-critical wording.
