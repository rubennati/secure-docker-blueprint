# Coherence Check — 2026-04-16

First comprehensive self-audit of the repository: does it follow its own standards? Are documents consistent with each other? Are there broken cross-references?

## Audit Summary

| Dimension | Findings | Severity Mix |
|-----------|----------|--------------|
| Standards Compliance | 14 services audited | 3 critical, 8 high, 6 medium |
| Documentation Completeness | 19 services audited | 7 critical, 10 high |
| Cross-Reference Consistency | Repo-wide | 3 critical, 2 high, 1 medium |
| Self-Contradictions | All standards cross-checked | 2 critical, 4 high, 3 medium |

**Total action items:** 32, grouped into 7 work packages.

**Estimated resolution effort:** 8–12 hours of focused work, spread across several phased commits.

## Methodology

- Standards in `docs/standards/*.md` treated as the source of truth
- Each app in `apps/*` and core service in `core/*` checked against all relevant standards
- Cross-references between documents verified file by file
- Agent reports were used as input but verified manually before inclusion — false findings filtered out

Three auto-reported findings turned out incorrect and were excluded:

- "Traefik security config files missing" — actually present as `.tmpl` templates in `ops/templates/dynamic/`
- "WordPress `uploads.ini` missing" — present at `config/php/uploads.ini`
- "WordPress `.htaccess-security` missing" — present at `config/apache/.htaccess-security`

## 1. Standards Compliance Issues

### 1.1 Service naming violations (HIGH)

Standard (`naming-conventions.md`): service names should be `app`, `db`, `redis`, `nginx` — short and generic.

Services using `database` instead of `db`:

- `apps/calcom`
- `apps/ghost`
- `apps/paperless-ngx`

**Impact:** Inconsistent naming across apps. New contributors copy from these apps and propagate the wrong name.

**Fix:** Rename service `database` → `db` in each of these three compose files. Update every reference in the same file (e.g. `depends_on`, healthcheck connection strings if present).

### 1.2 Secrets folder path violations (HIGH)

Standard (`naming-conventions.md`, `security-baseline.md`): secret files belong in `.secrets/` (hidden dotfolder, gitignored).

Compose files pointing at `./secrets/` (without dot):

- `apps/calcom`
- `apps/dockhand`
- `apps/ghost`
- `apps/paperless-ngx`
- `core/authentik`
- `core/onlyoffice`

**Impact:** Six services use a path that is not part of `.gitignore` coverage. If someone creates files in `secrets/` by mistake, they could be committed.

**Fix:** Change `file: ./secrets/<name>` to `file: ./.secrets/<name>` in each compose file. Update the app's `.env.example` secret-generation instructions accordingly. Delete any empty `secrets/` folders and create the `.secrets/` convention going forward.

### 1.3 Invoice Ninja compose is non-compliant (CRITICAL)

Multiple violations in a single file:

- Missing `security_opt: no-new-privileges:true` on all services
- Uses `env_file: ./.env` instead of explicit `environment:` block
- Plaintext database password in `environment:` (should be Docker Secrets)
- Network named `internal` instead of `${COMPOSE_PROJECT_NAME}-internal`
- Network named `proxy` instead of `proxy-public`
- Missing healthchecks on `app` and `nginx` services
- No container names via `${CONTAINER_NAME_*}` variables

**Impact:** This app is the most standards-divergent in the repo. A contributor reading this file could conclude the standards are "optional".

**Context:** Invoice Ninja was ported from the upstream `invoiceninja/dockerfiles` repo as-is (Stage 0 principle: minimal adaptation). The migration to full standards was deferred.

**Fix:** Requires significant rework. Either:

- Migrate to full standards compliance (estimated 2–3 hours)
- OR document as an explicit exception in `apps/invoiceninja/README.md` with clear justification for each deviation

### 1.4 Vaultwarden custom middleware and password handling (CRITICAL)

Two issues in one app:

1. **Password in environment variable:** `DATABASE_URL: mysql://${DB_USER}:${DB_PASSWORD}@db:3306/${DB_NAME}` embeds the password directly into an env var, violating `security-baseline.md` rule "passwords never in `environment:`".
2. **Custom Traefik middleware instead of `sec-*e`:** Vaultwarden uses inline Docker-level headers middleware rather than the `sec-3e` chain that `traefik-security.md` recommends.

**Context:** Both are explicitly documented as known limitations:

- The `.env.example` has a `TODO: Switch to sec-3e after testing` comment
- The compose file has an inline comment about header conflicts
- These predate the `sec-*e` embed variants being added to `traefik-security.md`

**Impact:** The standards say one thing, the implementation does another. A reader either assumes the standards are wrong or that the app is broken — neither is true.

**Fix:**

1. Add a custom entrypoint wrapper to Vaultwarden (pattern: `core/acme-certs`, `apps/dockhand`) that reads the password from `/run/secrets/DB_PWD` and exports `DATABASE_URL`
2. Test Vaultwarden with `sec-3e` chain — if compatible, switch and remove the custom middleware
3. If incompatible, update `traefik-security.md` to document Vaultwarden as an explicit exception with the conflict reason
4. Either way: move the TODO out of `.env.example` into `ROADMAP.md`

### 1.5 Service-specific issues (MEDIUM)

- `apps/hawser`: missing `restart: unless-stopped`, missing `security_opt`, missing networks — fundamental compose structure issues
- `core/crowdsec`: port exposition on `127.0.0.1:8080` without documented reason
- `core/acme-certs`: no networks defined

Each requires a small fix in the respective compose file.

## 2. Documentation Completeness Issues

### 2.1 Apps missing `README.md` (HIGH)

Required by `new-app-checklist.md` for every app. Missing in:

- `apps/calcom`
- `apps/dockhand`
- `apps/ghost`
- `apps/nextcloud`
- `apps/paperless-ngx`
- `apps/portainer`
- `apps/seafile`

**Impact:** A user landing in `apps/calcom/` sees only `docker-compose.yml` and `.env.example`. No idea how to set up or verify the service.

**Fix:** Create a `README.md` for each of the seven apps using the template from `apps/wordpress/README.md` (or `apps/vaultwarden/README.md`).

### 2.2 Apps missing `UPSTREAM.md` (HIGH)

Required by `new-app-checklist.md`. Missing in:

- `apps/calcom`
- `apps/dockhand`
- `apps/ghost`
- `apps/paperless-ngx`
- `apps/portainer`
- `apps/seafile`

**Impact:** Upgrade path for these apps is undocumented. Breaking changes between versions go unnoticed.

**Fix:** Create `UPSTREAM.md` using the template from `apps/vaultwarden/UPSTREAM.md`. Minimum content: Source, Based on version, Last checked, Changes made with reasons, Upgrade checklist.

### 2.3 Apps missing `.gitignore` (MEDIUM)

Should contain `.secrets/`, `volumes/`, `.env`. Missing in:

- `apps/calcom`
- `apps/dockhand`
- `apps/ghost`
- `apps/paperless-ngx`
- `apps/portainer`
- `apps/seafile`

**Impact:** Root `.gitignore` does cover these patterns globally, so the risk is low. But per-app `.gitignore` is the documented convention.

**Fix:** Add `.gitignore` with three lines to each affected app.

### 2.4 Core services missing documentation (HIGH)

Missing `README.md`:

- `core/authentik`
- `core/onlyoffice`
- `core/whoami`

Missing `UPSTREAM.md`:

- `core/authentik`
- `core/onlyoffice`
- `core/traefik`
- `core/whoami`

**Impact:** Core services are infrastructure — undocumented infrastructure is operational risk.

**Fix:** Create the missing files. Traefik's `README.md` is extensive and well-written; an `UPSTREAM.md` would be a small addition referencing the Traefik version and upgrade considerations.

### 2.5 Seafile CE is effectively undocumented (CRITICAL)

`apps/seafile/` contains a custom multi-file Compose setup (references external YAMLs via `COMPOSE_FILE`), but:

- No `README.md`
- No `UPSTREAM.md`
- No `docker-compose.yml` in a conventional single-file setup

**Impact:** Seafile CE is live-tested but entirely opaque to a new reader. Cannot be onboarded by following the repo alone.

**Fix:** Either:

- Document the multi-file setup explicitly (what files exist, how they interact)
- Or restructure into a single `docker-compose.yml` with optional overlays via `COMPOSE_FILE` (like `apps/paperless-ngx/sso.yml`)

## 3. Cross-Reference Consistency Issues

### 3.1 Apps missing from root `README.md` apps table (CRITICAL)

Apps on filesystem: 12.
Apps in root `README.md` apps table: 10.

Missing from the table:

- `apps/nextcloud`
- `apps/seafile-pro`

Both exist and are tested. Nextcloud even has a full `README.md`. Seafile Pro has both `README.md` and `UPSTREAM.md`.

**Impact:** Direct violation of the "Live Document" rule in `documentation-workflow.md`. New users won't know these apps exist.

**Fix:** Add both rows to the apps table in the root `README.md` with a brief description.

### 3.2 `new-app-checklist.md` references a non-existent path (CRITICAL)

`new-app-checklist.md` line 51 says:

```bash
cp -r apps/_template apps/my-app
```

But `apps/_template/` does not exist. The actual template is at `docs/templates/`.

**Impact:** Users following this checklist hit an immediate error. The first thing the guide tells them to do fails.

**Fix:** Change the reference to `cp -r docs/templates apps/my-app` (or, equivalently, create a symlink `apps/_template → ../docs/templates/`).

### 3.3 `docs/public-go-live-guide.md` referenced from `ROADMAP.md` but doesn't exist in main (HIGH)

`ROADMAP.md` § Planned Community Infrastructure says:

> These are GitHub-repo-level additions, not code changes. Tracked in `docs/public-go-live-guide.md` (private).

The file exists on the `docs` branch, not in `main`. Public readers of `main`'s ROADMAP see a reference to a file they cannot find.

**Impact:** Public confusion. "Private" is not a term that makes sense on a single-branch view.

**Fix:** Remove the reference to `public-go-live-guide.md` from `ROADMAP.md`, or phrase the ROADMAP entry without referring to a nonexistent file.

### 3.4 Docs-branch files referenced from main-branch standards (MEDIUM)

The memory files under `/Users/rb3nt/.claude/projects/...` are occasionally mentioned in standards. These are AI-assistant local state, not repository files. They should never be linked from public documentation.

Verified: none of the current `docs/standards/*.md` in `main` reference memory files. The `docs` branch does reference them, which is acceptable since that branch is private.

**No action needed** — but worth documenting the rule explicitly in `documentation-workflow.md`: "Public files must not reference non-repo paths."

## 4. Self-Contradictions

### 4.1 Vaultwarden standard vs. implementation (CRITICAL — duplicate of 1.4)

Already covered in section 1.4. Cross-listed here because it is also a cross-document inconsistency.

### 4.2 `commit-rules.md` and `documentation-workflow.md` have one-way references (MEDIUM)

`documentation-workflow.md` references `commit-rules.md` three times.
`commit-rules.md` does not reference `documentation-workflow.md`.

The two standards cover overlapping process concerns (commits, doc updates per commit). They should be mutually linked so a reader of either can find the other.

**Fix:** Add a "Related Standards" section to `commit-rules.md` with a link to `documentation-workflow.md`.

### 4.3 Traefik middleware provider suffix (`@file` vs `@docker`) not in `traefik-labels.md` (HIGH)

The rule about `@file` for file-provider middlewares and `@docker` for Docker-label middlewares is critical for routing to work. It is documented only in `troubleshooting.md`.

**Impact:** New contributors configuring a Traefik router often omit the suffix or pick the wrong one, resulting in 403 errors that are hard to diagnose without reading the troubleshooting guide.

**Fix:** Add a "Provider Suffixes" section to `traefik-labels.md` with clear rules and examples. Keep `troubleshooting.md` as the diagnostic reference.

### 4.4 Secret generation: `-hex` vs `-base64` (HIGH)

`env-structure.md` recommends `openssl rand -base64 32 | tr -d '\n'` for all secrets.

But base64 output can contain `+`, `/`, `=` which break URL-embedded passwords (e.g. `DATABASE_URL=mysql://...`). Hex output is URL-safe.

**Impact:** Following the standard literally produces passwords that break some apps.

**Fix:** Update `env-structure.md` to differentiate:

- Hex for URL-embedded passwords (DB connection strings, Redis URLs)
- Base64 for other secrets (API keys, tokens)

### 4.5 Template `docs/templates/docker-compose.yml` uses non-standard names (MEDIUM)

The template example uses `database` as service name and `DB_MYSQL_DATABASE`, `DB_MYSQL_USER` as variable names — both violate `naming-conventions.md`.

**Impact:** Anyone copying the template inherits non-compliant patterns.

**Fix:** Update the template to use `db`, `DB_NAME`, `DB_USER` consistently.

### 4.6 ROADMAP.md accuracy (MEDIUM)

Spot check shows:

- "Completed — Traefik Security Middleware Refactoring" ✅ Verified (templates exist)
- "Completed — WordPress Hardening" ✅ Verified (uploads.ini, .htaccess-security, mu-plugin all present)
- "Completed — CrowdSec Phase 1+2" ✅ Phase 1 live, Phase 2 prepared (not yet active)

The ROADMAP is accurate for the items checked. No falsely-marked completions found.

### 4.7 `security-baseline.md` ambiguity for images requiring privilege escalation (LOW)

The standard says `no-new-privileges: true` is mandatory. It does not say what to do if an image cannot start under this constraint. In practice: no such image is currently used, so the ambiguity has no effect.

**Fix (optional):** Clarify in `security-baseline.md` that images incompatible with `no-new-privileges: true` are disqualified from the blueprint.

## Action Plan

Grouped into work packages. Each package is a single commit on `dev`. Order is by dependency and priority.

### Package 1 — Path and Naming Fixes (CRITICAL + HIGH, ~1 hour)

Atomic fix for three related issues:

- Fix `new-app-checklist.md` to reference `docs/templates` instead of `apps/_template`
- Add `nextcloud` and `seafile-pro` to root `README.md` apps table
- Remove `docs/public-go-live-guide.md` reference from `ROADMAP.md`

**Commit scope:** `docs: fix broken cross-references`

### Package 2 — Secrets Folder Standardization (HIGH, ~30 minutes)

Six services use `./secrets/` instead of `./.secrets/`. Fix in one atomic commit:

- `apps/calcom`, `apps/dockhand`, `apps/ghost`, `apps/paperless-ngx`
- `core/authentik`, `core/onlyoffice`

Update compose files + .env.example secret generation instructions.

**Commit scope:** `standardize secrets folder path to .secrets/`

### Package 3 — Service Naming Consistency (HIGH, ~30 minutes)

Three services use `database` instead of `db`:

- `apps/calcom`, `apps/ghost`, `apps/paperless-ngx`

Rename service, update `depends_on` references, update any internal connection strings.

**Commit scope:** `standardize service name to db`

### Package 4 — Template Corrections (MEDIUM, ~20 minutes)

Fix the template itself so new apps start compliant:

- Rename `database` → `db` in `docs/templates/docker-compose.yml`
- Update variable names to `DB_NAME`, `DB_USER` (drop `_MYSQL_` infix)
- Consistency check against final standards

**Commit scope:** `docs/templates: align with naming conventions`

### Package 5 — Standards Clarifications (MEDIUM, ~1 hour)

Three targeted additions to existing standards:

- `traefik-labels.md`: add "Provider Suffixes" section (`@file` vs `@docker`)
- `env-structure.md`: differentiate `-hex` vs `-base64` by use case
- `commit-rules.md`: add cross-reference to `documentation-workflow.md`

**Commit scope:** `docs/standards: clarify traefik suffixes, secret generation, cross-refs`

### Package 6 — Missing Per-App Documentation (HIGH, ~4–6 hours)

Large package. Create missing files for 10 services:

**Apps (7 READMEs, 6 UPSTREAMs, 6 .gitignore):**

- `calcom`, `dockhand`, `ghost`, `nextcloud`, `paperless-ngx`, `portainer`, `seafile`

**Core (3 READMEs, 4 UPSTREAMs):**

- `authentik`, `onlyoffice`, `whoami`, `traefik` (only UPSTREAM needed)

**Strategy:** use `apps/wordpress` and `apps/vaultwarden` as README templates; use `apps/vaultwarden/UPSTREAM.md` as UPSTREAM template.

**Commit scope:** could be split by app-group or done as one large "documentation sweep" commit.

### Package 7 — App Compose Fixes (CRITICAL + HIGH, ~2 hours)

Three apps need compose-level fixes:

- `apps/invoiceninja`: either migrate to standards or add explicit exception documentation with per-deviation justification
- `apps/vaultwarden`: add entrypoint wrapper for DB_PASSWORD secret handling; retest with `sec-3e`; update README + traefik-security.md accordingly
- `apps/hawser`: add `restart`, `security_opt`, networks; verify standards compliance

**Commit scope:** one commit per app, since each is a distinct scope.

## Prioritization

Suggested execution order:

1. Package 1 (cross-references) — fastest, unblocks navigation
2. Package 2 (secrets folder) — largest blast radius, low risk
3. Package 3 (service names) — cascading in compose, medium risk
4. Package 4 (template) — prevents future issues
5. Package 5 (standards clarifications) — low risk, high clarity value
6. Package 6 (documentation) — largest effort, low technical risk
7. Package 7 (compose fixes) — highest technical risk, last

## Follow-up

After resolving these packages, rerun this audit to confirm. The audit methodology should be formalized in a script (`ops/scripts/audit.sh`) so it can be rerun cheaply. That is a separate improvement to consider.

## Appendix: What Is Already Working Well

Not to lose sight of what's fine:

- Root `README.md` structure and coverage: strong
- `LICENSE`, `SECURITY.md`, `ROADMAP.md`: present and useful
- Standards documents exist, are well-organized, mostly consistent
- Bugfix docs follow a consistent Symptom/Root Cause/Fix/Lesson format
- `docs/standards/commit-rules.md` and `documentation-workflow.md`: thoughtful, actionable
- `apps/wordpress`, `apps/vaultwarden`, `core/traefik`, `core/crowdsec`, `core/dnsmasq`: exemplary documentation quality
- Branch model (`main` + `dev` + `docs` orphan): sound

The audit reveals gaps, not rot. Most findings are consistency issues that naturally accumulate as a project evolves faster than its documentation.
