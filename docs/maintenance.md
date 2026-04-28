# Maintenance Process

This document defines how the blueprint stays accurate, consistent, and up to date over time. It answers three questions: **what** needs checking, **when** to check it, and **how to log** what was done so the next session starts from a known state — not from zero.

---

## Quick-Reference Checklists

Use these as the quick check. The detailed process below explains the reasoning.

### Every session
- [ ] `CHANGELOG.md` `[Unreleased]` updated with today's work
- [ ] `ROADMAP.md` reflects current direction (nothing completed or cancelled without an update)
- [ ] Every file touched follows the relevant standard
- [ ] One row added to the Maintenance Log at the bottom of this file

### Every app — run when adding or re-verifying
- [ ] Directory exists and contains at minimum `docker-compose.yml` + `.env.example` + `.gitignore` + `README.md`
- [ ] Status tag is honest: `⚠️ draft` = files exist, `📋 planned` = no files yet, `✅` = clean-install tested
- [ ] Status in category README = status in root README (no drift)
- [ ] Compose follows block order (Identity / Security / Configuration / Storage / Networking / Traefik / Health)
- [ ] No `:latest` image tags — all pinned
- [ ] Secrets via `.secrets/` + Docker Secrets, never in `environment:`
- [ ] `no-new-privileges:true` on every service
- [ ] DB / Redis on `internal: true` network only
- [ ] `deploy.resources` + `pids_limit` set on every long-running service
- [ ] `read_only: true` where the image allows it
- [ ] `.gitignore` covers `volumes/`, `.secrets/`, `.env`

### Version Audit — run periodically or when upstream advisories appear
- [ ] All `.env.example` image tags still reasonable vs. upstream releases
- [ ] Any upstream security advisories for pinned images?
- [ ] Log the outcome — even "all current" is worth recording to avoid re-checking unnecessarily

### Consistency Audit — run before releases or when the repo grows significantly
- [ ] Every `⚠️ draft` entry has a real directory with files — if not, downgrade to `📋 planned`
- [ ] Every directory in `apps/` `business/` `monitoring/` `backup/` `core/` has a row in its category README
- [ ] Root README tables match category README tables (no phantom entries, no missing entries)
- [ ] `grep -r "__REPLACE_ME__"` returns nothing in committed files
- [ ] `ROADMAP.md` Direction items still reflect intent — archive anything stale
- [ ] `docs/architecture.md` still accurate (new category? changed networking?)

---

## Single Source of Truth Map

Each piece of information has exactly one authoritative location. When two files disagree, this map decides which one wins.

| Information | Authoritative file | All other occurrences mirror this |
|---|---|---|
| App status (✅ / ⚠️ / 📋) | Category README (`business/README.md`, `monitoring/README.md`, …) | Root `README.md` tables mirror the category README |
| App location (which category) | Directory structure | README tables reflect the actual directory |
| What has been shipped | `CHANGELOG.md` — `[Unreleased]` and tagged sections | Nothing else is authoritative for history |
| What is planned / direction | `ROADMAP.md` | Category READMEs may reference ROADMAP items but do not duplicate them |
| How to build an app | `docs/standards/` files | App-level READMEs apply standards, do not redefine them |
| Architecture decisions | `docs/architecture.md` | Category READMEs may summarise, not contradict |
| Per-app setup + verify | `<app>/README.md` | Root README has a one-line description only |
| Per-app config options | `<app>/CONFIG.md` (where it exists) | No duplication elsewhere |
| Security rules | `docs/standards/security-baseline.md` | Checklist is the enforcement tool |

**Rule**: if two files conflict, fix the mirror — not the source.

---

## Cycles

Four cycles, each with a different scope and cadence. They are cumulative: a Consistency Audit includes everything in a Version Audit, and so on.

---

### 1 — Session Routine

**When**: every work session, regardless of what was changed.

- [ ] `CHANGELOG.md` — is `[Unreleased]` updated with what was done today?
- [ ] `ROADMAP.md` — did today's work complete or invalidate a roadmap item? Update if yes.
- [ ] Any file touched — does it still follow the relevant standard? (compose structure, env layout, naming)
- [ ] Add a row to the **Maintenance log** at the bottom of this file.

---

### 2 — App Pass

**When**: every time an app is added, re-verified on a clean install, or significantly changed.

Run the `docs/standards/new-app-checklist.md` in full. Then specifically:

**Standards compliance**
- [ ] `docker-compose.yml` follows compose-structure standard (Identity / Security / Configuration / Storage / Networking / Traefik / Health blocks in order)
- [ ] `.env.example` follows env-structure standard (sections, comments, image links, TZ comment, no real values)
- [ ] Secrets via `.secrets/` + Docker Secrets pattern, never in `environment:`
- [ ] `no-new-privileges:true` on every service
- [ ] Internal network for DB / Redis (`internal: true`)
- [ ] Images pinned — no `:latest`
- [ ] `.gitignore` covers `volumes/`, `.secrets/`, `.env`

**Security baseline** (from `docs/standards/security-baseline.md`)
- [ ] `cap_drop: ALL` + minimal `cap_add` where applicable
- [ ] `read_only: true` where the image supports it
- [ ] `deploy.resources` limits set (memory + cpus) — use measured values from `docker stats`
- [ ] `pids_limit` set on every long-running service
- [ ] Docker socket only through socket proxy (if needed at all)

**Status accuracy**
- [ ] Status in category README matches reality (was this actually live-tested on a clean install?)
- [ ] Root README table matches category README
- [ ] If status changed: add a line to `CHANGELOG.md`

---

### 3 — Version Audit

**When**: periodically, or when an upstream security advisory appears.

The goal: no image tag in any `.env.example` should be more than one major version behind current upstream.

**Process**
1. Run `grep -r "APP_TAG\|DB_TAG\|REDIS_TAG\|_TAG=" */*/\.env.example core/*/.env.example` to list all pinned tags.
2. For each tag: check the upstream release page (linked in the app's `UPSTREAM.md`).
3. If a newer version exists: note it in the log. Do **not** auto-update — test first on a clean install, then bump.
4. If an upstream image has a known CVE or breaking change: flag immediately, document in `docs/bugfixes/`.

**Log what you found** — even "all tags current" is worth recording. The log entry prevents re-checking next month unnecessarily.

---

### 4 — Consistency Audit

**When**: before tagging a release, or when the repo grows significantly.

The goal: no contradictions between any two files in the repo.

**Cross-reference checks**
- [ ] Every app in root `README.md` has a corresponding directory (or is marked 📋 planned with no directory expected)
- [ ] Every directory in `apps/`, `business/`, `monitoring/`, `backup/`, `core/` has a row in the corresponding category README
- [ ] Status in root README matches status in category README for every app
- [ ] Every `📋 planned` entry in a category README is either also in `ROADMAP.md` or clearly scoped to that category only

**Standards drift check**
- [ ] `docs/standards/security-baseline.md` checklist — run it mentally against 3–5 live-tested apps. Do they still comply, or did the standard move forward since they were written?
- [ ] Scan for `__REPLACE_ME__` in all committed files: `grep -r "__REPLACE_ME__" --include="*.yml" --include="*.md" --include="*.sh" .`
- [ ] Scan for real domains slipping in: `grep -r "\.at\b\|\.io\b" --include="*.env.example" .` — everything should be `example.com`

**ROADMAP hygiene**
- [ ] Does every item in `ROADMAP.md` → Direction still reflect what we actually intend to build?
- [ ] Has anything in `ROADMAP.md` → Shipped that hasn't been removed from Direction?
- [ ] Are `ROADMAP.md` → Evaluating items still open, or have some been decided?

**Architecture consistency**
- [ ] Does `docs/architecture.md` still accurately describe the directory structure? (Did we add a category?)
- [ ] Does the networking model diagram still match how apps are actually wired?

**Outcome**: fix contradictions found, update the log with what was checked and what was corrected.

---

## Pre-release Sweep

**When**: before tagging any version (`v0.x.0`). Combines a full Consistency Audit with release-specific steps.

In addition to the full Consistency Audit:

- [ ] `CHANGELOG.md` — does `[Unreleased]` accurately summarise everything since the last tag? Move to a new `[x.y.z]` heading.
- [ ] `CHANGELOG.md` — are the version comparison links at the bottom correct?
- [ ] `ROADMAP.md` — move the newly shipped milestone to the Shipped section.
- [ ] All `⚠️ draft` entries — is the `⚠️` still honest? Promote to ✅ only if tested on a clean install.
- [ ] All `✅ live-tested` entries — were any broken by a dependency update since the last test?
- [ ] Resource limits — are `deploy.resources` and `pids_limit` set on all live-tested apps?
- [ ] GitHub release draft — create via `gh release create vX.Y.Z --draft`.

---

## Maintenance Log

Add one row per session or cycle. This is the record of "where we left off". The next session starts by reading the last two or three rows — not the entire repo.

| Date | Cycle | Scope | What was checked / changed | Carry-forward |
|---|---|---|---|---|
| 2026-04-28 | Setup | Entire repo | Maintenance process document created. Single source of truth map defined. Four cycles defined. | — |
