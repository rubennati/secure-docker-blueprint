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
3. **Make your changes** following the [app-setup-blueprint](docs/app-setup-blueprint.md) if you're adding or modifying an app
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

The CI pipeline is the automated test suite for this configuration project. It runs on every push and pull request. **All checks must pass before merge.**

| Job | What it validates |
|---|---|
| Secret scan | No credentials committed to git history |
| Compose validation | All compose files parse and resolve correctly |
| Structure check | Every service directory has `README.md`, `.env.example`, no `:latest` image tags |
| Sentinel check | No `__REPLACE_ME__` values in committed `.env` files |
| Security baseline | `no-new-privileges:true` present, no `privileged: true`, socket proxy pattern enforced |

See [`docs/standards/ci.md`](docs/standards/ci.md) for full documentation of each job.

### Running checks locally

The primary check during development:

```bash
python3 scripts/ci/check-baseline.py
```

This validates every compose file against the security baseline rules and prints all violations and documented exceptions.

## Questions?

Open a [discussion](https://github.com/rubennati/secure-docker-blueprint/discussions) or file an issue with the `question` label.

Enhancement requests and feature suggestions are welcome via GitHub Issues or Discussions. The project direction is tracked in [ROADMAP.md](ROADMAP.md).
