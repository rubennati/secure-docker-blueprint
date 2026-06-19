# Security Verification

> This document is an evidence-based assessment of the security controls in this repository.
> It does not repeat marketing claims. Every statement is backed by a specific file, line, or CI output.
> Gaps are documented honestly.

---

## Security Philosophy

This repository aims for **reasonable, enforced defaults** for self-hosted Docker Compose infrastructure targeting homelab and small-team production environments. The goal is not military-grade hardening; it is making common misconfigurations impossible to accidentally introduce and documenting every deliberate exception.

The control model has three tiers:

| Tier | Description | Enforcement |
|------|-------------|------------|
| **Hard** | Controls that block CI if violated | `scripts/ci/check-baseline.py` |
| **Soft** | Controls documented as recommended, not CI-enforced | `docs/standards/security-baseline.md` |
| **Optional** | Controls available but not applied by default | Per-service configuration |

---

## Implemented Controls

### CI-Enforced (Hard Controls)

These controls block merges if violated. Evidence is the CI output from `.github/workflows/ci.yml`.

#### 1. `no-new-privileges:true`

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — `scripts/ci/check-baseline.py` |
| **Coverage** | 50 / 50 compose files |
| **Location** | Every `docker-compose.yml` under `core/`, `apps/`, `business/`, `monitoring/` |
| **Verification** | `python3 scripts/ci/check-baseline.py` — exits 1 if any service is missing the flag |
| **Exceptions** | 2 services documented with `reason` / `alternatives` / `risk acceptance` fields: `apps/nextcloud` app + cron (s6-overlay requires root at startup) |
| **Gaps** | None — exceptions are structurally enforced in the Python script |

#### 2. `privileged: true` forbidden

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — `scripts/ci/check-baseline.py` |
| **Coverage** | 0 violations across 50 compose files |
| **Verification** | `grep -r "privileged: true" --include="docker-compose.yml"` returns nothing |
| **Gaps** | No exception path exists — `privileged: true` is always a hard failure with no allowlist |

#### 3. Docker socket access via proxy only

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — `scripts/ci/check-baseline.py` |
| **Location** | Socket proxies defined in `core/traefik`, `core/portainer`, `core/dockhand`, `core/hawser`, `core/portainer-agent`, `monitoring/beszel`, `monitoring/beszel-agent` |
| **Pattern** | `tecnativa/docker-socket-proxy` with per-service API surface allowlists |
| **Exceptions** | 7 services have documented exceptions, all in `SOCKET_EXCEPTIONS` dict with mandatory `reason` / `alternatives` / `risk` fields |
| **Gaps** | Hawser is a known exception pending upstream support for TCP socket proxy (tracked: `https://github.com/Finsys/hawser/pull/52`). Beszel agent mounts socket read-only (`:ro`) which limits but does not eliminate risk. |

#### 4. Image tag pinning — no `:latest`

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — structure check in `.github/workflows/ci.yml` |
| **Coverage** | 0 violations. The one `:latest` occurrence in the repo is in a comment (`monitoring/changedetection/docker-compose.yml:61`) |
| **Verification** | `grep -rP '^\s+image:\s+\S+:latest' --include="docker-compose.yml"` |
| **Gaps** | Tags are pinned to version strings but are **not pinned to digest** (`image: name@sha256:...`). A version tag can be overwritten by an upstream registy push without detection. |

#### 5. Secret scanning (gitleaks)

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — `gitleaks/gitleaks-action@v2` |
| **Scope** | Full git history (`fetch-depth: 0`) on every push and nightly |
| **Configuration** | `.gitleaks.toml` — one allowlisted historical commit (`cdb795e`, documented example key in Traefik README, not a real credential) |
| **Gaps** | No custom rules for project-specific secret patterns (e.g. Cloudflare tokens, Tailscale auth keys) beyond gitleaks defaults |

#### 6. Compose syntax validation

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — `docker compose config --quiet` on all 50 compose files |
| **Scope** | All compose files in `core/`, `apps/`, `business/`, `monitoring/` |
| **Method** | Each compose file is tested with its `.env.example` substituted as `.env` |
| **Gaps** | Validates YAML syntax and compose schema, but does not catch semantic errors (e.g. a volume referencing a path that will not exist at runtime) |

#### 7. README and `.env.example` presence

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Enforcement** | CI FAIL — structure check |
| **Coverage** | Every directory containing a `docker-compose.yml` must have both `README.md` and `.env.example` |
| **Gaps** | Does not validate content — a minimal or incorrect README passes |

---

### Traefik-Enforced Controls

These controls are enforced by Traefik configuration rendered from templates in `core/traefik/ops/templates/`. They apply to all traffic that passes through the reverse proxy.

#### 8. HTTPS-only + HTTP redirect

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/traefik.yml.tmpl` lines 28–33 |
| **Evidence** | `entryPoints.web.http.redirections.entryPoint.to: websecure` — HTTP → HTTPS permanent redirect |
| **Gaps** | Redirect is global but applies only to traffic that reaches Traefik. Services not registered in Traefik are not covered. |

#### 9. TLS minimum version enforcement

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/dynamic/tls-profiles.yml.tmpl` |
| **Profiles** | `tls-basic` (TLS 1.2+, sniStrict), `tls-aplus` (TLS 1.2+, forward-secrecy-only ciphers, X25519 preferred), `tls-modern` (TLS 1.3 only, sniStrict) |
| **Default** | Set via `TLS_DEFAULT_OPTION` in `.env`, applied globally via `websecure.http.tls.options` |
| **Gaps** | TLS profile is documentation-recommended per app but not machine-verified. No CI check confirms a given app uses an appropriate profile. |

#### 10. Security headers

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/dynamic/security-blocks.yml.tmpl` |
| **Headers enforced** | HSTS (63072000s = 2yr), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or SAMEORIGIN in embed variants), Referrer-Policy, Permissions-Policy (camera, mic, geolocation, payment, USB, gyroscope disabled), CSP (report-only in sec-3, enforcing in sec-5), `Vary` |
| **Removed** | `X-XSS-Protection` — removed intentionally, documented rationale: deprecated, Chrome removed XSS Auditor in 2019 |
| **Gaps** | CSP is `report-only` in sec-3 (the most common level). Enforcing CSP is only in sec-5 (`Whoami` is the only app at this level). Most apps run with a permissive CSP. |

#### 11. Rate limiting

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/dynamic/security-blocks.yml.tmpl` |
| **Limits** | `rl-soft`: 100 avg / 50 burst. `rl-hard`: 20 avg / 40 burst. `rl-spa`: 100 avg / 200 burst (for SPA initial load) |
| **Applied from** | sec-2 (soft) / sec-4 (hard) |
| **Gaps** | Rate limits are per-IP at the Traefik level. No distributed rate limiting. Behind a CDN or NAT, all users share one bucket. |

#### 12. Network access policies

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/dynamic/access.yml.tmpl` |
| **Policies** | `acc-public`, `acc-local` (RFC1918 + ULA hardcoded), `acc-tailscale` (CIDR from .env), `acc-private` (LAN + VPN), `acc-deny` (nobody) |
| **Gaps** | `forwardedHeaders.trustedIPs` (Cloudflare's published IP ranges) is now configured in `traefik.yml.tmpl`, closing the X-Forwarded-For spoofing gap for the Cloudflare path. Not CI-verified per deployment — a custom edit could still misconfigure it, and nothing checks that the hardcoded ranges stay in sync with Cloudflare's published list over time. Separately, the Tailscale path recovers the real client IP at the network layer (direct connection, no header involved) — this only works end to end if `proxy-public` is dual-stack, which is opt-in (`core/traefik/network-dual-stack.yml`), not the default. An IPv4-only deployment with Tailscale IPv6 clients loses the real client IP for `ipAllowList` purposes (`ClientHost` shows the Docker gateway address) until the operator opts in. See `core/traefik/docs/ipv6-dual-stack.md` and `docs/bugfixes/traefik-ipv6-dualstack-2026-06-19.md`. |

#### 13. `exposedByDefault: false`

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `core/traefik/ops/templates/traefik.yml.tmpl` line 49 |
| **Effect** | Containers must opt in to Traefik routing via `traefik.enable=true` label. No accidental service exposure. |

#### 14. Traefik dashboard requires auth

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Evidence** | `api.insecure: false` in `traefik.yml.tmpl`. Dashboard is routed via `acc-tailscale + sec-4` per `docs/standards/traefik-security.md` |
| **Gaps** | Not CI-verified that the dashboard router is actually configured with the correct middleware. A misconfigured `.env` could expose the dashboard publicly. |

---

### Repository-Structure Controls

#### 15. Secrets excluded from git

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Location** | `.gitignore` |
| **Patterns** | `**/.env`, `**/secrets/`, `**/volumes/`, `**/logs/`, `**/acme.json` |
| **Evidence** | `.env.example` is committed; `.env` is not. Secret files go under `.secrets/` which matches `**/secrets/` |
| **Gaps** | `.gitignore` prevents accidental commits but does not prevent a user from forcibly adding files or checking out on a system without `.gitignore` enforcement. The CI gitleaks scan is the backstop. |

#### 16. Network isolation (database networks)

| Field | Value |
|-------|-------|
| **Implemented?** | Yes |
| **Coverage** | 27 / 50 compose files use `internal: true` networks |
| **Pattern** | Database and internal services on `app-internal` (internal: true). Web services on `proxy-public` + `app-internal`. No database ports exposed on host. |
| **Gaps** | Not CI-enforced. Nothing prevents a developer from adding a database to `proxy-public`. Several apps intentionally do NOT mark `app-internal` as internal (e.g. Nextcloud — documented in README). |

#### 17. `__REPLACE_ME__` sentinel values

| Field | Value |
|-------|-------|
| **Implemented?** | Partially |
| **Coverage** | 50 occurrences of `__REPLACE_ME__` across `.env.example` files |
| **Purpose** | Force the deployer to set required values before first run |
| **Gaps** | CI does **not** check that `__REPLACE_ME__` is absent at runtime. A user can copy `.env.example` to `.env` without substitution and start containers with sentinel values. The Traefik `validate.sh` script checks for this locally but it is not run in CI. |

---

### Soft Controls (Documented, Not CI-Enforced)

These are in `docs/standards/security-baseline.md` and applied inconsistently across the repository.

| Control | Coverage | Standard Location | CI-Enforced? |
|---------|----------|------------------|-------------|
| `read_only: true` | ~14 / 50 compose files | `docs/standards/security-baseline.md` | No |
| `cap_drop: ALL` | ~10 / 50 compose files | `docs/standards/security-baseline.md` | No |
| Non-root `user:` | 1 / 50 compose files | `docs/standards/security-baseline.md` | No |
| Resource limits (`deploy.resources`) | 3 / 50 compose files | `docs/standards/security-baseline.md` | No |
| Config mounts with `:ro` | Inconsistent | `docs/standards/security-baseline.md` | No |
| Docker Secrets (no raw passwords in `environment:`) | 30 / 50 compose files | `docs/standards/security-baseline.md` | No |

The soft controls are well-documented but application is inconsistent. `read_only` and `cap_drop` appear to be applied only when the developer remembered to do so, not systematically.

**Notable pattern: Redis password in `.env`**
Several apps (Nextcloud) pass `REDIS_PASSWORD` via `.env` rather than Docker Secrets. This is documented as intentional — Redis `--requirepass` cannot use `_FILE` format. The password is in a gitignored file, but it is not isolated the way Docker Secrets are (in `/run/secrets/` with kernel-level access control).

---

## CIS Docker Benchmark Mapping

Based on **CIS Docker Benchmark v1.6.0**.

| CIS Control | Status | Evidence | Notes |
|-------------|--------|----------|-------|
| **4.1** Create user for container | ⚠ Partial | `user:` in 1/50 files; `no-new-privileges` in 50/50 | Most containers run as image-defined users. No systematic non-root enforcement. |
| **4.2** Use trusted base images | ⚠ Partial | Well-known registries (ghcr.io, docker.io). No image signing or digest pinning. | Tags pinned but not digests. No provenance verification. |
| **4.3** Do not install unnecessary packages | ℹ N/A | Not applicable to compose blueprint — image content is upstream responsibility | |
| **4.4** Scan images for vulnerabilities | ⚠ Partial | `trivy.yml` scans ~11 high-risk images for CRITICAL/HIGH CVEs; IaC config scan covers all compose files | Not exhaustive — ~40 compose files not image-scanned; see Missing Verification |
| **4.5** Enable Content Trust | ❌ Not implemented | No `DOCKER_CONTENT_TRUST=1`, no cosign verification | |
| **4.6** Add HEALTHCHECK | ✅ Partial | Most compose files include healthchecks. Some scratch images correctly use `disable: true` | |
| **4.7** Do not use update in Dockerfile | ℹ N/A | No Dockerfiles in this repository | |
| **4.9** Use COPY not ADD | ℹ N/A | No Dockerfiles | |
| **5.1** AppArmor profile | ❌ Not implemented | No `--security-opt apparmor:` in any compose file | |
| **5.2** SELinux options | ❌ Not implemented | No `--security-opt label:` in any compose file | |
| **5.3** Capabilities (cap_drop) | ⚠ Partial | Applied in ~10/50 compose files | `cap_drop: ALL` documented as recommended, not enforced |
| **5.4** Privileged containers | ✅ Enforced | CI FAIL — `scripts/ci/check-baseline.py` | Zero violations |
| **5.5** Sensitive host paths | ✅ Enforced | Docker socket via proxy only — CI FAIL for direct mounts | Documented exceptions |
| **5.6** SSH in containers | ✅ Not present | No SSH daemon in any service | |
| **5.7** Privileged ports | ✅ Not needed | Traefik handles port binding; app containers use internal ports | |
| **5.8** Open ports | ✅ Minimal | Only Traefik 80/443 exposed. No DB port exposure on host. | |
| **5.9** Shared host network | ⚠ Documented | `network_mode: host` in 2 services (dnsmasq, Beszel agent) — documented exceptions | |
| **5.10** Memory limits | ❌ Partial | Resource limits in 3/50 compose files | Documented as recommended, rarely applied |
| **5.11** CPU limits | ❌ Partial | Same as memory limits | |
| **5.12** Read-only root FS | ⚠ Partial | Applied in ~14/50 compose files | Not CI-enforced |
| **5.14** Bind only to required interfaces | ✅ Yes | `ping` entryPoint bound to `127.0.0.1:8082` | |
| **5.15** `docker.sock` mount | ✅ Enforced | CI FAIL — socket proxy pattern enforced | Documented exceptions with risk acceptance |
| **5.25** Restart policy | ✅ Yes | All services use `restart: unless-stopped` | |
| **5.28** PIDs limit | ❌ Partial | Only in 3 files with `deploy.resources` | |

---

## OWASP Docker Security Mapping

Based on **OWASP Docker Security Cheat Sheet**.

| OWASP Recommendation | Status | Evidence | Notes |
|---------------------|--------|----------|-------|
| Use official base images | ✅ Yes | All images from official registries (docker.io, ghcr.io, quay.io) | |
| Use specific image tags | ✅ Enforced | CI FAIL for `:latest` tags | Not pinned to digest |
| Do not store secrets in images | ✅ Yes | Docker Secrets pattern; `.gitignore` covers `.env` | Redis password exception documented |
| Use non-root users | ⚠ Partial | `no-new-privileges` enforced; explicit `user:` in 1 file only | |
| Use read-only filesystems | ⚠ Partial | ~14/50 files | Not systematically enforced |
| Drop capabilities | ⚠ Partial | ~10/50 files | |
| Disable inter-container communication | ✅ Yes | `internal: true` networks isolate DB tier | |
| Set resource limits | ❌ Partial | 3/50 files | Documented baseline, not applied |
| Use security profiles (AppArmor/SELinux) | ❌ No | None configured | Significant gap |
| Enable Docker Content Trust | ❌ No | Not configured | |
| Scan for vulnerabilities | ⚠ Partial | `trivy.yml` scans ~11 high-risk images for CVEs; IaC config scan covers all compose files | Not exhaustive — see Missing Verification section |
| Use Docker Bench for Security | ❌ No | Not in CI | |
| Log all container activities | ⚠ Partial | Traefik access log captures HTTP. No container-level audit logging. | |
| Monitor containers at runtime | ⚠ Optional | Beszel available for metrics. No behavioral anomaly detection. | |

---

## Automated Verification

### What is currently verified in CI

#### `ci.yml` — runs on push to `dev`/`main`, PRs to `main`, nightly 03:00 UTC

**Job 1: Secret scan (`gitleaks`)**
- Full git history scan with `fetch-depth: 0`
- Catches committed credentials, API keys, tokens
- Configured via `.gitleaks.toml` with one documented historical allowlist entry

**Job 2: Compose syntax validation**
- Runs `docker compose config --quiet` on all 50 compose files
- Substitutes `.env.example` as `.env` for validation
- Catches YAML errors and undefined variable references

**Job 3: Structure check**
- Verifies every compose directory has `README.md` and `.env.example`
- Checks for `:latest` image tags (regex match on uncommented `image:` lines)

**Job 4: Sentinel value check** *(added)*
- Finds any committed `.env` file (not `.env.example`) containing `__REPLACE_ME__`
- Prevents deployment of unsubstituted configuration values reaching the repository
- Does **not** cover runtime `.env` files that are gitignored — only committed files

**Job 5: Security baseline (`check-baseline.py`)**
- Parses all compose files as YAML
- Enforces: `no-new-privileges:true`, no `privileged: true`, no direct Docker socket mount
- Reports: `network_mode: host`, `pid: host`
- Exceptions are in-code with mandatory `reason` / `alternatives` / `risk` fields
- Generates GitHub Actions job summary with violation table and accepted exception table

---

#### `trivy.yml` — runs on push/PR to `main`, weekly Monday 04:00 UTC *(added)*

**Job 1: IaC misconfiguration scan**
- Scans all repository files with `trivy config`
- Detects Compose and infrastructure misconfigurations
- Results uploaded to GitHub Security tab as SARIF
- Non-blocking (exit-code 0) — informational relative to `check-baseline.py`

**Job 2: Image CVE scan**
- Extracts image references from a curated list of ~11 high-risk compose files
  via `scripts/ci/list-images.sh` (uses `.env.example` + envsubst)
- Scans each image with Trivy for CRITICAL CVEs (`--ignore-unfixed`)
- Fails the job if any CRITICAL CVE is found
- Reports HIGH CVEs in logs as informational (non-blocking)
- Limitation: covers ~11 of 50 compose files; not all images are scanned

---

#### `scorecard.yml` — runs on push to `main`, weekly Monday 05:30 UTC *(added)*

**OpenSSF Scorecard**
- Evaluates supply chain security posture: branch protection, dependency review,
  pinned dependencies, code review, vulnerability disclosure, signed releases
- Results published to `https://api.securityscorecards.dev`
- Results uploaded to GitHub Security tab as SARIF
- Score is visible via badge in README

---

## Missing Verification

The following controls are absent from CI. Ordered by security value.

### Partially addressed by recent additions

| Gap | Status | Remaining limitation |
|-----|--------|----------------------|
| **CVE / vulnerability scanning** | ⚠ Partial — `trivy.yml` scans ~11 high-risk compose files | ~39 compose files not covered; image scanning is not exhaustive |
| **IaC static analysis** | ⚠ Partial — `trivy.yml` config scan runs but is non-blocking | Overlaps with `check-baseline.py`; Trivy config scan exit-code is 0 |
| **`__REPLACE_ME__` sentinel check** | ✅ Addressed — `ci.yml` sentinel job | Only covers committed `.env` files; runtime `.env` files are gitignored and unchecked |
| **OpenSSF Scorecard** | ✅ Addressed — `scorecard.yml` | Score is a posture signal, not a blocking control |

### Not implemented — still missing

| Gap | Description | Suggested Tool |
|-----|-------------|---------------|
| **Digest pinning** | Tags are pinned (no `:latest`) but not to digest. `name:1.2.3` can be overwritten upstream silently. | Renovate with digest pinning, or manual `@sha256:...` pins |
| **Image signing / provenance** | No verification that images come from the claimed publisher. | cosign, SLSA provenance, Sigstore |
| **SBOM generation** | No Software Bill of Materials. Unknown what packages are in running containers. | Syft, Trivy SBOM mode |
| **GitHub Actions pinning** | ✅ Addressed — all workflow actions pinned to commit SHA in Batch 1/2 (ci.yml, trivy.yml, scorecard.yml) | Dependabot (`github-actions` ecosystem) keeps pins current |
| **`read_only: true` coverage** | Applied in ~28% of compose files. No CI enforcement. | Extension to `check-baseline.py` |
| **`cap_drop` coverage** | Applied in ~20% of files. No CI enforcement. | Extension to `check-baseline.py` |
| **Resource limits coverage** | Applied in 6% of files. A compromised container can exhaust host memory. | Extension to `check-baseline.py` |
| **Dependency review** | No automated check for newly introduced vulnerable dependencies on PRs. | `dependency-review-action` |
| **Docker Bench for Security** | Runtime checks against host Docker daemon config. Not coverable in CI without host access. | Docker Bench for Security |
| **TLS profile enforcement** | No CI check that each app uses an appropriate TLS profile. | Extension to structure check |
| **Exhaustive image scanning** | Trivy covers ~11 of 50 compose files. Remaining ~39 files are unscanned. | Extend `scripts/ci/list-images.sh` |

---

## Maturity Assessment

### Documentation: 4 / 5

The documentation is detailed, accurate, and actively maintained. Security decisions are explained with rationale. Exceptions carry full justification. The `SECURITY.md` defines a responsible disclosure process. The only weakness is that soft-control documentation does not translate into enforcement.

### Security Baseline: 3 / 5

The hard controls (no-new-privileges, no privileged, socket proxy pattern, no `:latest`) are genuinely enforced and cover the most critical risks. The soft controls (read_only, cap_drop, resource limits, non-root user) are documented but inconsistently applied — coverage ranges from 6% to 28% of compose files. This is honest inconsistency rather than false coverage.

### Enforcement: 3 / 5

CI enforces 4 categories of controls that block merges on violation. The exception system is structured and well-designed. The weakness is the large gap between documented soft controls and actual enforcement. A developer can add a new service, get it past CI, and miss `read_only`, `cap_drop`, resource limits, and non-root user without any CI feedback.

### Verification: 3 / 5 *(updated)*

CVE scanning is now in place for a curated set of high-risk images via `trivy.yml`. OpenSSF Scorecard provides a supply chain posture signal. The sentinel value check closes a specific gap. The score moves from 2 to 3 because basic vulnerability visibility now exists. It is not 4 because image scanning is not exhaustive (~11/50 compose files), IaC scanning is non-blocking, and runtime security is still absent.

### Supply Chain Security: 2 / 5 *(updated)*

Tags are pinned. OpenSSF Scorecard now publishes a public score. Basic CVE scanning exists for high-risk images. The score moves from 1 to 2. It remains low because: no digest pinning, no image signing, no provenance verification, no SBOM, no dependency review, and GitHub Actions are still referenced by floating version tags (`@v2`, `@v6`) not commit SHAs.

---

## Prioritized Improvement Roadmap

### Priority 1 — High security value, low effort

These close the largest gaps with the least complexity. Implement before anything else.

| Item | What | Complexity | Maintenance | Security Value |
|------|------|-----------|-------------|----------------|
| **Trivy in CI** | Scan all images referenced in compose files for CVEs. Run on push, fail on CRITICAL. | Low — one new CI job | Low — automated | High — CVE visibility |
| **`__REPLACE_ME__` CI check** | Add step that fails if any `.env` file (not `.env.example`) contains `__REPLACE_ME__`. Catches deployment of unsubstituted configs. | Trivial — 3-line grep | None | Medium — prevents silent misconfigurations |
| **`read_only: true` CI enforcement** | Extend `check-baseline.py` to WARN (not FAIL initially) for services missing `read_only: true`. Add to exception system. | Low | Low | Medium |
| **GitHub Actions SHA pinning** | Pin `actions/checkout`, `gitleaks-action` etc. to commit SHAs instead of floating tags. | Trivial | Low (Renovate automates updates) | Medium — supply chain |
| **`cap_drop` CI check** | Extend `check-baseline.py` to WARN for services missing `cap_drop: [ALL]`. | Low | Low | Medium |

### Priority 2 — Significant verification improvement

These materially improve the "evidence vs. claims" ratio.

| Item | What | Complexity | Maintenance | Security Value |
|------|------|-----------|-------------|----------------|
| **Digest pinning for critical images** | Pin high-risk images (Traefik, Authentik, Vaultwarden, database images) to `@sha256:` in addition to version tag. | Medium — manual or Renovate | Medium — requires update process | High — prevents tag overwrite attacks |
| **Checkov scan** | Run Checkov against all compose files. Accept initial noise and build a suppression list. Catches resource limits, port exposure, missing healthchecks. | Medium — tune suppressions | Low once baseline established | High — broadens static coverage |
| **Resource limits CI enforcement** | Extend `check-baseline.py` to WARN for services missing `deploy.resources.limits`. Start with WARN, graduate to FAIL. | Low | Low | Medium — prevents resource exhaustion from compromised container |
| **OpenSSF Scorecard** | Add `ossf/scorecard-action` to CI. Scores the repository on branch protection, dependency review, code review, vulnerability disclosure, pinned dependencies. | Low — GitHub Action | None | Medium — public signal and internal audit |

### Priority 3 — Advanced controls

These require significant design decisions and ongoing commitment.

| Item | What | Complexity | Maintenance | Security Value |
|------|------|-----------|-------------|----------------|
| **SBOM generation** | Generate a Software Bill of Materials for each image on release. Enables downstream CVE tracking and compliance. | Medium — tooling (Syft + Grype) | Medium | High — compliance, supply chain |
| **Image signing (cosign)** | Sign images if this project builds any custom images. Verify signatures for third-party images that provide them. | High — requires key management | High | High — supply chain integrity |
| **AppArmor / Seccomp profiles** | Add default seccomp profile (`seccomp: unconfined` is often the unstated default). AppArmor requires host-side configuration. | High — host-dependent | High | High — kernel-level isolation |
| **Runtime anomaly detection** | Deploy Falco or similar to detect unexpected syscalls, file access, network connections at runtime. | High — infrastructure change | High | High — detects post-exploitation activity |
| **CIS Docker Benchmark (runtime)** | Run Docker Bench against the daemon configuration on each deployment host. Not automatable in CI — requires access to the host. | Low to run | Medium | Medium — catches daemon-level misconfigurations |

---

## Summary

**What this repository genuinely provides:**
- Enforced `no-new-privileges` on 100% of services (with documented exceptions)
- Enforced prohibition on `privileged: true`
- Enforced Docker socket proxy pattern for all management tools
- Enforced image version pinning (no `:latest`)
- Enforced git history secret scanning with full-history coverage
- Traefik-enforced HTTPS with configurable TLS profiles (1.2+, forward secrecy, 1.3-only)
- Traefik-enforced security headers on all routed services
- Traefik-enforced network access policies (VPN-only, LAN-only, public, deny)
- Structured exception system with mandatory justification fields
- Responsive disclosure policy

**What this repository does not provide:**
- Vulnerability scanning of any kind
- Image digest pinning or signing
- SBOM generation
- Runtime security monitoring
- Consistent application of soft controls (read_only, cap_drop, resource limits, non-root user)
- AppArmor / SELinux profiles
- CI verification that Redis passwords, inline secrets, or sentinel values are handled correctly at deployment time
