# Maintenance Process

Navigation document for keeping the repository accurate, consistent, and up to standard. Rules and standards are defined elsewhere — this file maps **triggers to chains**, **chains to affected files**, and tracks **where the process currently stands**.

---

## File Map — Single Source of Truth

Each piece of information has exactly one owner. When two files disagree, the owner wins and the mirror is corrected.

| Information | Owner | Mirrors / references it |
|---|---|---|
| App status (✅ / ⚠️ / 📋) | Category README | Root README tables |
| App location (category) | Directory structure | README tables |
| Shipped work | `CHANGELOG.md` | — |
| Direction / planned work | `ROADMAP.md` | Category READMEs reference, do not duplicate |
| Compose standards | `docs/standards/compose-structure.md` | Every `docker-compose.yml` |
| Env standards | `docs/standards/env-structure.md` | Every `.env.example` |
| Security rules | `docs/standards/security-baseline.md` | Every service in every compose |
| Naming conventions | `docs/standards/naming-conventions.md` | Every compose, env, container name |
| Architecture decisions | `docs/architecture.md` | Category READMEs may summarise |
| Per-app setup | `<app>/README.md` | Root README one-liner only |
| Per-app config options | `<app>/CONFIG.md` (where it exists) | No duplication |
| Per-app upstream info | `<app>/UPSTREAM.md` | — |

**Root README structure rule**: tables show `⚠️` / `✅` only. `📋` planned items appear as inline `Planned: X, Y, Z` lines — never as table rows.

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
| 3 | `docs/maintenance.md` | Add a row to the Progress Log. |

---

### App Chain
**Trigger**: new app added, existing app re-verified, or significantly changed.

| Step | File | Action |
|---|---|---|
| 1 | `<app>/docker-compose.yml` | Follows compose structure → `docs/standards/compose-structure.md` |
| 2 | `<app>/.env.example` | Follows env structure → `docs/standards/env-structure.md` |
| 3 | `<app>/docker-compose.yml` | Passes security baseline → `docs/standards/security-baseline.md` |
| 4 | `<app>/README.md` | Setup + verify steps accurate and tested |
| 5 | `<app>/UPSTREAM.md` | Image source, license, changelog link current |
| 6 | `<app>/.gitignore` | Covers `volumes/`, `.secrets/`, `.env` |
| 7 | Category README | Status correct: `⚠️` = files exist, `✅` = clean-install tested, `📋` = no files |
| 8 | Root `README.md` | Table row matches category README (status, description) |
| 9 | `CHANGELOG.md` | Change documented |

---

### Version Chain
**Trigger**: upstream image has a new release, or a security advisory appears.

| Step | File | Action |
|---|---|---|
| 1 | `<app>/.env.example` | Bump image tag — test on clean install first, then commit |
| 2 | `<app>/UPSTREAM.md` | Update version reference and release notes link |
| 3 | `<app>/docker-compose.yml` | Check if any compose changes are needed (new envs, removed features, healthcheck changes) |
| 4 | `docs/bugfixes/` | If anything broke during upgrade, document it here |
| 5 | `CHANGELOG.md` | Version bump documented |

---

### Standards Chain
**Trigger**: a standard in `docs/standards/` is updated or a new standard is added.

| Step | File | Action |
|---|---|---|
| 1 | `docs/standards/<changed-file>` | Update the standard itself |
| 2 | All Ready apps (`✅`) | Check compliance with the updated standard |
| 3 | All Draft apps (`⚠️`) | Note any drift — fix before next verification pass |
| 4 | `CHANGELOG.md` | Standard change documented |
| 5 | `docs/maintenance.md` | Progress Log: which apps were checked, which have open drift |

---

### Consistency Chain
**Trigger**: before a release, or when the repo has grown significantly.

| Step | File | Action |
|---|---|---|
| 1 | All category READMEs | Every directory has a row; every `⚠️` entry has files on disk |
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
| 2 | `ROADMAP.md` | Move shipped milestone to Shipped section |
| 3 | All `⚠️` entries | Is the draft status still honest? |
| 4 | All `✅` entries | Were any broken by dependency updates since last test? |
| 5 | GitHub | `gh release create vX.Y.Z --draft` |

---

## Progress Log

One row per session or chain run. The next session starts here — not at the top of the repo.

| Date | Chain | Scope | What was done | Open / carry-forward |
|---|---|---|---|---|
| 2026-04-28 | Setup | Entire repo | Process document created. File map defined. Chains defined. | — |
| 2026-04-28 | Consistency | Entire repo | First live run. Fixed: SMTP hostnames in 3 `.env.example` files, broken Ackee link, root README pattern (tables = ⚠️/✅ only, Planned = inline). Rules refined: `__REPLACE_ME__` scan scoped to compose+scripts, vendor hostname scan added. | Category READMEs need content depth pass (choice guidance, integration notes) to differentiate from root README. |
| 2026-04-29 | Setup | Process redesign | Rebuilt `maintenance.md` as a process map with trigger-based chains. Removed duplicate rules — chains reference standards, do not repeat them. | First real chain run pending. |
| 2026-05-01 | App Chain | `core/authentik` | Fixed: `init-perms` missing `no-new-privileges:true`; `UPSTREAM.md` still on 2024.12.3 → bumped to 2026.2.2. Found two violations in `docs/standards/env-structure.md` itself: SMTP example used real vendor hostname, TZ default was Europe/Vienna instead of UTC — both fixed. | Open: `cap_drop` missing on all services (Recommended); `deploy.resources` + `pids_limit` not set (v1.0 Polish, needs measuring). |
