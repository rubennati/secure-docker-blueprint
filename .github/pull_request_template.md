## What this changes

Short description of the change.

## Why

Link or reference the issue / discussion that motivated this. If none exists, explain the motivation briefly.

## Type

- [ ] Bug fix
- [ ] New app
- [ ] Existing app improvement / hardening
- [ ] Core service change (Traefik, CrowdSec, Authentik, OnlyOffice)
- [ ] Standards / documentation
- [ ] Refactor / cleanup
- [ ] Other:

## Manual test

How was this verified? Commands run, expected output seen. For apps:

```bash
docker compose up -d
docker compose ps                # all healthy
bash ops/scripts/test-security.sh <host>   # if applicable
```

## Checklist

- [ ] Branch target is `dev` (not `main`, unless trivial doc fix)
- [ ] Single focused topic (no unrelated drive-by changes)
- [ ] Follows `docs/standards/` — compose-structure, env-structure, naming-conventions, commit-rules
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] App-level `README.md`, `UPSTREAM.md`, `CONFIG.md` updated if relevant
- [ ] No real data in the diff — no real domains, IPs, tokens, or personal paths
- [ ] Secrets via Docker Secrets or `.env` (gitignored), never hardcoded

## For documentation changes

- [ ] Preflight done before writing — readers, document purpose, section objective, what is explicitly out of scope, and the canonical owner of each changing fact ([purpose preflight](../docs/standards/documentation-workflow.md#before-drafting-the-purpose-preflight))
- [ ] `python3 scripts/ci/check-prose.py` reports no blocking finding

## For new apps specifically

- [ ] Full `apps/<name>/` directory created
- [ ] `README.md` with Setup + Verify + Security Model + Known Issues + Details-Links
- [ ] `UPSTREAM.md` with Source + Changes + Upgrade-Checklist
- [ ] `CONFIG.md` if app has non-trivial configuration
- [ ] `.gitignore` with `.secrets/`, `volumes/`, `.env`
- [ ] App has a test-security script if it has a hardening story
