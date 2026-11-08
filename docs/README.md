# Documentation

Two kinds of document live here. **Reference** says how the blueprint works and what
holds today; keep it open while you deploy or change something. **Records** say what
was measured, reviewed, proposed or fixed at a given time; they are evidence and
history, and a later change does not rewrite them.

## Reference

| Document | What it covers |
|---|---|
| [`architecture.md`](architecture.md) | The networking model, the categories, the application contract and the boundaries between components |
| [`standards/`](standards/) | The rules every stack is checked against — Compose, env, secrets, networking, Traefik, restore, the deployment lifecycle |
| [`host-baseline.md`](host-baseline.md) | The Docker host the blueprint assumes, by role, with what was tested |
| [`security-coverage.md`](security-coverage.md) | Security controls counted from the compose files (generated) |
| [`sovereignty/`](sovereignty/) | Data egress, the edge in front of a server, and licence and jurisdiction per product |
| [`resource-measurement.md`](resource-measurement.md) | How to measure the resource limits on a running host |
| [`maintenance.md`](maintenance.md) | The maintainer's chains: adding a stack, updating a pin, consistency, releases |

## Records

| Record | What it holds |
|---|---|
| [`maintenance-log.md`](maintenance-log.md) | One line per release and maintenance session |
| [`audits/`](audits/) | Audits with their findings registers and evidence |
| [`labs/`](labs/) | Results of lab runs |
| [`reviews/`](reviews/) | Design reviews |
| [`bugfixes/`](bugfixes/) | Root-cause notes per fix, dated |
| [`research/`](research/) | Concepts and decision papers, not implemented unless the CHANGELOG says so |
| [`host-verification-ingress.md`](host-verification-ingress.md) | The host verification plan and results of the ingress programme |
| [`host-verification-phase-2.md`](host-verification-phase-2.md) | The host checks of the core audit's Phase 2, with [`../scripts/verify-phase-2.sh`](../scripts/verify-phase-2.sh), which runs the read-only ones |
| [`host-session-plan.md`](host-session-plan.md), [`host-session-findings.md`](host-session-findings.md), [`host-session-priority-1.md`](host-session-priority-1.md), [`host-session-v0.7.0.md`](host-session-v0.7.0.md), [`host-session-v0.8.0.md`](host-session-v0.8.0.md) | Host sessions: plans, backlogs and what they found |
| [`v1-readiness-audit.md`](v1-readiness-audit.md) | The stabilization audit's findings register |
| [`security-verification.md`](security-verification.md) | An earlier security assessment, kept for history |
| [`ci-trigger-proposal.md`](ci-trigger-proposal.md), [`renovate-proposal.md`](renovate-proposal.md) | Proposals — when checks run, automated dependency updates |
| [`site-review-2026-08-03.md`](site-review-2026-08-03.md) | A review of the operator site |

Decisions and their reasons are in [`../.ai/decisions.md`](../.ai/decisions.md); what
changed in each release is in [`../CHANGELOG.md`](../CHANGELOG.md).
