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

### Registry check (2026-08-16)

Every image reference in the tree resolved through its `.env.example` and compared
against its registry — 98 references. The script is in the session scratchpad and
is not part of CI; `scripts/ci/list-images.sh` covers 11 stacks by hand and is the
thing worth replacing with the discovery `check-structure.py` already has.

**Three comparisons in that run were wrong.** A comparison that parses only
numbers reads `2021.11.28` as newer than `2.8.1` (`apps/heimdall`), `20220121` as
newer than `260601` (`apps/photoprism`, which tags `YYMMDD`), and the build number
`511` as newer than `5.13.26` (`business/invoiceninja`). All three of those stacks
are current. A tag comparison has to reject a candidate whose scheme differs from
the pinned one.

**Acted on:**

| Stack | Was | Now | Why |
|---|---|---|---|
| `business/zammad` | `7.1.1-0036` | `7.1.2-0013` | 18 advisories published 2026-08-04, one critical |
| `apps/unifi` | `mongo:4.4` | `mongo:8.0` | 4.4 reached end of life in February 2024. The pin rested on a claim the image's own documentation contradicts — it supports 3.6–7.0 from UniFi 8.1 and 8.0 from 9.0, and this stack runs 10.x |

**Still behind, not acted on:**

- `business/opensign` runs `mongo:6.0`, which reached end of life in July 2025. What OpenSign supports has not been checked against upstream, so the version to move to is unknown.
- Database and runtime bases are a major behind in several stacks — PostgreSQL 16/17 against 18, MariaDB 10.11/11.4 against 12, Redis 7.4 against 8, Elasticsearch 8.15 against 9. All of these are on supported branches; being behind is not the same as being unsupported, and a database major is a migration rather than a pin change.
- Roughly a dozen stacks are one minor or patch behind. Nothing there is security-driven as far as this check can tell.

**The check is incomplete.** Docker Hub rate-limits after about a hundred tag
queries, so the run degraded partway through and the figures above cover what
completed. Re-running it needs either pacing or an authenticated token.

### Sweep status (2026-07-26)

**Verified current (no action):** it-tools · beszel(+agent) · monicahq 4.1.2 · photoview 2.4.0

**Bumped this session (3rd wave):** easyappointments 1.6.0 · lychee v7.7.1 · librephotos 2026w25 · heimdall v2.8.1 · homepage v1.13.2 🚧 · opnform 2.2.2 🚧

**4th wave applied:** matomo `5.12.0-apache` (was floating `5-apache`) · adminer **5.5.0** 🚧 (major 4→5) · unifi **10.4.57** · dockhand **v1.0.39**.

**Verified current (no action):** it-tools · beszel(+agent) · monicahq · photoview · whoami v1.11.0 · dnsmasq 2.90-r3 · hawser 0.2.39.

**Operator-owned (you version these — no registry check):** vikunja (local build `vikunja-local`) · acme-certs (`ghcr.io/rubennati/cert-ops-tool`) · seafile / seafile-pro (proprietary).

**Genuinely open — awkward tag scheme, decide before pinning:**

- zammad — scheme decided: pin `X.Y.Z-NNNN` at the **highest** build of the target release. A release
  keeps receiving builds after it ships, so the first build of a version is not the version. Now at
  `7.1.2-0013`.
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
| 2026-07-28 | Standards | Dependency-update proposal — written, not activated | Third phase of the quality pass, deliberately stopping short of a working configuration. **A false negative in the earlier survey was corrected first:** the phase plan recorded "no Dependabot, no Renovate", but `.github/dependabot.yml` has existed since the Scorecard work — the check that produced that finding used a shell glob that matched nothing, which aborted the command and fell through to its "none" branch. Same class as the checker that reported 0 of 20 action references. GitHub Actions are therefore already covered; only the ~118 image pins are not, because every image is written `image: app:${APP_TAG}` and Dependabot does not resolve the variable. **The anchor holds for 90 of 118 pins:** `env-structure.md` prescribes the image name in a comment above the pin, but that holds for 90 of 118 — the other 28 carry something more important in that line, such as UniFi's "MongoDB MUST stay at 4.4". A 76%-consistent convention is a worse machine anchor than none, since it mis-assigns rather than fails. Explicit `# renovate:` markers recommended. Regexes dry-tested against all six real pin shapes; `managerFilePatterns` confirmed as the current option name against the documentation source, the rendered docs page having served the superseded `fileMatch`. | Three decisions belong to the maintainer and nothing runs until they are made: markers vs. normalising the outliers, App vs. self-hosted Action, and whether `site/`'s unwatched `package-lock.json` rides along. Sequencing in the proposal puts the inert steps first, so no pull requests appear before the anchors are reviewed. Phases 4 and 5 — digest-pinning policy plus SBOM, and raising Trivy's exit code — remain untouched. |
| 2026-07-28 | Session | `.ai/state.md` — corrected a stale precondition | The file recorded "No host available. Everything requiring a running server waits" as the constraint behind three milestones. The blueprint's stacks are in fact running across several environments; what is missing is a machine that may be broken, filled with throwaway data and restored into. Stating it as "no host" made v0.7.0 look blocked by something unobtainable rather than by a disposable VM. Constraint reworded, and the real-values discipline added explicitly because a host session is exactly when real domains and secrets are at hand. Next steps rewritten as an ordered run across both host-session documents, with the resource sampler started first so v0.9.0 gets its measurements from containers that are being started anyway. Open decisions rewritten to be answerable without chat history — conflict, options and a recommendation each — and extended from six to eight with the Renovate questions and the `core/` composition. | None of the eight blocks the host session. Two cost a minute each and have been open for weeks. `core/` composition is deliberately sequenced *after* the host session: it is a structural change and moving directories mid-verification would invalidate what was just verified. |
| 2026-07-28 | Session | First host session — Traefik verified, findings recorded | The blueprint ran on a real Debian 13 host for the first time. **Traefik came up correctly from a clean clone**: healthy on first start, wildcard certificate via DNS-01 on the first attempt, both entry points bound on IPv4 and IPv6, dashboard reachable over the tailnet and refused everywhere else. **The real client IP was verified over four paths** — public IPv4, public IPv6, Tailscale IPv6 and a commercial VPN exit node — which is the property CrowdSec, the access policies and every rate limit depend on. **`TROUBLESHOOTING.md` 4.4 is no longer undiagnosed.** It had carried "root cause (not fully diagnosed)" and recommended switching to `acc-public` as a workaround — that is, disabling the IP check for everyone. The cause is that a tailnet client connects directly with an IPv6 source address and no forwarded header exists to recover it from, so an IPv4-only `proxy-public` loses it before the allowlist is evaluated. Rewritten with the dual-stack fix and an explicit note that the three daemon flags and the overlay were applied together and not isolated. 4.3 gained the case where a *corrected* DNS record is still served stale by the browser, which presents identically to a rejecting access policy and cost time here. Seven findings recorded in the new `docs/host-session-findings.md`, together with the sequence that actually worked and a rule for reviewing the list afterwards rather than fixing during the session. | The `acc-public` workaround also lives in `apps/seafile-pro/UPSTREAM.md` and should be revisited. Nothing from the findings list has been fixed yet — that is deliberate. New task: `docker-compose.local.yml` exists for 6 of 57 stacks; extending it lets someone try an app without standing up Traefik, DNS and certificates first, and is the natural entry point for the operator site. |
| 2026-07-28 | Docs | Operator site — first concrete setup walkthrough | The site had a conceptual Getting Started page describing the order of steps but not one command, and an Operations placeholder. The first host session produced exactly what was missing: a verified path from a fresh Debian host to a working TLS-terminated foundation. Written as `getting-started/server-setup.mdx` from the operator's point of view — no repository internals, no file map, no mention of the checkers. Leads with the decision that is expensive to reverse (IPv6 before anything starts, because a VPN client's source address is otherwise lost and the VPN-only policy rejects the VPN), and states the symptom rather than the mechanism: a 403 that looks like permissions and is networking. Includes the `whoami` measurement as the verification that matters, with the instruction to close it again — and the browser-DNS-cache trap, because a corrected record presents identically to a rejecting policy. Sidebar restructured so Getting Started has children. Site builds, 14 pages. | This is the pattern for the rest of the operator documentation: the repository keeps the reasoning and the maintainer's view, the site carries the sequence someone follows without having read the source. The Operations placeholder still says "planned for v0.9.0" — backup and restore content lands there once the host session produces it. |
| 2026-07-29 | App | `apps/nextcloud` rebuilt on 34.0.2 — unattended install, network exception | Nextcloud was pinned to 32.0.13, the oldest maintained major, with **two months of support left**; Nextcloud has no LTS and gives each major twelve months. Rebuilt on 34.0.2 from an empty volume, and the rule behind that choice is now in `env-structure.md`: pin the newest version the project recommends for production, and record the end-of-life date before pinning — nothing in this repository notices an expiring base. Status dropped to 🚧: the ✅ rested on a verification of 32. **The setup wizard is gone.** `NEXTCLOUD_ADMIN_USER_FILE` and `_PASSWORD_FILE` make the entrypoint run `occ maintenance:install` at first start, which dissolves three findings at once — no wizard means no root-owned files blocking installation, no SQLite offered while a configured MariaDB idles, and no unauthenticated form reachable during setup. `acc-private` replaces `acc-public` as the shipped default. Redis password moved out of the environment into a secret; it must be owned by the web user because the image reads it at PHP runtime, which upstream documents and which Compose cannot solve with `uid`/`mode` outside Swarm. Hardening applied via `occ` from the admin manual: maintenance window, preview bounds, skeleton files off, admin actions restricted to the VPN, five telemetry and UI-noise apps disabled. **Network exception documented**: `app` and `cron` get an egress network while `db` and `redis` stay isolated — without it, mobile push, app store, outgoing mail, external storage and the instance's own setup checks all fail, and every outbound attempt costs a five-second timeout. Setup checks went from 7 warnings and 1 error to 3 warnings and 0 errors, 57 passing. | Two real findings remain, both about the Traefik chains rather than Nextcloud: `X-Frame-Options` is `DENY` where Nextcloud needs `SAMEORIGIN`, and no chain combines the iframe-friendly variant with the SPA rate limit — `sec-3e-spa` does not exist. And `.well-known/caldav` fails because the middleware rewrites internally where a 301 is expected. SMTP is still unconfigured, so password reset does not work. |
| 2026-07-29 | Standards | Traefik chains adjusted to a real app | Two corrections to the proxy layer, both surfaced by verifying Nextcloud rather than by reading the configuration. **`sec-3e-spa` did not exist.** The chains combine three independent properties — header strictness, frame policy, rate limit — but are named as a single scale, so only ten of sixteen combinations are defined. Nextcloud needs `X-Frame-Options: SAMEORIGIN` *and* the wider first-load burst, which was one of the six gaps. Added. **The rationale for the SPA variants was wrong**: the template restricted them to VPN-gated apps, but `rl-soft` and `rl-spa` share the same sustained rate of 100 and differ only in burst size — the restriction bought 429 errors during normal use and no protection. Corrected. **And `.well-known/caldav` was broken by a middleware that duplicated working configuration:** the stack's nginx already returns the documented `301`, while a `replacepathregex` rewrote the path first so the redirect never fired. Removed rather than replaced. Nextcloud now passes all 60 of its own setup checks with no warnings. | The naming remains the larger issue: `sec-1e`, `rl-spa`, `hdr-strict-embed` do not tell a newcomer what they select, and bundling three axes into one scale is why the missing combination was the needed one. Renaming touches the `.env` of 48 stacks and is its own decision. TLS profiles have not been reviewed per app at all. |
| 2026-07-29 | Session | `backup/borgmatic` exercised end to end — first backup, first restore | The configuration had never run. Both directions were performed against a live Nextcloud stack and the archive was inspected rather than trusted: `config.php` compared against the live file, and a full MariaDB dump loaded into a throwaway container where 131 tables, the expected account and 114 rows in the file index were checked by query. **Three documented claims did not survive contact**: the `container:` hook still needs the engine's client on the host, the packaged borgmatic is older than the 2.0.8 the architecture depends on, and the example configuration names paths from a different deployment when a host carries two. The rehearsal is logged in `RESTORE.md`, which is what awards the first `ops-proven`. | The repository sits on the same machine — the off-site target is written, not demonstrated. The timer stays off until a monitor exists to notice a failed run |
| 2026-07-29 | Session | `core/crowdsec` Phase 1 on a running host | Healthy in about twenty seconds, six collections active, a scenario firing on the first traffic it saw. **The number worth keeping is the other one**: 120 requests aimed at a host behind `acc-tailscale` moved the acquisition counter by 3, because `ipAllowList` rejects a request before the access log is written. The two layers take turns rather than add up — where the allowlist holds, CrowdSec is blind. | — |
| 2026-07-30 | Docs | Operator site becomes SecDockBlue | The site now carries an eleven-page security section that stands without these compose files, ordered along the chain a request passes through, each page stating what the layer does *not* stop. Added sources with citations, an application catalogue limited to what the repository has checked, and the legal, privacy and accessibility pages. A content gate (`site/scripts/check-content.mjs`) fails the build on dangerous or unpinned commands and on links that do not resolve, because this site tells people to paste commands into a root shell. | Publication still gated by its milestone — no deploy job |
| 2026-07-30 | Standards | Document purpose, and a prose register gate | `documentation-workflow.md` gained the level above the writing rules: nothing had decided whether a paragraph *belonged* where it stood. Preflight, section contracts, six ownership modes, and a six-question relevance test. `scripts/ci/check-prose.py` matches on prose units rather than lines — four findings were hiding across a line wrap, one on a customer-facing page. | Fourteen findings remain, all in records whose subject is how something was established |
| 2026-07-31 | Standards | What `apps/` and `business/` send outward | 29 stacks read from documentation and source, every positive re-checked by a pass whose job was to refute it — one claim did not survive. Six carry a persistent installation identifier; **two documented off switches do not work and neither project says so** (Lychee, Dashy). Telemetry switched off in the four stacks that accept a variable for it, with the cost written beside the two where there is one. `scripts/ops/egress-probe.sh` makes the wire observable — DNS plus dropped packets, forwarding rather than blackholing so the stack keeps making the calls worth seeing. | UniFi unestablished rather than clean — closed source, vendor documentation does not settle it |
| 2026-07-31 | Session | First wire test — Invoice Ninja | An hour of outbound DNS: 20 calls to Sentry against 5 to the PDF service. Reading the source had found both and led with the version check; on the wire the ranking and the significance are the other way round. Sentry carries stack traces, breadcrumbs and an id keyed to the account, so the reports identify the installation across restarts. `SENTRY_LARAVEL_DSN` emptied. | The point of running a wire test rather than only reading — the other 28 stacks have been read, not watched |
| 2026-07-31 | Session | Release v0.7.0 | CHANGELOG `[Unreleased]` → `[0.7.0]`, with the work from 2026-07-29 onward written up — it had not been recorded. ROADMAP: v0.7.0 section removed, the backup remainder moved to where it belongs. `.ai/state.md`, `tasks.md`, `progress.md`, `risks.md` moved to v0.8.0. README badge bumped. Git tag + GitHub Release. | — |
| 2026-08-03 | Session | Site publication and fork safety | Site live and every document that named a future date corrected. `security.txt` added under `.well-known/`, which needed `.nojekyll` and an upload that stops filtering dot paths before GitHub Pages would serve it. Privacy page names every company handling a request. Content licence decided as CC BY-NC 4.0. ROADMAP gained the direction for the personal data a fork would inherit: one data module, placeholders committed, the real values in a gitignored override decrypted from `age`. | The Session Chain was not run for this session — `[Unreleased]`, this row and `.ai/state.md` were written on 2026-08-16 |
| 2026-08-16 | Standards | Resource-limit ownership, port literal, egress | The resource block was defined in two standards with two value tables that disagreed on CPU limits. Split by kind: `security-baseline.md` owns controls that are on or off, `compose-structure.md` owns anything carrying a number. `cpus` is not part of the baseline — it bounds neither of the two failures that take a host down, and the sentence claiming otherwise went with the table. 23 surviving `cpus` values marked as derived so v0.9.0 can find them. `${APP_INTERNAL_PORT}` removed from 39 compose files and 40 `.env.example` — the standard had always said literal. `business/openproject` and `business/vikunja` had a network named `internal` that was a plain bridge. | OpenProject mail from `worker` unverified after the isolation — in `.ai/tasks.md` |
