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
| Status definitions (what ✅ / 🚧 / 📋 promise) | `docs/standards/status-model.md` | Root README legend, `LIFECYCLE.md` |
| App status — `business/`, `monitoring/`, `backup/` | Category README | Root README tables, `LIFECYCLE.md` |
| App status — `core/`, `apps/` | Root README tables | `LIFECYCLE.md` |
| Per-stack lifecycle detail | *generated* — `scripts/ci/lifecycle-report.py` | `LIFECYCLE.md` (never hand-edited) |
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
| AI entry point and rule precedence | `AGENTS.md` | `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/00-project.mdc` — pointers only, never a rule of their own |
| Working context for AI sessions | `.ai/` | Mirrors the owners above in condensed form; `.ai/domains/*.md` restate `docs/standards/` and lose to them on any disagreement |

**Root README structure rule**: tables show `🛡️` / `✅` / `🚧` only. `📋` planned items appear as inline `Planned: X, Y, Z` lines — never as table rows. `🛡️` is listed in every status legend but appears in no table yet; the first stack earns it with the v0.7.0 restore.

`core/` and `apps/` deliberately have no category README — they are documented per service in the root README tables, which is why the root owns their status. Everything derived from these owners is regenerated, not retyped:

```bash
python3 scripts/ci/lifecycle-report.py --write
```

---

## ✅ Ready Criteria

An app is marked ✅ when all of the following are true. Apps that do not meet
every point stay at 🚧 until the gap is closed.

These ten points are the gate between public `preview` and public `ready`, and
together they are exactly the internal status `baseline-aligned` — see
[`standards/status-model.md`](standards/status-model.md) for how the two axes map
onto each other and onto the symbols in the README tables.

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
| 3 | `docs/maintenance.md` | Add a row to the Progress Log. |
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
| 4 | All `🚧` entries | Is the preview status still honest? |
| 5 | All `✅` entries | Were any broken by dependency updates since last test? |
| 6 | GitHub | Minor versions only (`v0.X.0`): `gh release create vX.Y.0 --draft` — review, then publish. Patch tags (`vX.Y.Z`) are Git tags only — no GitHub Release needed. |

---

## Dependency Sweep — 2026-07-26

Repo-wide check of pinned image tags vs. current upstream releases (~30 of ~50 services verified;
rest listed below to finish). Update path = Version Chain above; prefer digest-pinning on bump
(reference: `apps/caldiy`).

### Applied this session (security-critical)

| Service | From | To |
|---|---|---|
| apps/vaultwarden | 1.36.0 | **1.37.0** (SSRF + 7 more fixes) |
| core/authentik | 2026.2.2 | **2026.5.6** |
| apps/nextcloud | 32.0.6 | **32.0.13** (33/34 exist — major, deliberate) |
| apps/ghost | 6.27.0 | **6.54.0** |
| core/crowdsec | v1.7.7 | **v1.7.8** |
| apps/paperless-ngx | 2.20.13 | **3.0.3** (🚧 major — verify: Python 3.11+, API v1 removed, search Whoosh→tantivy reindex) |
| business/invoiceninja | 5.13.24 | **5.13.26** |

### Pending — verified, security-relevant (apply next)

**Applied 2026-07-26** (second wave): wordpress **7.0.2** 🚧, listmonk **v6.2.0**, portainer(+agent)
**2.39.5**, dolibarr **23.0.3**, changedetection **0.55.8**, photoprism **260601**, bookstack
**v26.05.2**, immich **v3.0.3** 🚧, healthchecks **v4.2** 🚧. (🚧 = major, verify migration on deploy.)

Still pending:

| Service | Pinned | Latest | Note |
|---|---|---|---|
| core/traefik | v3.6 | **3.7.9** | floating `v3.6` auto-patches to 3.6.24; evaluate 3.7 (deliberate minor upgrade) |

### Feature/minor — applied 2026-07-26

n8n 2.31.6 · homarr v1.72.0 · onlyoffice 9.4.0 · nocodb 2026.07.0 (🚧 CalVer switch) · openproject 17.6.0 · dashy 4.5.0 · kimai 2.61.0 · gatus v5.36.0

### Up-to-date (no action)

it-tools (2024.10.22, dormant) · beszel + agent (0.18.7)

### Structural (fix regardless of version)

- ~~business/opensign pinned to `main`~~ — **fixed 2026-07-26: digest-pinned.** Upstream ships no semver tags (only `main`/`staging`/`docker_beta`), so both images pinned to `main@sha256:…` for reproducibility (re-pin on upgrade).
- **Floating major tags** — matomo `5-apache`, opnform/invoiceninja nginx `1`/`1.29`, clamav `1.4`. Pin specific (contrast: caldiy is digest-pinned).
- **`main` and `dev` diverged** — Dependabot bumps on `main`, app work on `dev`. Converge.

### Sweep status (2026-07-26)

**Verified current (no action):** it-tools · beszel(+agent) · monicahq 4.1.2 · photoview 2.4.0

**Bumped this session (3rd wave):** easyappointments 1.6.0 · lychee v7.7.1 · librephotos 2026w25 · heimdall v2.8.1 · homepage v1.13.2 🚧 · opnform 2.2.2 🚧

**4th wave applied:** matomo `5.12.0-apache` (was floating `5-apache`) · adminer **5.5.0** 🚧 (major 4→5) · unifi **10.4.57** · dockhand **v1.0.39**.

**Verified current (no action):** it-tools · beszel(+agent) · monicahq · photoview · whoami v1.11.0 · dnsmasq 2.90-r3 · hawser 0.2.39.

**Operator-owned (you version these — no registry check):** vikunja (local build `vikunja-local`) · acme-certs (`ghcr.io/rubennati/cert-ops-tool`) · seafile / seafile-pro (proprietary).

**Genuinely open — awkward tag scheme, decide before pinning:**

- zammad — Docker Hub uses `X.Y.Z-BUILD` (e.g. `7.1.1-0036`) or floating `7`/`7.1`; pinned `7.0.1`. Pick a scheme.
- uptime-kuma — `2.4.0` exists but 1.x→2.x is a major transition; verify before leaving `1.23.17`.

The sweep is otherwise complete: every registry-checkable service is verified or bumped.

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
| 2026-06-19 | App Chain | `core/traefik` | IPv4-only vs. dual-stack IPv6 networking implemented: opt-in `network-dual-stack.yml` overlay (`proxy-public` stays IPv4-only by default — existing installs unaffected), Docker daemon prerequisites with backup/rollback and a full migration guide in new `core/traefik/docs/ipv6-dual-stack.md`, Cloudflare `forwardedHeaders.trustedIPs` added to `traefik.yml.tmpl` (closes the gap tracked in `docs/security-verification.md` control #12). Fixes the failure mode where Tailscale IPv6 clients lose their real source IP on an IPv4-only public network and get blocked by `acc-tailscale` — new snapshot doc `docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`. Cross-referenced from `networking.md`, `traefik-security.md`, `troubleshooting.md`, `architecture.md`. | Not yet exercised against a real dual-stack Docker host — local validation covered `docker compose config` overlay-merge behavior and rendered-YAML syntax only. Operators applying the overlay should follow the migration guide's whoami + `curl -4`/`curl -6` verification steps before cutting production traffic over. |
| 2026-07-26 | Version Chain | 5 security-critical images | Bumped vaultwarden 1.37.0, authentik 2026.5.6, nextcloud 32.0.13, ghost 6.54.0, crowdsec 1.7.8 (+ `.env.example`, `UPSTREAM.md`, README status/verified dates). Not deploy-tested — server offline. | Verify on next deploy. |
| 2026-07-26 | Version Chain | Repo-wide dependency sweep (~30 of ~50 verified) | Checked pinned tags vs. upstream; recorded results in "Dependency Sweep — 2026-07-26". | Pending high: wordpress 7.0.2, listmonk 6.2, portainer 2.39.5, dolibarr 23.0.3, changedetection 0.55.8, bookstack, photoprism; majors to verify: immich 3.x, paperless 3.x, healthchecks 4.x. Structural: opensign pinned to `main`; floating tags; `main`/`dev` diverged. ~15 services not yet verified. |
| 2026-07-26 | Version Chain | 20 more image pins + opensign | Applied the pending sweep updates (wordpress 7.0.2🚧, immich 3.0.3🚧, healthchecks 4.2🚧, nocodb CalVer🚧 + 16 minor/patch); digest-pinned opensign `main` (no semver tags upstream). Not deploy-tested. | Verify majors on deploy; core/traefik 3.7 optional; ~15 services still unchecked. |
| 2026-07-26 | Standards | `apps/_reference` + structure checker | Added the canonical reference app (runnable: postgres `_FILE` secrets + nginx entrypoint-wrapper secrets; prod & local compose; layer-tagged `.env.example`) and `scripts/ci/check-structure.py` (severity per rule). First run found and fixed: repo-root `.gitignore` never covered `.secrets/`; 3 major-only tags (paperless `16`, opensign `6`, opnform nginx `1`); section order in documenso/infisical. Two false positives were verified and the rules corrected (date-based tag `260601`; gitignore rule now reads the root file and only fails when secrets are actually unprotected). `compose-structure.md` gained the `Resources` block so spec and reference agree. | **Open work list** (all WARN, nothing blocking): ~102 services without `deploy.resources`, ~41 without a healthcheck, invoiceninja section order + `env_file:`, core/traefik without `COMPOSE_PROJECT_NAME`, whoami without a local `.gitignore`. **Not done yet:** wire `check-structure.py` into CI (currently 0 FAILs, so it would pass); point `docs/templates/` + `new-app-checklist.md` at `apps/_reference/` so only one template exists; `apps/_reference/UPSTREAM.md`; actually boot the reference stack (Docker daemon was off, so "runnable" is unproven). |
| 2026-07-26 | Version Chain | Finish sweep (3rd wave) | Bumped easyappointments 1.6.0, lychee v7.7.1, librephotos 2026w25, heimdall v2.8.1, homepage v1.13.2🚧, opnform 2.2.2🚧; monicahq/photoview confirmed current. caldiy → v6.2.0-3 (new digest). Merged `main`→`dev`. | Operator-tracked (seafile) / floating (matomo) / awkward-source (unifi, zammad, vikunja, uptime-kuma, adminer) remain — see Sweep status. |
| 2026-07-26 | Session | `ROADMAP.md` | Roadmap synced to the actual state — it had not been touched since 2026-06-04. Checked first whether any of the intervening work blocks v0.7.0: it does not, so **the milestone order stays unchanged**. Added a "Since v0.6.0 — work outside the plan" section placing the sweep, reference app + structure checker, four new drafts, the Cal.diY track, and the supply-chain work. v0.7.0 gained two practical notes (backup services start from `apps/_reference/`; restore walkthroughs share the host precondition with the pending majors). v0.9.0 gained measured numbers from the checker (54 apps · 102 services without `deploy.resources.limits` · 41 without a healthcheck). v1.0 CI baseline updated (Trivy done, structure checker written but not wired in). Corrected stale entries: Cal.com retired, OpnForm in place, category counts; added office-server and e-signature choice matrices. Status-language convention applied ("verified" instead of "sober-/live-tested", "review" instead of "audit"). | **Found, not fixed — needs a decision:** 12 services claim ✅ in the root README but `🚧` in their owning category README (business: dolibarr, kimai, listmonk, matomo, zammad, opensign; monitoring: all six). Per the File Map the category README is the owner, and criterion 8 backs it — all 12 still carry the pre-v0.5.1 `Last checked:` field instead of `Last verified: DATE (vX.Y.Z)`. Either correct the root README to 🚧 or verify the 12 and update both. |
| 2026-07-26 | Standards | Status model — repo-wide | Resolved the root cause behind the 12 mismatches above: three status systems ran in parallel (root README, category README, `LIFECYCLE.md`) with no derivation between them, so drift was structural rather than accidental. New `docs/standards/status-model.md` defines the public axis (what an operator can rely on) and the internal axis (what the maintainer has established), maps them onto each other and onto the ✅ Ready Criteria — all ten criteria = `baseline-aligned` = public `ready` = ✅ — and records the owner of every fact. `LIFECYCLE.md` is now generated by `scripts/ci/lifecycle-report.py` across all 54 stacks (was 6, hand-written, three months stale, and claiming backup/restore docs that no stack has ever had). Two CI jobs added: `Canonical structure` (`check-structure.py`, previously written but never wired in) and `Status model` (`lifecycle-report.py --check`). Root README corrected to 🚧 for the 12; dead `core/README.md` + `apps/README.md` links removed from the front page; 🚧 relabelled Draft → Preview repo-wide; `docs/templates/` folded into `apps/_reference/` (+ its missing `UPSTREAM.md`) so one template remains; whoami `.gitignore`, traefik `COMPOSE_PROJECT_NAME`, invoiceninja section order fixed. All six CI checks pass locally. | **20 stacks carry `Last checked:` instead of `Last verified: DATE (vX.Y.Z)`** — reported as `legacy-stamp` (WARN, non-blocking). The date exists, so evidence probably does too; converting the field asserts that evidence is real, which is a per-app judgement and never automatic. Decide per app on the next host session. **Still open:** invoiceninja `env_file:` (needs the Laravel entrypoint wrapper, not a cleanup); 102 services without `deploy.resources.limits` and 41 without a healthcheck (v0.9.0 — needs measuring, must not be guessed); the reference stack has still never been booted. |
| 2026-07-26 | Standards | `backup/` + checker coverage | v0.7.0 architecture written before any service: layer model (snapshot/backup/archive), host agent with the reasoning (a containerised agent needs read access to every volume, therefore every secret), both volume types without preference, Borgmatic 2.0.8 `container:` hooks for Postgres/MySQL/MariaDB/SQLite, four-stage adoption, and append-only documented as upstream states it — `delete`/`prune` remain allowed, recovery is a manual transaction rollback and only while `borg compact` has not run. Added `backup/borgmatic/` (config, timer, README, RESTORE) as the first host-installed component — no compose file by design. Extending the lifecycle generator to cover it surfaced two blind spots: **`apps/seafile` and `apps/seafile-pro` split their compose across per-component files and had therefore never been seen by `check-structure.py`** — two ✅ stacks never checked for `:latest`, plaintext secrets, unprotected `.secrets/` or exposed datastores. Both now checked (0 FAILs); warnings rose 147→176 because their services became visible, not worse. | Overlay files (`activitypub.yml`, `*.local.yml`, `network-dual-stack.yml`) are still unchecked — deliberate for now, they are opt-in. Borgmatic itself is unexercised: no host, no target, no restore rehearsal. `RESTORE.md` carries an empty rehearsal log until then. |
| 2026-07-27 | Standards | v0.7.0 Phase A — `backup/urbackup` + borgmatic corrections | Added UrBackup as the second direction of backup (client/endpoint → this host), bridge+Traefik by default instead of upstream's `network_mode: host`, with `network-host.yml` as an opt-in overlay for broadcast discovery. Digest-pinned (upstream ships only rolling series tags). Mapping borgmatic's integration list against the repo produced three corrections: **MongoDB was missing from every engine claim** although `apps/unifi` and `business/opensign` run it; **Layer 0 was wrong** — borgmatic can drive btrfs/ZFS/LVM snapshots itself, which answers the named-volume consistency gap; and **`backup` was absent from `check-structure.py` ROOTS**, so nothing in the category would ever have been checked. Credentials reworked from `${ENV}` interpolation to `{credential file ...}` pointing at the stack's own `.secrets/` file. Added `docs/host-session-v0.7.0.md` and the per-app `## Backup` pattern in `apps/_reference/`. | **Third checker-coverage gap in one day** (split compose, compose-less components, missing ROOT). Worth inverting the check: report any directory with content that no checker covers, instead of finding the next one by accident. **Kopia deferred to v0.8.0**; Bareos kept as planned with a stated reason. All 59 stacks still show `Backup docs: missing` — the pattern exists, the filling happens per app. |
| 2026-07-27 | Session | `.ai/` coherence pass | Coherence check across the `.ai/` layer, the File Map and the checkers. All three checkers pass (0 failures; 176 structure warnings, 22 `legacy-stamp`), and root README / category READMEs / `LIFECYCLE.md` agree on every status. Four stale statements corrected: the v0.8.0-scope open decision was resolved at its owners (`ROADMAP.md` and `monitoring/README.md` both now describe five axes with alerting as the cross-cutting layer) but was still listed as open; a cross-reference pointed at a decision number that no longer existed; the v0.9.0 progress bar still carried the pre-`backup/` counts (now 57 apps · 121 services without limits · 54 without a healthcheck — the rise is checker coverage, not regression); `.ai/risks.md` repeated that count instead of deferring to its owner. **Ownership gap closed:** `AGENTS.md`, the three tool pointer files and `.ai/` had no File Map row and appeared in no chain — both added, with `.ai/state.md` now a Session Chain step so a decision resolved at its owner gets struck there. `.ai/domains/*.md` checked against `docs/standards/`: condensed restatements, no contradictions. | Open decisions 1–6 in `.ai/state.md` are untouched and still the maintainer's. `.ai/` is committed and therefore public — internal process detail (branch lifecycles, deletion plans) does not belong in it. |
| 2026-07-27 | App | v0.8.0 desk work — `monitoring/ntfy` + alerting documentation | Added the first notification receiver to `monitoring/`. Channel support was verified against upstream documentation rather than taken from the stack READMEs, which produced two corrections worth having before a host session: **Beszel has no email path at all** — it sends only through Shoutrrr URLs — so a single channel spanning all five monitoring services cannot be SMTP; and Healthchecks reaches Gotify only through Apprise, which needs `APPRISE_ENABLED` and a package not in the stock image. The matrix is now in `monitoring/README.md`. `acc-public` on ntfy is a documented deviation from the category's VPN-only default, compensated by `auth-default-access: deny-all`, because upstream's default makes every topic world-readable and world-writable once the server is public. The alerting section was also split: what the blueprint verifies versus what the operator decides when deploying — the previous "prove it arrives while the host is down" step was a topology requirement in a blueprint checklist, and it is now stated as a property of the deployment. The dead-man's-switch pattern gained its name from safety engineering, the closed-circuit principle. Gotify recorded as 📋 planned. All three checkers pass; the new stack adds no structure warnings. | **Nothing here has run.** ntfy stays 🚧 until it starts on a host: `read_only: true` is untested, the `sec-3` rate limit is the first suspect if notifications go missing under load, and `user:` is commented because it needs the mounted paths chown'd first. All four are listed in the stack's Known Issues rather than left to be discovered. |
| 2026-07-27 | Session | Coverage checker · `business/` backup docs · v0.8.0 and v0.9.0 preparation | Acted on a status review rather than adding features. **`scripts/ci/check-coverage.py`** closes the pattern behind three blind spots that had surfaced by accident: it enumerates content and asks which checker claims it, instead of asking whether known stacks comply. Verified against both gap classes — a compose-less directory under a stack root and an undeclared top-level directory each produce a FAIL — and it correctly reports `backup/borgmatic` as structure-blind. An earlier version of it missed borgmatic because it keyed on marker filenames; that is the same mistake it exists to catch, so it now treats any tracked file as content. **`business/` backup documentation** filled for all ten stacks from the compose files, taking backup coverage from 7 of 59 to 17. **`docs/host-session-v0.8.0.md`** and **`docs/resource-measurement.md`** added, the latter because v0.9.0 cannot be prepared at a desk — only the method can. `docs/standards/ci.md` documented 4 of 8 jobs and now documents all 8. Two stale ROADMAP claims corrected: the structure checker was listed as not wired into CI, and the Operator Site as pending when its content and deploy pipeline both exist. | **42 stacks still lack a `## Backup` section** — `core/`, `apps/` and the rest. Per category, from the compose file. `Checker coverage` runs but is not in the required set; adding it is a branch-protection setting, not a file here. Invoice Ninja's borgmatic block is written but unusable: the stack keeps its database password in `.env` rather than `.secrets/`. Markdown lint remains the one missing v1.0 CI baseline item. |
| 2026-07-27 | App | `## Backup` sections — `core/`, `apps/`, `backup/urbackup` | Completed the sweep started with `business/`: 41 further stacks, taking backup documentation from 17 of 59 to 58 of 59. Written from each compose file, so the non-obvious cases are stated rather than inferred — Seafile needs **three** databases dumped (`ccnet_db`, `seafile_db`, `seahub_db`) and backing up only `seafile_db` restores to something that starts and does not work; Nextcloud is the one stack here where maintenance mode genuinely matters, because the file index and the file tree diverge under load; Immich's Postgres carries a vector extension and must be restored into its own image, not a stock one; PhotoPrism's `volumes/storage` is mostly cache but holds sidecar edits that exist nowhere else, so excluding the whole tree is wrong; Vaultwarden's `rsa_key*` files leave every client unable to log in if lost. Several stacks hold their irreplaceable half **outside** the stack directory (`UPLOAD_LOCATION`, `SCAN_DIRECTORY`, `ORIGINALS_PATH`), which is exactly why it gets forgotten. `backup/urbackup` gained a section whose headline is an *exclusion*: `BACKUP_STORAGE_PATH` must not enter borgmatic's sources, or terabytes of already-deduplicated client backups get re-deduplicated into the Borg repository. | **`backup/borgmatic` is `n/a`, not missing** — a backup tool cannot document backing itself up with itself; `lifecycle-report.py` now carries that as a declared exception with its reason, and the column legend explains the marker. `backup/urbackup` still has no restore section: restoring a *client* backup is a real procedure and the one remaining gap in that column. Two `core/` sections had to be relocated after insertion — a "Phase 1: Security Engine" and a "Security System" heading both matched a substring rule and split a setup flow. |
| 2026-07-27 | Standards | Backup-doc ownership · corrected Vaultwarden deviation | Follow-up to the sweep, prompted by the question why two stacks keep secrets in `.env`. Both have a recorded reason; only one holds. **Invoice Ninja is genuinely upstream-limited** — Laravel has no `_FILE` for most variables including `APP_KEY` and `DB_PASSWORD`, with an entrypoint wrapper recorded as Phase 2. **Vaultwarden's recorded reason was wrong**: `UPSTREAM.md` and the compose comment both claimed no `_FILE` support, which the upstream configuration wiki contradicts. Whether that was wrong when written (2026-06-14) or went stale could not be established — the release notes do not mention the feature and a commit search returned nothing, so the correction states what is confirmed today rather than inventing a history. The genuine obstacle is narrower and now recorded as such: the password sits inside `DATABASE_URL`, so the secret has to carry the whole URL or an entrypoint has to assemble it. **Ownership**: both stacks already had backup procedure in `UPSTREAM.md`, which `lifecycle-report.py` does not read — so both showed as "missing" and the sweep wrote a second copy next to the first. Consolidated into the README, keeping what the older versions had and the sweep did not: Invoice Ninja's `APP_KEY`, without which a restored database cannot be decrypted. New `backup-docs-split` WARN catches the pattern — a backup or restore heading in `UPSTREAM.md` whose body holds a table or a command block, verified by restoring the duplicate and watching it fire. | `apps/vaultwarden` → Docker Secrets is now open work rather than a blocked path, but it changes how a ✅ stack starts and belongs in a host session. `business/invoiceninja` keeps its Phase 2 entrypoint plan. |
| 2026-07-28 | Standards | Docs QA gate — markdown lint + internal link checker | First phase of a repo-wide quality pass. Baseline was 7,900 markdown findings and no gate at all; the v1.0 CI baseline had listed markdown lint as missing since it was written. Over 7,000 of those findings were two rules arguing with deliberate house conventions (line length, compact table pipes), so the ruleset was tuned to the repository rather than the repository to the ruleset — each disabled rule records the convention it would break. **The lint found a real defect:** a table row in `new-app-checklist.md` whose inline code contained an unescaped pipe, so Markdown read it as a third column and discarded the rest when rendering. The advice that vanished was the trailing-newline fix that `errors.md` lists as a recurring failure. **The auto-fix caused two of its own**, both caught by reading the diff rather than trusting it: a wrapped sentence whose literal `+` was reformatted into a list item, and a numbered list renumbered to `1.` `1.` because an unindented fence split it. Same class in the 121 fence labels — of eighteen classified as `yaml` by first-line heuristic, seventeen were log output. Every one reviewed by hand. New `scripts/ci/check-links.py` validates relative paths and heading anchors offline; external URLs are out of scope because they fail for reasons unrelated to the commit. Both checks verified by introducing the defect they catch. | `Docs QA` runs but is not in the required set — branch protection, not a file here. `--fix` is deliberately **not** run in CI: automatic rewriting of prose needs a human reading the diff, which this session demonstrated twice. Remaining phases: action pinning, Renovate for the `APP_TAG` pins, digest policy + SBOM, Trivy gating. |
| 2026-07-28 | Standards | Workflow supply chain — action pinning enforced | Second phase of the quality pass. `site.yml` referenced `actions/checkout@v7` and `actions/setup-node@v7` by mutable tag while all three other workflows pinned by SHA — a tag the action owner can move at any time, with the new code running under the same repository permissions. Both pinned to `v7.0.0`, with each SHA resolved through the GitHub API rather than copied from elsewhere: `actions/checkout@v7` currently points at a *newer* commit than the repository's `v7.0.0` pin, which is the pin working as intended and would have been easy to "correct" wrongly. Also found: the `github/codeql-action` SHA in `scorecard.yml` carried a `# v3` comment while the identical SHA in `trivy.yml` said `# v4.37.1` — the commit is v4.37.1, so one of the two had been misleading readers about what runs. New `scripts/ci/check-workflows.py` enforces all of it — SHA pinning, a version comment beside each SHA, and a top-level `permissions:` block per workflow — verified by breaking each rule in turn. | `Workflow supply chain` runs but is not in the required set. Phase 3 is Renovate with custom managers for the `APP_TAG` pins in `.env.example`, which Dependabot cannot read; it is the phase with the largest payoff and the most room to go wrong, since a careless configuration opens dozens of pull requests at once. |
| 2026-07-28 | Standards | Dependency-update proposal — written, not activated | Third phase of the quality pass, deliberately stopping short of a working configuration. **A false negative in the earlier survey was corrected first:** the phase plan recorded "no Dependabot, no Renovate", but `.github/dependabot.yml` has existed since the Scorecard work — the check that produced that finding used a shell glob that matched nothing, which aborted the command and fell through to its "none" branch. Same class as the checker that reported 0 of 20 action references. GitHub Actions are therefore already covered; only the ~118 image pins are not, because every image is written `image: app:${APP_TAG}` and Dependabot does not resolve the variable. **The anchor was measured rather than assumed:** `env-structure.md` prescribes the image name in a comment above the pin, but that holds for 90 of 118 — the other 28 carry something more important in that line, such as UniFi's "MongoDB MUST stay at 4.4". A 76%-consistent convention is a worse machine anchor than none, since it mis-assigns rather than fails. Explicit `# renovate:` markers recommended. Regexes dry-tested against all six real pin shapes; `managerFilePatterns` confirmed as the current option name against the documentation source, the rendered docs page having served the superseded `fileMatch`. | Three decisions belong to the maintainer and nothing runs until they are made: markers vs. normalising the outliers, App vs. self-hosted Action, and whether `site/`'s unwatched `package-lock.json` rides along. Sequencing in the proposal puts the inert steps first, so no pull requests appear before the anchors are reviewed. Phases 4 and 5 — digest-pinning policy plus SBOM, and raising Trivy's exit code — remain untouched. |
