# Security Policy

This project is a **security-focused Docker Compose blueprint**. Security reports are taken seriously and handled responsibly.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report security issues privately using one of the following channels:

### Option 1: GitHub Private Security Advisory (preferred)

1. Go to the [Security tab](../../security) of this repository
2. Click **Report a vulnerability**
3. Fill in the private advisory form

This is the recommended way — it keeps the discussion private until a fix is released, and allows coordinated disclosure.

### Option 2: Email

If you cannot use GitHub Private Security Advisories, email the maintainer with:

- **Subject:** `[SECURITY] <short description>`
- **Details:** Steps to reproduce, impact assessment, affected components
- **Timeline:** How urgent is disclosure from your side

_Contact information is in the repository's public profile._

## What to Report

### In scope

- **Security misconfigurations in the blueprint itself** — e.g. a `docker-compose.yml` that exposes secrets, weak TLS defaults, missing `no-new-privileges`, unsafe Traefik middleware
- **Documentation that leads users to insecure setups** — e.g. a README snippet that recommends unsafe defaults
- **Secret leaks in git history** — if any real secrets, domains, or credentials ended up in the repository
- **Supply chain issues** — e.g. a pinned image version with known CVEs that should be updated

### Out of scope

- **Vulnerabilities in the upstream images** — report those to the respective upstream projects (e.g. CrowdSec, Traefik, Vaultwarden, Paperless-ngx)
- **Issues in user-specific deployments** — this blueprint is a starting point; your deployment's security depends on your configuration
- **Missing optional hardening** — if something could be more hardened but the default is still safe, open a regular issue or PR

If in doubt, report it privately anyway. Better safe than sorry.

## What to Expect

- **Acknowledgement** within 7 days of report
- **Assessment** within 14 days (severity, affected components, rough fix plan)
- **Fix or mitigation** timeline depends on severity:
  - Critical (e.g. secret leak, auth bypass): within 7 days
  - High: within 30 days
  - Medium/Low: next regular release

## Disclosure Policy

- **Coordinated disclosure preferred** — we fix first, disclose after
- **Public disclosure** after the fix is released, with credit to the reporter (if desired)
- **No bounty program** — this is a community blueprint, not a commercial product

## Scope & Limitations

This blueprint aims for **reasonable security defaults**, not military-grade hardening. It targets:

- Self-hosted infrastructure operators
- Homelab / SOHO deployments
- Small-team production systems

For **high-stakes production environments** (critical infrastructure, financial systems, healthcare), please have a security professional review the configuration before deployment.

## Security Principles This Blueprint Follows

- **Least privilege** — `cap_drop: ALL`, `no-new-privileges`, read-only filesystems where supported
- **Secret isolation** — Docker Secrets via `_FILE` env vars or entrypoint wrappers, never in `environment:`
- **Network segmentation** — databases and backends in internal networks, no internet exposure
- **Socket proxy pattern** — no direct Docker socket mounts on app containers
- **Pinned versions** — every image tagged with a specific version, never `:latest`
- **Defense in depth** — multiple layers (IP allowlist, security headers, rate limiting, WAF via CrowdSec AppSec)

See [`docs/standards/security-baseline.md`](docs/standards/security-baseline.md) for the full security baseline.

## Known Accepted Risks

- **Git author identity** — commits are signed with the maintainer's GitHub account; this is intentional for a public Open Source project
- **`acc-tailscale` and self-loopback requests** — some applications (WordPress, Paperless-ngx) may log self-request failures when behind IP allowlist; this is documented and does not affect user-facing security

See per-service `Known Issues` sections in each app's `README.md`.
