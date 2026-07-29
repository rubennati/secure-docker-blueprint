# Routing Guide

Read the minimum a task needs. Do not preload unrelated documents.

Every entry below is **in addition to** `state.md`, which is always read first.

| Task type | Read |
|---|---|
| **Adding or changing an app** | `domains/coding.md` · `docs/standards/new-app-checklist.md` · `compose-structure.md` · `env-structure.md` · `security-baseline.md` · the app's own README + UPSTREAM |
| **Version bump** | `docs/maintenance.md` Version Chain · the app's `UPSTREAM.md` · upstream release notes |
| **Traefik, routing, middleware, TLS** | `docs/standards/traefik-security.md` · `traefik-labels.md` · `networking.md` |
| **Security hardening** | `docs/standards/security-baseline.md` · `docs/security-verification.md` · `SECURITY.md` |
| **Documentation change** | `domains/documentation.md` · `docs/standards/documentation-workflow.md` · `docs/maintenance.md` File Map |
| **Status or lifecycle** | `docs/standards/status-model.md` · `docs/maintenance.md` ✅ Ready Criteria |
| **Architecture question** | `domains/architecture.md` · `docs/architecture.md` · `decisions.md` |
| **Release** | `domains/release.md` · `docs/maintenance.md` Release Chain · `ROADMAP.md` |
| **Commit, branch, push** | `docs/standards/commit-rules.md` — binding, read before every commit |
| **Verification and CI** | `quality-gates.md` · `docs/standards/ci.md` |
| **Continuation after interruption** | `state.md` · `progress.md` · `tasks.md` · `decisions.md` |
| **Troubleshooting** | `errors.md` · `docs/standards/troubleshooting.md` · `TROUBLESHOOTING.md` · `docs/bugfixes/` |

## Before proposing anything about an area

Read that area's own README and its `ROADMAP.md` section first, and state what they
say. An opinion comes after, and only with reasoning where it differs. Most questions
are already answered somewhere in this repository.
