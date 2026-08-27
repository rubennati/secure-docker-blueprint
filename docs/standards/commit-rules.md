# Commit Rules

Rules for every commit in this repository. These rules are binding.

## Core Principles

- **Commit only on user request** — never auto-commit after file changes
- **Ask before committing** — two-part question: "Commit X? With message Y?"
- **English everywhere in main** — code, comments, commit messages, README, standards
- **German drafts go to `docs` branch** — never into `main`
- **No personal or private data** — ever
- **No leaks** — API keys, tokens, credentials never committed
- **Scope-first commits** — one logical change per commit

## Pre-Commit Checks (mandatory)

Before every commit the AI runs these checks. If any fails, the commit is aborted and reported.

### 1. No real domains

```bash
# Private / company domains must not appear in the repo.
# Only example.com / example.org / example.net (RFC 2606) allowed.
grep -rE "<privat-domain-pattern>" --include="*.yml" --include="*.yaml" \
  --include="*.md" --include="*.env*" --include="*.sh" --include="*.conf"
# Must return zero lines
```

### 2. No real IPs

```bash
# Only RFC ranges allowed:
# - 0.0.0.0, 127.0.0.0/8 (loopback)
# - 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (RFC1918)
# - 100.64.0.0/10 (CGNAT/Tailscale)
# - 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 (RFC 5737 documentation)
# - fc00::/7 (IPv6 ULA)
# - fd7a:115c:a1e0::/48 (Tailscale IPv6)

grep -rE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" --include="*.yml" --include="*.md" \
  | grep -vE "0\.0\.0\.0|127\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|100\.64\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\."
# Must return zero lines
```

### 3. No secrets

```bash
# Common patterns for credentials
grep -rE "(api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[=:]\s*['\"]?[A-Za-z0-9+/=_-]{16,}" \
  --include="*.yml" --include="*.md" --include="*.sh"
# Any match → abort + manual review
```

### 4. No personal or company names

```bash
# Avoid leaking identifiers that tie the repo to a specific person/company.
# List of disallowed tokens kept private — maintained by user.
```

### 5. No .env / .secrets staged

```bash
# These must never be committed
git diff --cached --name-only | grep -E "\.env$|\.secrets/" && echo "ABORT: secrets staged"
```

### 6. English in commit message

```bash
# Commit message should be English in main branch
# Heuristic: check for German word markers
git log -1 --pretty=%B | grep -iE "ä|ö|ü|ß|und|für|nach|mit|auch|bei|oder" \
  && echo "WARN: commit message may contain German — confirm"
```

## Commit Message Format

Conventional-style, English, scope-first:

```text
<scope>: <short description (max 72 chars)>

<optional body with details>
- Bullet point 1
- Bullet point 2

<optional footer for breaking changes / refs>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

### Scope examples

- `apps/wordpress:` for app-specific changes
- `core/traefik:` for core services
- `docs:` for root documentation
- `docs/standards:` for standard documents
- `docs/bugfixes:` for bugfix docs

### Good examples

- `apps/wordpress: standardize setup + security hardening`
- `core/traefik: add IPv6 support to access policies`
- `docs/standards: add commit-rules.md`
- `apps/paperless-ngx: set PAPERLESS_ALLOWED_HOSTS explicitly`

### Anti-patterns

- `update files` — no scope, no info
- `fix` — too generic
- `wip` — not acceptable in main
- `Aktualisiere Manifest` — German in main branch

## Branch Model

```text
main       ← stable, tested, public
│
└─ dev     ← active work, merges into main after test
   │
   └─ feature/*  ← short-lived branches; the only way into dev
```

### Workflow rule: both branches receive pull requests

All changes reach `dev` through a pull request from a short-lived branch, and
reach `main` through a pull request from `dev`. Both branches carry an active
ruleset that rejects direct pushes and requires the ten repository CI jobs to
pass against the current state of the target branch before a merge is possible,
so work-in-progress lives on the short-lived branch rather than on either
protected branch.

Neither ruleset has a standing bypass actor. CodeQL runs on both branches as a
reporting check: it surfaces findings and does not block a merge.

Rationale:

- `main` stays in a known-good state
- Testing happens before merge into `main`
- Revert of a feature is possible without touching `main` history
- Clear separation between "tested" and "in progress"

### When to use which branch

| Change type | Branch |
|-------------|--------|
| Any code change | branch from `dev` → pull request to `dev` |
| New app, hardening, refactoring | branch from `dev` → pull request to `dev` |
| Bugfix | branch from `dev` → pull request to `dev` |
| Release | pull request from `dev` to `main` after test |
| Emergency fix | see [Break-glass](#break-glass) — never a direct push |

### Merge workflow

```bash
# Work on a branch off dev
git switch dev && git pull --ff-only
git switch -c fix/my-change

# Publish it, then open a pull request against dev and merge it there
git push -u origin fix/my-change
```

If `dev` moves while the pull request is open, bring the branch up to date before
merging. The ruleset requires it, so the gates run against the integration that
actually lands.

For a release, open the pull request from `dev` to `main` the same way. Both
rulesets require the branch to be up to date before merging, so the gates run
against the integration that actually lands.

If conflicts: resolve them on the branch, never by merging into a protected
branch locally.

### Break-glass

Normal changes always go through a pull request. There is no permanent bypass on
either branch, and none should be added.

If an emergency genuinely cannot wait for the normal path, the maintainer
temporarily changes the GitHub ruleset, performs the action, and restores the
ruleset immediately afterwards. The reason belongs in the commit message and in
whatever incident record the change relates to.

This is a deliberate, audited exception. It is not a development workflow, and
nothing in this repository should be built on the assumption that it is
available.

### Rules per branch

**main:**

- Only receives merged pull requests from `dev`; direct pushes are rejected
- Everything tested, and the ten repository CI jobs passed against current `main`
- Commit messages in English
- Full CI runs again on the push that results from the merge — that run checks
  the integrated branch rather than the pull request's merge preview

**dev:**

- Only receives merged pull requests; direct pushes are rejected
- Represents integrated development state that has passed the gates
- Merged into `main` through a pull request after test

**feature/\*:**

- Short-lived
- Branched from `dev`, merged back into `dev`
- Deleted after merge

### Merge rules

- `dev` → `main`: only after live testing passed and tests green
- `feature/*` → `dev`: through a pull request, once the feature works and is self-contained

## Push Strategy

Push only what should be public. Always push refs explicitly.

### Explicit push commands

```bash
# Good — explicit ref, and on this repository the only ref you push
git push -u origin fix/my-change

# Avoid — pushes every local branch
git push --all
```

`main` and `dev` are not push targets: both rulesets reject a direct push, so the
day-to-day push is always to a short-lived branch. The bootstrap commands below
apply to a fresh remote that has no protection yet.

### Push-time checklist

Before `git push`:

- [ ] Pre-commit checks passed on all commits being pushed
- [ ] No real domains, IPs, secrets, personal data in files or commit messages
- [ ] Commit messages in English
- [ ] Remote ref explicitly named

### Setting up a public remote

```bash
# Add remote
git remote add origin git@github.com:<user>/<repo>.git

# Optional: configure which refs get pushed by default
git config --add remote.origin.push refs/heads/main

# Verify config
git config --get-all remote.origin.push
```

With this config, a plain `git push origin` pushes only the configured refs. Other branches require explicit `git push origin <branch>`.

### First push to a fresh remote

```bash
# 1. Run pre-push audit (see below)

# 2. Dry-run
git push --dry-run origin

# 3. Actual push
git push origin main
```

### Pre-push audit

Run before each push. Replace the pattern list with your own sensitive strings (domains, hostnames, usernames):

```bash
PATTERNS=(
  "your-private-domain\.com"
  "internal-hostname"
  "real-user-name"
  # add site-specific patterns here
)

for branch in main dev; do
  echo "── $branch ──"
  for pattern in "${PATTERNS[@]}"; do
    echo -n "  $pattern: "
    if git log $branch -p 2>/dev/null | grep -qE "$pattern"; then
      echo "FOUND — do NOT push"
    else
      echo "CLEAN"
    fi
  done
done
```

### Branch Protection (GitHub settings)

After first push, configure on the GitHub repo:

1. Settings → Branches → Branch Protection Rules
2. Protect `main`:
   - Require pull request before merging
   - Require status checks
   - Do not allow force pushes
   - Do not allow deletions
3. Optionally protect `dev` similarly

### Pre-push hook (optional)

A `.git/hooks/pre-push` script can prevent accidental pushes of specific local branches. The hook is not tracked (per-developer setup). Example pattern:

```bash
#!/usr/bin/env bash
# Block push of specific local-only branches
BLOCKED_BRANCHES=("local-notes" "drafts")

while read local_ref local_sha remote_ref remote_sha; do
  for blocked in "${BLOCKED_BRANCHES[@]}"; do
    if [[ "$remote_ref" == "refs/heads/$blocked" ]]; then
      echo "Push to '$blocked' blocked by local hook."
      exit 1
    fi
  done
done
exit 0
```

Make executable: `chmod +x .git/hooks/pre-push`

## AI Commit Behavior

The AI must follow these rules:

### Before any commit

1. Run `git status` and report to user
2. Run `git diff --cached` if anything staged
3. Run pre-commit checks (above)
4. Propose commit message
5. Ask user: "Commit the staged files with message `<msg>`? Or adjust?"
6. Wait for explicit user confirmation
7. Only then commit

### When the AI should NOT commit

- User hasn't asked for a commit
- Changes involve real data not yet redacted
- Changes involve secrets or .env
- Changes are in-progress / broken
- User said "don't commit" earlier in session
- User is reviewing / discussing, not decided

### When in doubt

Always ask. "Wollen wir das jetzt committen?" is better than an unwanted commit.

### Commit frequency

- **Small, logical commits** — one change per commit
- **Not every file-edit** — group related edits
- **Test-driven** — commit after tests pass, not during debugging

## Undoing Commits

### Options in order of safety

| Method | Safe for | Effect |
|--------|---------|--------|
| `git revert <hash>` | Any commit, including pushed | New commit that undoes the change. History preserved. |
| `git reset --soft <hash>` | Local, unpushed | Moves HEAD back, keeps changes staged |
| `git reset --mixed <hash>` | Local, unpushed | Moves HEAD back, keeps changes unstaged |
| `git rm <file> && commit` | Any time | Removes file in new commit, history preserved |
| `git reset --hard <hash>` | Local only, unpushed | **DESTRUCTIVE** — loses work |
| `git filter-repo / filter-branch` | Pushed, secret leaks | **NUCLEAR** — rewrites all history, breaks all clones |

### When to use which

- **Accidentally committed something** → `git revert` (safest)
- **Committed to wrong branch, want to move** → `git reset --soft` + re-commit on right branch
- **Committed secret that's already pushed** → `git filter-repo` + force push + rotate secret
- **Want file gone going forward but keep history** → `git rm` + commit

### Workflow example: undo last commit on main

```bash
# Safe (recommended): revert creates new commit
git revert HEAD

# If only local, not pushed yet:
git reset --soft HEAD~1  # keeps changes staged
git reset --mixed HEAD~1 # keeps changes unstaged
git reset --hard HEAD~1  # DESTROYS changes — use with care
```

## Checklist before every commit

- [ ] User explicitly asked for commit
- [ ] Scope and message clear
- [ ] English in message (unless `docs` branch and explicitly German)
- [ ] Pre-commit checks passed (no domains, IPs, secrets, personal data)
- [ ] Correct branch (not accidentally committing to main)
- [ ] `git status` and `git diff --cached` reviewed
- [ ] Test-Script run (if applicable)
- [ ] Co-Authored-By footer present
- [ ] User confirmed after seeing proposed message
- [ ] Related docs updated in the same commit (see [`documentation-workflow.md`](documentation-workflow.md))

## Related Standards

- [`documentation-workflow.md`](documentation-workflow.md) — which documents must be updated when code changes, and the "same-commit documentation" rule
- [`new-app-checklist.md`](new-app-checklist.md) — step-by-step for adding a new app, including doc requirements per commit
