# Contributing to secure-docker-blueprint

Thanks for considering a contribution. This is an opinionated blueprint for security-hardened self-hosted Docker Compose infrastructure — contributions that fit that vision are welcome.

## Before you start

- **License**: contributions are accepted under the project's [Apache 2.0 license](LICENSE). By submitting a contribution you agree that it can be distributed under those terms.
- **Code of Conduct**: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be respectful.
- **Security issues**: please do not open public issues for security bugs. See [SECURITY.md](SECURITY.md).

## What's welcome

- **New apps** following the blueprint structure — a full `<category>/<name>/` setup with `README.md`, `UPSTREAM.md`, `.gitignore`, `docker-compose.yml`, `.env.example`. A `CONFIG.md` covering all env vars and lifecycle operations is encouraged for complex apps (see `apps/paperless-ngx/CONFIG.md` as the reference pattern) but not required for minimal single-container apps.
- **Improvements to existing apps** — security hardening, upstream version bumps, bug fixes
- **New core services** — only with prior discussion, since these affect every app
- **Documentation fixes** — typos, clarifications, missing cross-references
- **Test script improvements** — `ops/scripts/test-security.sh` variants per app
- **Traefik middleware additions** — new access/security/TLS profiles that fill a real gap

## What's out of scope

- Apps that don't fit self-hosted / homelab / small-team use-cases
- Workarounds that break the standards in `docs/standards/`
- Changes that require real domain names, real IPs, or personal data in committed files

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
- Update `CHANGELOG.md` under the `## [Unreleased]` section
- Update relevant docs (root `README.md`, app-level `README.md` / `UPSTREAM.md`, any app-specific `CONFIG.md` that exists) if behaviour or configuration changed
- No real data — verify with the pre-commit scan patterns listed in the go-live guide
- Secrets always via Docker Secrets or `.env` (gitignored), never hardcoded
- All CI checks must pass before merge (enforced by branch protection)
- New apps and services must pass compose validation, structure checks, and the security baseline

## CI and testing

The CI pipeline is the automated test suite for this configuration project. It runs on every pull request targeting `dev` or `main`, on every push to those branches, and nightly. **All checks must pass before merge.**

| Area | What it validates |
|---|---|
| Secrets | No credentials in the commit history, no `__REPLACE_ME__` left in a committed `.env` |
| Compose | Every compose file parses and resolves; every stack has a `README.md` and a `.env.example` |
| Security baseline | `no-new-privileges:true` present, no `privileged: true`, socket proxy pattern enforced |
| Canonical structure | No `:latest` or major-only image tags, no plaintext secrets, no datastore on the public network |
| Status model | Owner and mirror agree on a status, `LIFECYCLE.md` is current, ✅ carries a verification date |
| Checker coverage | No content directory that no checker looks at |
| Documentation | Markdown style, internal links and anchors, and the prose register across the repository |
| Workflow supply chain | Actions pinned by SHA, every workflow declares `permissions:` |

See [`docs/standards/ci.md`](docs/standards/ci.md) for full documentation of each job.

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
