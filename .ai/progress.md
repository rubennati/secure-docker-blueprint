# Progress

Milestone-level history. Per-release detail is in [`../CHANGELOG.md`](../CHANGELOG.md);
session-level detail is in the Progress Log of
[`../docs/maintenance.md`](../docs/maintenance.md).

| Release | Date | What it established |
|---|---|---|
| v0.1.0 | 2026-04-16 | Initial public release — core infrastructure plus ten hardened apps, standards, Apache 2.0 |
| v0.2.0 | 2026-04-18 | Structure Stable Baseline — five top-level categories forks can rely on |
| v0.3.0 | 2026-04-20 | Core complete — every core service validated on a fresh install; both multi-host management paths proven |
| v0.4.0 | 2026-04-20 | CrowdSec bouncer enforcing at the proxy, proven end-to-end |
| v0.5.0 | 2026-05-03 | Authentik Forward-Auth, two reusable patterns proven end-to-end |
| v0.5.1 | 2026-05-03 | Network isolation fix, tag pinning standard, ✅ Ready Criteria formalised |
| v0.6.0 | 2026-06-04 | CrowdSec complete — firewall bouncer, runbook, AppSec and geoblocking guidance |
| v0.7.0 | in progress | Backup — designed and configured; closes with one performed restore |

**The through line:** every release since v0.2.0 is defined by something *proven on a
fresh install*, not by something written. That is why status carries verification
dates, why ✅ has ten criteria, and why v0.7.0 does not end with a working
configuration.

## Since v0.6.0, outside the plan

Recorded in `ROADMAP.md` under "Since v0.6.0 — work outside the plan": a repo-wide
dependency sweep, the reference app and structure checker, four new previews, the
Cal.diY fork and hardening track, supply-chain hardening, and the unified status
model with a generated lifecycle view. None of it changed the milestone order.
