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

```
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

```
main     ← stable, tested, public-ready
│
├─ dev   ← work-in-progress, merges into main after test
│
└─ docs  ← drafts / German meta-docs / Notion-bound content
```

### When to use which branch

| Change type | Branch |
|-------------|--------|
| Small fix, tested | `main` directly |
| New feature, hardening, refactoring | `dev` → merge to `main` after test |
| German meta-doc, Notion draft, work-in-progress doc | `docs` |
| Bugfix | `main` (small) or `dev` (bigger) |

### Rules per branch

**main:**
- English only
- Everything tested
- No drafts, no German
- Public-ready at all times

**dev:**
- English
- Work-in-progress allowed
- Will be merged after test
- Not public

**docs:**
- Can be German
- Drafts allowed
- Not public
- Content that belongs to Notion lives here until transferred

### Merge rules

- `dev` → `main`: Merge only after live testing passed and README + Test-Script are green
- `docs` → `main`: Never (except explicit English docs that become standards)

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
