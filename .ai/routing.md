# Routing Guide

Read the minimum a task needs. Do not preload unrelated documents.

Every entry below is **in addition to** `state.md`, which is always read first.

| Task type | Read |
|---|---|
| **Adding or changing an app** | `domains/coding.md` · `docs/standards/new-app-checklist.md` · `compose-structure.md` · `env-structure.md` · `security-baseline.md` · the app's own README + UPSTREAM |
| **Version bump** | `docs/maintenance.md` Version Chain · the app's `UPSTREAM.md` · upstream release notes |
| **Traefik, routing, middleware, TLS** | `docs/standards/traefik-security.md` · `traefik-labels.md` · `networking.md` |
| **Security hardening** | `docs/standards/security-baseline.md` · `docs/security-verification.md` · `SECURITY.md` |
| **Documentation change** | `domains/documentation.md` · `docs/standards/documentation-workflow.md` · `docs/standards/writing-style.md` · `docs/maintenance.md` File Map — roles below |
| **Status or lifecycle** | `docs/standards/status-model.md` · `docs/maintenance.md` ✅ Ready Criteria |
| **Architecture question** | `domains/architecture.md` · `docs/architecture.md` · `decisions.md` |
| **Release** | `domains/release.md` · `docs/maintenance.md` Release Chain · `ROADMAP.md` |
| **Commit, branch, push** | `docs/standards/commit-rules.md` — binding, read before every commit |
| **Verification and CI** | `quality-gates.md` · `docs/standards/ci.md` |
| **Continuation after interruption** | `state.md` · `progress.md` · `tasks.md` · `decisions.md` |
| **Troubleshooting** | `errors.md` · `docs/standards/troubleshooting.md` · `TROUBLESHOOTING.md` · `docs/bugfixes/` |

## Documentation route

| Source | Answers |
|---|---|
| [`domains/documentation.md`](domains/documentation.md) | the operative summary for the session — owns nothing |
| [`../docs/standards/documentation-workflow.md`](../docs/standards/documentation-workflow.md) | document and section purpose, section contracts, the relevance test, ownership modes, when a document must be updated |
| [`../docs/standards/writing-style.md`](../docs/standards/writing-style.md) | register and wording — the seven forms, address and mood, one reader per file |
| [`../docs/maintenance.md`](../docs/maintenance.md) | File Map: which source is the canonical owner of a changing fact, and who keeps each file current |

Read only the sections the task needs; the preflight in `documentation-workflow.md`
names them. Where the summary and a canonical standard disagree, the standard and
the File Map win.

## Before proposing anything about an area

Read that area's own README and its `ROADMAP.md` section first, and state what they
say. An opinion comes after, and only with reasoning where it differs. Most questions
are already answered somewhere in this repository.
