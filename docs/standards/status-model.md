# Status Model

Two people ask different questions about the same stack:

- **An operator deciding whether to deploy it** asks: *can I rely on this?*
- **A maintainer deciding what to work on** asks: *what have we actually established?*

One checkmark cannot answer both. Before this standard the repository tried anyway, and the result was predictable: the root README, the category READMEs, and `LIFECYCLE.md` each carried their own status, none derived from another, and they drifted apart — twelve services claimed ✅ in one file and 🚧 in the file that owned the claim.

This standard defines the two axes, how they map onto each other, and which file owns which fact.

---

## Axis 1 — Public status

*What an operator can rely on.* This is what the README tables show, as a symbol.

| Symbol | Status | What it promises |
|---|---|---|
| 📋 | `planned` | Named as intended. Nothing on disk yet. |
| 🚧 | `preview` | On disk, and it may well work — but the blueprint does not vouch for it. Evaluate it yourself before trusting it with data. |
| ✅ | `ready` | Clean install and core function established, security baseline met, documentation in place. Deploy it. |
| 🛡️ | `ops-ready` | `ready`, plus a restore has actually been performed from a backup — not merely documented. |

`ops-ready` is defined here but **no stack holds it yet**: the blueprint has no restore evidence for any service. It becomes reachable with the v0.7.0 backup milestone.

The symbol is nevertheless listed in every status legend from the start, and the legends say plainly that nothing holds it. A vocabulary that only appears once something earns it hides the bar it sets — showing the empty tier is itself the statement that a restore has not been performed.

## Axis 2 — Internal status

*What the maintainer has established.* This lives in [`LIFECYCLE.md`](../../LIFECYCLE.md), never in the README tables.

| Status | Meaning |
|---|---|
| `scaffolded` | The structure exists. Nothing beyond that is claimed. |
| `verified` | Clean install and core function established on a real host. |
| `baseline-aligned` | `verified`, plus the security baseline is met — or every deviation is documented. |
| `ops-proven` | `baseline-aligned`, plus restore evidence. |

## How the two map

| Internal | Public | Symbol |
|---|---|---|
| *(nothing on disk)* | `planned` | 📋 |
| `scaffolded` | `preview` | 🚧 |
| `verified` | `preview` | 🚧 |
| `baseline-aligned` | `ready` | ✅ |
| `ops-proven` | `ops-ready` | 🛡️ |

Note that `verified` still maps to 🚧. Running correctly is not the same as being safe to hand to someone else — the security baseline is part of what ✅ promises, so a stack that boots and works but has not been checked against the baseline is still a preview.

## The gate between 🚧 and ✅

The [✅ Ready Criteria](../maintenance.md#-ready-criteria) are that gate. They were already the internal definition; this standard names them as such and maps them onto the axis:

| Criteria | Establishes |
|---|---|
| 5–7 — clean install, core function, Traefik routing | `verified` |
| 1–4 — pinned tag, healthcheck, security baseline, no hardcoded values | the baseline half of `baseline-aligned` |
| 8–10 — `UPSTREAM.md` with `Last verified`, license, complete `.env.example` | the documentation half |

**All ten together are exactly `baseline-aligned`, which is exactly public `ready`, which is exactly ✅.** One gate, three names for the same bar, no independent judgement anywhere.

---

## Who owns which fact

Every fact below has exactly one owner. Everything else derives from it. When two files disagree, the owner wins — and the derived file was generated from stale input, which is a bug in the generator or a missed run, not a judgement call.

| Fact | Owner | Derived into |
|---|---|---|
| Public status symbol — `business/`, `monitoring/`, `backup/` | that category's `README.md` | root `README.md`, `LIFECYCLE.md` |
| Public status symbol — `core/`, `apps/` | root `README.md` | `LIFECYCLE.md` |
| Pinned image version | `<stack>/.env.example` | `LIFECYCLE.md` |
| Last verified date + version | `<stack>/UPSTREAM.md` | `LIFECYCLE.md` |
| Security baseline alignment | `<stack>/docker-compose.yml`, checked by `scripts/ci/check-baseline.py` and `check-structure.py` | `LIFECYCLE.md` |
| Restore evidence | `docs/maintenance.md` Progress Log | `LIFECYCLE.md` |

`core/` and `apps/` have no category README — those two categories are documented per service in the root README tables instead. That is a deliberate exception, not an oversight, and it is why the root README owns their status.

## LIFECYCLE.md is generated

`LIFECYCLE.md` is produced by `scripts/ci/lifecycle-report.py` and **must not be edited by hand**. Every column is read from the owner listed above.

This is the point of the whole standard. The previous hand-maintained version covered 6 of 54 stacks and its version data was three months stale, because keeping a parallel table current by hand is work nobody does twice. A generated file cannot drift: either it is regenerated and correct, or CI fails because it is out of date.

Regenerate after any change to a status, a pin, or an `UPSTREAM.md`:

```bash
python3 scripts/ci/lifecycle-report.py --write
```

## What CI enforces

`scripts/ci/lifecycle-report.py --check` fails when:

- a stack's status disagrees between its owner and the root README mirror
- `LIFECYCLE.md` is out of date with respect to its sources
- a stack claims ✅ while missing `Last verified:` in `UPSTREAM.md` (criterion 8 unmet)

The third rule is the one that would have caught the twelve mismatched services at the commit that introduced them, rather than months later by hand.

---

## Related

- [`../maintenance.md`](../maintenance.md) — the ✅ Ready Criteria themselves, and the chains that apply them
- [`../../LIFECYCLE.md`](../../LIFECYCLE.md) — the generated per-stack view
- [`security-baseline.md`](security-baseline.md) — what "baseline met" means concretely
- [`documentation-workflow.md`](documentation-workflow.md) — when each document must be updated
