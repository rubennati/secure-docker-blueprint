# Maintenance Process

This document operates one level above the repository content. It defines **how the project maintains quality over time** — not what the standards are (those live in `docs/standards/`), but when and how they are applied, verified, and kept current.

The repository has three kinds of truth:

- **Standards** — what correct looks like (`docs/standards/`)
- **State** — what exists right now (files, READMEs, CHANGELOG)
- **Process** — how state is kept aligned with standards (this document)

During active development it is easy to add an app, update a standard, or bump a version without updating everything that depends on it. These gaps accumulate silently. The chains below make the dependencies explicit: when X changes, these are the files that need to be checked.

No chain needs to be run in full every time. Run only what the trigger requires.

---

## File Map — Single Source of Truth

Each changing fact has exactly one **canonical owner** — the source that defines it. When two files disagree, the canonical owner wins and the mirror is corrected. Which role keeps a file current is a separate question, answered under [Maintenance responsibility](#maintenance-responsibility).

Four models describe documentation in this repository, each answering one question. This File Map answers **which source owns a changing fact**. [`standards/documentation-workflow.md`](standards/documentation-workflow.md) answers **what a document or section is for, and when it has to be updated**. [`standards/writing-style.md`](standards/writing-style.md) answers **how the content is written** once it belongs. [`../.ai/domains/documentation.md`](../.ai/domains/documentation.md) is a short operative summary of all three for a working session, and is never a canonical owner.

| Information | Canonical owner | Mirrors / references it |
|---|---|---|
| Status definitions (what ✅ / 🚧 / 📋 promise) | `docs/standards/status-model.md` | Root README legend, `LIFECYCLE.md` |
| App status — `business/`, `monitoring/`, `backup/` | Category README | Root README tables, `LIFECYCLE.md` |
| App status — `core/`, `apps/` | Root README tables | `LIFECYCLE.md` |
| Per-stack lifecycle detail | the sources listed in [`standards/status-model.md`](standards/status-model.md#who-owns-which-fact) — status, pin, `Last verified`, baseline | `LIFECYCLE.md`, *generated* by `scripts/ci/lifecycle-report.py`, never hand-edited |
| App location (category) | Directory structure | README tables |
| Shipped work | `CHANGELOG.md` | — |
| Direction / planned work | `ROADMAP.md` | Category READMEs reference, do not duplicate |
| Compose standards, and every rule that carries a value — resource limits and their derivation | `docs/standards/compose-structure.md` | Every `docker-compose.yml`; `security-baseline.md` references it |
| Env standards | `docs/standards/env-structure.md` | Every `.env.example` |
| Local test stack — shape, header, which stacks get one | `docs/standards/compose-structure.md` | Every `docker-compose.local.yml` and `.env.local.example`; `apps/_reference/` is the worked example |
| Security rules that are on or off — privileges, capabilities, secrets, socket access, network isolation | `docs/standards/security-baseline.md` | Every service in every compose |
| Naming conventions | `docs/standards/naming-conventions.md` | Every compose, env, container name |
| A symptom and its fix — a failure seen in this blueprint | `TROUBLESHOOTING.md` | Stack READMEs and `UPSTREAM.md` reference a numbered entry |
| The layer-by-layer debugging method and command reference | `docs/standards/troubleshooting.md` | — |
| Architecture decisions | `docs/architecture.md` | Category READMEs may summarise |
| Per-app setup | `<app>/README.md` | Root README one-liner only |
| Per-app config options | `<app>/CONFIG.md` (where it exists) | No duplication |
| Per-app upstream info | `<app>/UPSTREAM.md` | — |
| AI entry point and rule precedence | `AGENTS.md` | `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/00-project.mdc` — pointers only, never a rule of their own |
| Working context for AI sessions | `.ai/` | Mirrors the owners above in condensed form; `.ai/domains/*.md` restate `docs/standards/` and lose to them on any disagreement |

**Root README structure rule**: tables show `🛡️` / `✅` / `🚧` only. `📋` planned items appear as inline `Planned: X, Y, Z` lines — never as table rows. `🛡️` is listed in every status legend but appears in no table yet; the first stack earns it with the v0.7.0 restore.

`core/` and `apps/` deliberately have no category README — they are documented per service in the root README tables, which is why the root owns their status. Everything derived from these owners is regenerated, not retyped:

```bash
python3 scripts/ci/lifecycle-report.py --write
```

**Generated is a presentation mode, not a second owner.** `LIFECYCLE.md` holds no fact of its own: every column is read from the canonical source named above, the file is written only by `scripts/ci/lifecycle-report.py --write`, and it is never edited by hand. A wrong value in it is corrected at that source and the file regenerated — editing the generated file changes nothing that survives the next run.

---

## Maintenance responsibility

Who keeps a file current. This is a role, not ownership of the facts inside the file: a file may carry facts owned elsewhere, and the role below keeps the file — its content, its references and its mirrors — correct.

| Document | Maintenance responsibility | When to touch |
|---|---|---|
| `README.md` | Maintainer | Any user-visible change |
| `ROADMAP.md` | Maintainer | Planning, milestones |
| `SECURITY.md` | Maintainer | Policy updates |
| `docs/standards/*` | Maintainer | Standard evolution |
| `docs/bugfixes/*` | Whoever fixed the bug | At the event |
| App `README.md` | App contributor | When changing that app |
| App `UPSTREAM.md` | App contributor | At version bumps |

---

## Baseline-aligned criteria

A stack reaches `baseline-aligned` when all of the following hold. A stack that
misses any of them stays at the state below it until the gap is closed.

These ten points are what `baseline-aligned` means in practice. Points 1–4 and
part of 8–10 are enforced by `check-baseline.py` and `check-structure.py`;
points 5–7 are what the version-anchored `Last verified` date records. See
[`standards/status-model.md`](standards/status-model.md) for how each state is
measured.

**Technical**

1. Image tag pinned — no `latest`, no major-only tags (e.g. `8`, `v2`)
2. Healthcheck present and verified working
3. Security baseline met — `no-new-privileges`, network isolation, secrets via Docker Secrets or `_FILE` pattern
4. No hardcoded values — everything configurable via `.env`

**Tested**
5. Clean install on a fresh environment completed
6. Core function verified — the app is usable, not just "container running"
7. Traefik routing confirmed working (HTTPS, correct middleware)

**Documented**
8. `UPSTREAM.md` present — source, `Last verified: YYYY-MM-DD (vX.Y.Z)`, upgrade checklist
9. `UPSTREAM.md` includes license — name (e.g. MIT, Apache 2.0, AGPL-3.0) and a note if it deviates from standard self-hosting use (see license policy in `ROADMAP.md`)
10. `.env.example` complete — all required fields present, no real domains or credentials as defaults

> **Note on rising bar:** Apps verified in earlier versions of the blueprint may not
> meet all current criteria. When an app is re-verified, it is brought up to the
> current standard before ✅ is re-confirmed.

---

## Chains

A chain is a defined sequence of files to check and update for a specific trigger. Each chain is independent — run only what the trigger requires. Chains can be combined or run partially.

---

### Session Chain

**Trigger**: any work session, regardless of what was changed.

| Step | File | Action |
|---|---|---|
| 1 | `CHANGELOG.md` | Is `[Unreleased]` up to date with what was done? |
| 2 | `ROADMAP.md` | Did anything complete or become irrelevant? Update if yes. |
| 3 | `docs/maintenance-log.md` | Add a row. |
| 4 | `.ai/state.md` | Does phase, snapshot and the open-decision list still match reality? A decision resolved at its owner is struck here. |

---

### App Chain

**Trigger**: new app added, existing app re-verified, or significantly changed.

| Step | File | Action |
|---|---|---|
| 1 | `<app>/docker-compose.yml` | Follows compose structure → `docs/standards/compose-structure.md` |
| 2 | `<app>/.env.example` | Follows env structure → `docs/standards/env-structure.md` |
| 3 | `<app>/docker-compose.yml` | Passes security baseline → `docs/standards/security-baseline.md` |
| 4 | `<app>/README.md` | Setup + verify steps accurate and tested |
| 5 | `<app>/UPSTREAM.md` | Image source, license, changelog link current; `Last verified: YYYY-MM-DD (vX.Y.Z)` updated |
| 6 | `<app>/.gitignore` | Covers `volumes/`, `.secrets/`, `.env` |
| 7 | Category README | Status is current and honest → status definitions in root `README.md` |
| 8 | Root `README.md` | Table row matches category README (status, description) |
| 9 | `CHANGELOG.md` | Change documented |

---

### Version Chain

**Trigger**: upstream image has a new release, or a security advisory appears.

| Step | File | Action |
|---|---|---|
| 1 | Release notes | Read changelog — any breaking changes, removed features, required migrations? |
| 2 | Security advisories | Check the upstream GitHub repo for open CVEs or security advisories against the current and new version (`Security` tab → `Advisories`) |
| 3 | `<app>/.env.example` | Bump image tag — test on clean install first, then commit |
| 4 | `<app>/UPSTREAM.md` | Update version reference and release notes link |
| 5 | `<app>/docker-compose.yml` | Check if any compose changes are needed (new envs, removed features, healthcheck changes) |
| 6 | `docs/bugfixes/` | If anything broke during upgrade, document it here |
| 7 | `CHANGELOG.md` | Version bump documented |

---

### Standards Chain

**Trigger**: a standard in `docs/standards/` is updated or a new standard is added.

| Step | File | Action |
|---|---|---|
| 1 | `docs/standards/<changed-file>` | Update the standard itself |
| 2 | All Ready apps (`✅`) | Check compliance with the updated standard |
| 3 | All Preview apps (`🚧`) | Note any drift — fix before next verification pass |
| 4 | `CHANGELOG.md` | Standard change documented |
| 5 | `docs/maintenance-log.md` | which apps were checked, which have open drift |

---

### Consistency Chain

**Trigger**: before a release, or when the repo has grown significantly.

| Step | File | Action |
|---|---|---|
| 1 | All category READMEs | Every directory has a row; every `🚧` entry has files on disk |
| 2 | Root `README.md` | Tables mirror category READMEs; `Planned:` lines match category planned items |
| 3 | All `.env.example` | No real hostnames or vendor values as defaults — `example.com` or empty |
| 4 | All `docker-compose.yml` + scripts | `grep -r "__REPLACE_ME__"` returns nothing |
| 5 | `ROADMAP.md` | Direction items still reflect intent; shipped items removed from Direction |
| 6 | `docs/architecture.md` | Still accurate — new category? changed networking? |
| 7 | `CHANGELOG.md` + `ROADMAP.md` | Version comparison links correct |

---

### Release Chain

**Trigger**: before tagging a version (`vX.Y.Z`).

Run the full Consistency Chain first, then:

| Step | File | Action |
|---|---|---|
| 1 | `CHANGELOG.md` | Move `[Unreleased]` to `[X.Y.Z]` heading; update comparison links |
| 2 | `ROADMAP.md` | Move shipped milestone to Shipped section; update "Last updated" date |
| 3 | `README.md` | Bump version badge (`v0.X.Y-blue`) |
| 4 | All `🚧` entries | Is the preview status still honest? |
| 5 | All `✅` entries | Were any broken by dependency updates since last test? |
| 6 | GitHub | Minor versions only (`v0.X.0`): `gh release create vX.Y.0 --draft` — review, then publish. Patch tags (`vX.Y.Z`) are Git tags only — no GitHub Release needed. |

---

## Historical record

Dated maintenance history has its own files, so this document stays the reference
a maintainer needs while working rather than the archive of previous work:

| Record | Where |
|---|---|
| What each session established, in sequence | [`maintenance-log.md`](maintenance-log.md) |
| The 2026-07-26 repo-wide pin inventory | [`audits/dependency-sweep-2026-07-26.md`](audits/dependency-sweep-2026-07-26.md) |
| One incident — symptom, cause, fix | [`bugfixes/`](bugfixes/) |
| A dated inspection of a state | [`audits/`](audits/) |
