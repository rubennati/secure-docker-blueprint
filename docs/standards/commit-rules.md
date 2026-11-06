# Commit Rules

## Core Principles

- Commit when the user requests it or explicitly includes it in the task.
  Authorization for an agreed change set does not require another approval of
  each commit message. A request to edit or review alone does not authorize a commit.
- Keep unrelated work out of the commit. Review the staged diff before committing.
- Use an English, descriptive, scope-first message.
- Protect credentials and private data as specified below.
- Group changes by purpose, verification and rollback needs. Related pin updates
  may share a commit; migrations and changes to authentication or other behavior
  may need separate units. There is no fixed count per file, stack or batch.

## Signing

Commit signing is recommended when available, not a repository-wide requirement.
Use the existing signing setup when it works. If it is unavailable, an authorized
commit may be unsigned unless the user explicitly requested a signature or the
remote policy requires one. State a signing limitation when relevant.

Do not change global Git configuration, rebuild commits or cherry-pick changes
solely to obtain a signature. Any history rewrite needs its own justification
and authorization.

## Public content

The repository is public, and so are its pull requests, issues and releases.
The rule protects private systems and people, not technical content.

**Not committed** — in files, commit messages or those texts:

- **domains, hostnames and addresses of private systems** — a deployment's own
  domain, a server's or workstation's name, an address a real host or tailnet
  node holds
- **local paths of a workstation** (`/Users/<name>/…`) and **password-manager
  references** (`op://…`)
- **credentials, tokens and keys**, including example values that were
  generated for real
- **personal data**, and anything addressed to or from an assistant session —
  instructions, approvals, session notes

**Fine, and expected:**

- the project's own site and repository, and the public domains and published
  address ranges of upstream projects, registries and vendors — documentation
  links, image registries, telemetry endpoints, a provider's IP ranges
- placeholders and clearly marked examples: `example.com`, `example.org`,
  `example.net` (RFC 2606); loopback, RFC 1918 and RFC 5737 addresses; a tailnet
  example inside `100.64.0.0/10` or `fd7a:115c:a1e0::/48` that no real node holds
  (`100.64.0.10`, `fd7a:115c:a1e0::10`); `/Users/<name>/` and `op://<vault>/…`
- a synthetic value that has to look real, such as a checker's self-test
  fixture — marked as synthetic where it stands, and listed by fingerprint in
  `.gitleaksignore` if gitleaks reports it
- the legal notice and contact address of the operator site (`site/`), which
  the law requires

Records of test runs and host sessions (`docs/maintenance-log.md`,
`docs/host-session-*.md`, `docs/bugfixes/`, `docs/reviews/`) are kept and stay
technical: they describe what a test environment showed, by its role ("the test
host"), not by its name, address or owner. A test environment is not a
statement about production systems.

## Checks

Review the staged diff for credentials, private deployment data and unintended
changes. Do not stage `.env`, `.secrets/`, runtime data or unrelated work.
Synthetic fixtures and public upstream references follow [Public content](#public-content).

Run checks relevant to the change; use [`ci.md`](ci.md) and
[the local check reference](../../.ai/quality-gates.md) to select them. Required CI
checks must pass before merge. Report a check that could not run, including why;
do not describe it as passed. Inspect an existing unrelated failure separately
rather than silently expanding the change.

## Commit Message Format

Use an English subject that names the scope and resulting change; aim for a short
subject. Add a body when it helps explain behavior, migration, risk or validation.

```text
<scope>: <short description>

<optional explanation and issue references>
```

Examples: `apps/wordpress: fix upload permissions`,
`deps: update related patch pins`, `docs: simplify maintenance rules`.
A co-author trailer is optional and must identify an actual contributor accurately.
Do not fabricate model versions, identities or vendor addresses.

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
protected branch. `main` requires two checks more — Trivy's IaC config scan and
its image CVE scan — so a pull request from `dev` cannot land with a red image
scan.

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
- The twelve required checks passed against current
  `main` — the ten CI jobs plus Trivy's IaC config scan and image CVE scan
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

- `dev` → `main`: after required checks pass and the release's relevant runtime
  verification is complete; untested updates and remaining gaps are stated explicitly
- `feature/*` → `dev`: through a pull request, once the feature works and is self-contained

## Push Strategy

Push only authorized changes and name the remote ref explicitly:

```bash
git push -u origin fix/my-change
```

Review which commits will be published and check them for private data. Do not use
`--all` or `--mirror` for routine work. A request for a local commit does not
itself authorize a push, release or merge. Do not alter branch protection to
complete ordinary work.

## AI Commit Behavior

Before an authorized commit, inspect `git status` and the staged diff, exclude
unrelated edits, run relevant checks and choose a descriptive message. Then commit
within the agreed scope; another message-approval step is unnecessary.

If authorization is unclear, ask whether a commit is wanted. If the user requested
no commit or is only discussing a proposal, leave the work uncommitted.

## Undoing Commits

Prefer a revert for published changes. Local resets can preserve edits but still
change branch state; choose the operation for the task rather than applying a
standard recovery recipe. Do not discard uncommitted work or rewrite shared
history without explicit authorization.

For a leaked credential, revoke or rotate it first. Removing a file does not
invalidate the credential or remove it from history. A history rewrite is a
separate decision with effects on clones, forks and tags.

## Checklist before every commit

- [ ] Commit is within the user's authorization.
- [ ] Staged changes contain only the intended change set and no private data.
- [ ] Relevant checks and limitations are understood and reported.
- [ ] Message describes the change; affected documentation is included in the change set.

## Related Standards

- [`documentation-workflow.md`](documentation-workflow.md) — affected documentation and generated views
- [`new-app-checklist.md`](new-app-checklist.md) — adding a stack
