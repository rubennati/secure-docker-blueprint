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

Each piece of information has exactly one owner. When two files disagree, the owner wins and the mirror is corrected.

| Information | Owner | Mirrors / references it |
|---|---|---|
| App status (✅ / 🚧 / 📋) | Category README | Root README tables |
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

**Root README structure rule**: tables show `🚧` / `✅` only. `📋` planned items appear as inline `Planned: X, Y, Z` lines — never as table rows.

---

## ✅ Ready Criteria

An app is marked ✅ when all of the following are true. Apps that do not meet
every point stay at 🚧 until the gap is closed.

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
8. `UPSTREAM.md` present — source, license, `Last verified: YYYY-MM-DD (vX.Y.Z)`, upgrade checklist
9. `.env.example` complete — all required fields present, no real domains or credentials as defaults

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
| 3 | All Draft apps (`🚧`) | Note any drift — fix before next verification pass |
| 4 | `CHANGELOG.md` | Standard change documented |
| 5 | `docs/maintenance.md` | Progress Log: which apps were checked, which have open drift |

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
| 4 | All `🚧` entries | Is the draft status still honest? |
| 5 | All `✅` entries | Were any broken by dependency updates since last test? |
| 6 | GitHub | `gh release create vX.Y.Z --draft` — review, then publish |

---

## Progress Log

One row per session or chain run. The next session starts here — not at the top of the repo.

| Date | Chain | Scope | What was done | Open / carry-forward |
|---|---|---|---|---|
| 2026-04-28 | Setup | Entire repo | Process document created. File map defined. Chains defined. | — |
| 2026-04-28 | Consistency | Entire repo | First live run. Fixed: SMTP hostnames in 3 `.env.example` files, broken Ackee link, root README pattern (tables = 🚧/✅ only, Planned = inline). Rules refined: `__REPLACE_ME__` scan scoped to compose+scripts, vendor hostname scan added. | Category READMEs need content depth pass (choice guidance, integration notes) to differentiate from root README. |
| 2026-04-29 | Setup | Process redesign | Rebuilt `maintenance.md` as a process map with trigger-based chains. Removed duplicate rules — chains reference standards, do not repeat them. | First real chain run pending. |
| 2026-05-01 | App Chain | `core/authentik` | Fixed: `init-perms` missing `no-new-privileges:true`; `UPSTREAM.md` still on 2024.12.3 → bumped to 2026.2.2. Found two violations in `docs/standards/env-structure.md` itself: SMTP example used real vendor hostname, TZ default was Europe/Vienna instead of UTC — both fixed. | Open: `cap_drop` missing on all services (Recommended); `deploy.resources` + `pids_limit` not set (v1.0 Polish, needs measuring). |
| 2026-05-02 | App Chain | `apps/ghost` | Live-tested end-to-end: `ghost:6.27.0-alpine` + `mysql:8.4` + ActivityPub overlay (`1.2.2`). Four bugs fixed: (1) ERR_INVALID_ARG_TYPE — custom entrypoint for secrets; (2) activitypub-migrate TCP connection refused — mysqladmin `-h 127.0.0.1` + password from secret file; (3) ERR_TOO_MANY_REDIRECTS — X-Forwarded-Proto middleware on ActivityPub Traefik router; (4) SMTP TLS mismatch — `mail__options__secure` made configurable via `GHOST_MAIL_SECURE` env var, `.env.example` defaults updated to Brevo/STARTTLS (port 587, secure=false). Login and email confirmed working end-to-end. Ghost status: ✅. | — |
| 2026-05-02 | Session | `apps/ghost` | Final verification on clean install: all services healthy, admin setup + login via SMTP code working, ActivityPub overlay running (migrate exited 0, webhooks registered). Cleanup: overlay renamed `activitypub.yml`, dead `ops/mysql-init.sh` removed, bugfix doc completed (4 bugs + correct entrypoint snippet). ROADMAP last-updated bumped. | — |
| 2026-05-02 | Version Chain | `apps/dashy` | Tag `3.1.1` never existed on Docker Hub. Bumped to `4.0.4`. Fixed healthcheck path (v4 added `.js` extension). Verified startup on clean install. | — |
| 2026-05-02 | App Chain | `apps/dashy`, `apps/heimdall`, `apps/homarr` | Full App Chain run for all three. Version fixes: Dashy 3.1.1→4.0.4, Homarr 1.39.0→v1.60.0 (both tags never existed). Security baseline: cap_drop+:ro+resources on Dashy; resources+healthcheck on Heimdall (cap_drop skipped, s6-overlay); resources+healthcheck on Homarr (cap_drop skipped, runs as root). Env files aligned to standard. Status 🚧→✅ for all three. | — |
| 2026-05-03 | App Chain | `core/authentik`, `apps/dashy`, `apps/heimdall`, `apps/paperless-ngx` | Authentik Forward-Auth integration live-tested end-to-end. Three bugs found and fixed: Traefik router priority=10 → 100 on path-scoped routers; Pattern 2 External host must include protected path for correct post-login redirect; SPA 429 on first load (NocoDB, n8n, Authentik login) — fixed with `rl-spa` (burst 200) + `sec-3-spa` chain + `/_static/` router split. Dashy + Heimdall protected via Pattern 1 (✅). Paperless `/admin` protected via Pattern 2 (✅). | — |
| 2026-05-03 | Session | Release v0.5.0 | CHANGELOG `[Unreleased]` → `[0.5.0]`. ROADMAP: v0.5.0 → Shipped, v0.6.0 (CrowdSec) added. README badge bumped. Git tag + GitHub Release published. | — |
| 2026-05-03 | Standards Chain | `docs/maintenance.md` | Added ✅ Ready Criteria (9-point checklist). Updated App Chain step 5 to `Last verified: YYYY-MM-DD (vX.Y.Z)` format. Updated Release Chain: badge bump + `--draft` flag. Updated all 10 live-tested UPSTREAM.md files: `Last checked` → `Last verified: DATE (vX.Y.Z)`. | — |
| 2026-05-03 | Consistency | Entire repo | Full audit across 7 categories: 27 findings. Fixed HIGH: stale Draft banners (4 READMEs), portainer-agent + invoiceninja root README status 🚧, Ghost SMTP vendor hostname, env-structure.md TZ checklist, seafile-pro 6 rolling `-latest` tags, nextcloud major-only tags. Fixed MEDIUM: TZ=UTC in invoiceninja + seafile-pro, paperless-ngx tag pins, onlyoffice pin, 6× redis 7.4→7.4.7, ROADMAP Paperless stale entry, business README dead links, acme-certs deprecation notice, maintenance log gaps. | Open: 9 🚧 apps missing UPSTREAM.md; Invoice Ninja docker-compose needs security baseline pass before ✅; Vaultwarden deviation note pending. |
| 2026-05-03 | Session | Release v0.5.1 | Fixed: Nextcloud network isolation, Seafile CE sidecar tag pinning, Immich healthcheck no-ops, README `.secrets/` path + `tr -d '\n'`, README feature claim softened, security-baseline Hawser deviation clarified, Zammad inline password deviation documented, Portainer Agent mount comment. Standards: two-tier tag pinning formalised, ✅ Ready Criteria added, `Last verified` format standardised. ROADMAP: v0.7–v1.1 milestones, image vulnerability scanning, secrets rotation, backup restore testing added. | — |
