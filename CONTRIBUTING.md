# Contributing to secure-docker-blueprint

Thanks for considering a contribution. This is an opinionated blueprint for security-hardened self-hosted Docker Compose infrastructure — contributions that fit that vision are welcome.

## Before you start

- **License**: contributions are accepted under the project's [Apache 2.0 license](LICENSE). By submitting a contribution you agree that it can be distributed under those terms.
- **Code of Conduct**: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be respectful.
- **Security issues**: please do not open public issues for security bugs. See [SECURITY.md](SECURITY.md).

## What's welcome

**Until the v1.0 work is complete, new applications are on hold.** Please discuss
an exception before implementing a new stack — see [Roadmap](ROADMAP.md#on-hold--after-v10-or-not-yet-needed).
Existing-stack fixes, verification and documentation can follow the workflow
below directly; the hold does not add an approval step for them.

For an agreed new application, provide a complete `<category>/<name>/` stack:
`README.md`, `UPSTREAM.md`, `.gitignore`, `docker-compose.yml` and `.env.example`.
Start from [`apps/_reference/`](apps/_reference/) and the
[new-app checklist](docs/standards/new-app-checklist.md). A `CONFIG.md` covering
settings and operations is encouraged for complex applications, as in
[`apps/paperless-ngx/CONFIG.md`](apps/paperless-ngx/CONFIG.md); it is not required
for a minimal single-container application.

- **Improvements to existing apps** — security hardening, upstream version bumps, bug fixes
- **New core services** — only with prior discussion, since these affect every app
- **Documentation fixes** — typos, clarifications, missing cross-references
- **Test script improvements** — `ops/scripts/test-security.sh` variants per app
- **Traefik middleware additions** — new access/security/TLS profiles that fill a real gap

## What's out of scope

- Apps that don't fit self-hosted / homelab / small-team use-cases
- Workarounds that break the standards in `docs/standards/`
- Changes that require a deployment's real domain names, IPs or personal data in committed files — see [Public content](docs/standards/commit-rules.md#public-content)

For larger changes, please open an issue first to discuss direction before writing code.

## Workflow

1. **Fork** the repository
2. **Create a branch** off `dev` (not `main`) with a descriptive name: `feature/add-vaultwarden`, `fix/wordpress-uploads-ini`, `docs/clarify-env-structure`
3. **Make your changes** — for a new app, copy [`apps/_reference/`](apps/_reference/) and follow the [new-app checklist](docs/standards/new-app-checklist.md)
4. **Test** live if possible — deploy on your own server, verify healthchecks green, run the app's test-security script if applicable
5. **Open a Pull Request** against `dev`. The maintainer will review and merge into `dev`, then later into `main` as part of a tested batch

## Commit messages

See [`docs/standards/commit-rules.md`](docs/standards/commit-rules.md) for the detailed convention. Short version:

- Short, imperative subject: `apps/ghost: add SMTP support via _FILE pattern`
- Scope-first prefix matches the top-level folder affected
- Keep unrelated changes in separate commits
- Reference issues with `Fixes #N` in the commit body

## Pull request expectations

- Single focused topic per PR
- Record notable changes in `CHANGELOG.md` under `## [Unreleased]`; routine wording corrections need no separate entry
- Update relevant docs (root `README.md`, app-level `README.md` / `UPSTREAM.md`, any app-specific `CONFIG.md` that exists) if behaviour or configuration changed
- Review the diff for credentials and private deployment data using [Public content](docs/standards/commit-rules.md#public-content). CI runs [gitleaks and the public-content pattern checks](docs/standards/ci.md#1--secret-scan-gitleaks); those checks do not replace review of real domains, addresses and other context they cannot recognise
- Secrets always via Docker Secrets or `.env` (gitignored), never hardcoded
- All CI checks must pass before merge — required by the ruleset on `dev` and on `main`
- New apps and services must pass compose validation, structure checks, and the security baseline

## CI and testing

The CI pipeline is the automated test suite for this configuration project. It runs on every pull request targeting `dev` or `main` and on every push to `main`; a manual run (`workflow_dispatch`) also scans the whole history for secrets. **All checks must pass before merge.**

| Area | What it validates |
|---|---|
| Secrets and public content | No credentials in the commits a pull request adds (gitleaks, default rules), no workstation paths or password-manager references in tracked files, no `__REPLACE_ME__` left in a committed `.env` |
| Compose | Compose files parse and resolve; Compose-based stacks carry a `README.md` and a `.env.example` |
| Security baseline | `no-new-privileges:true` present, no `privileged: true`, socket proxy pattern enforced |
| Canonical structure | No `:latest` or major-only image tags, no plaintext secrets, no datastore on the public network |
| Status model | Generated lifecycle views match their sources; verification names a date and version, and pin drift is reported |
| Checker coverage | No content directory that no checker looks at |
| Documentation | Markdown style, internal links and anchors, and the prose register across the repository |
| Workflow supply chain | Actions pinned by SHA, every workflow declares `permissions:` |

See the [standards guide](docs/standards/README.md) for the relevant rules and [`ci.md`](docs/standards/ci.md) for each CI job.

**Documentation quality is checked.** A phrase from the
[writing-style](docs/standards/writing-style.md) list in a reader-facing file —
the root documents, any stack `README.md`, anything under `site/` — fails the
build. Maintainer files report the same findings without blocking.

### Running checks locally

The primary check during development:

```bash
python3 scripts/ci/check-baseline.py
```

This validates every compose file against the security baseline rules and prints all violations and documented exceptions.

Before pushing, the checks most likely to fail on a documentation or structure change:

```bash
python3 scripts/ci/check-prose.py
python3 scripts/ci/check-links.py
npx markdownlint-cli2
python3 scripts/ci/check-structure.py
```

## Questions?

Open a [discussion](https://github.com/rubennati/secure-docker-blueprint/discussions) or file an issue with the `question` label.

Enhancement requests and feature suggestions are welcome via GitHub Issues or Discussions. The project direction is tracked in [ROADMAP.md](ROADMAP.md).
