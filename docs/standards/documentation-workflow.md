# Documentation Workflow

Rules for keeping documentation in sync with the code. Documentation that lags behind code is worse than no documentation — it misleads.

## Core Principle

**Same-commit documentation.** Code changes and their documentation updates go into the same commit (or the next one at the latest). "We'll fix the docs later" is not allowed.

## Document Types

Every document has a type. The type determines when it must be updated.

| Type | Update Trigger | Update Window | Examples |
|------|----------------|---------------|----------|
| **Live** | Any relevant commit | Same commit | `README.md`, `ROADMAP.md`, per-app `README.md`, `UPSTREAM.md` |
| **Policy** | Policy decision changes | Same commit | `SECURITY.md`, `LICENSE` |
| **Reference** | Standard evolves | Same commit | `docs/standards/*.md` |
| **Snapshot** | Event occurred | At event | `docs/bugfixes/<app>-<date>.md` |
| **State** | Milestone reached | Within 24h | External Notion status page |
| **Draft** | Ongoing iteration | Flexible | Private drafts, work-in-progress docs |

## Update Triggers

Concrete rules: when X happens, update Y.

### Code Changes

| When | Update |
|------|--------|
| New app added to `apps/` | `README.md` (apps table), `ROADMAP.md` (remove from planned if applicable), new app's `README.md` + `UPSTREAM.md` |
| New core service added to `core/` | `README.md` (core infrastructure table), related standards if patterns changed |
| App version bumped (new image tag) | App's `UPSTREAM.md` (Based on version + Last checked) |
| App removed | `README.md`, `ROADMAP.md`, possibly `CHANGELOG.md` |
| New standard in `docs/standards/` | `README.md` (conventions section), cross-refs in other standards |
| Standard evolves (rule change, new pattern) | Affected standards file + every app that uses it |
| Security baseline change | `SECURITY.md`, `docs/standards/security-baseline.md`, all apps |
| Breaking change | `CHANGELOG.md`, relevant app `UPSTREAM.md` |

### Bug Fixes

| When | Update |
|------|--------|
| Bug discovered | `docs/bugfixes/<app>-<date>.md` (OPEN status) |
| Bug fixed | Same bugfix doc (RESOLVED status), app `README.md` Known Issues if user-facing |
| Bug parked (upstream) | Same bugfix doc (PARKED status), note in app README |
| Recurring pattern across bugs | Project manifest "Lessons Learned" section (if manifest tracked) |

### Process Changes

| When | Update |
|------|--------|
| Commit rules change | `docs/standards/commit-rules.md` |
| Branch model change | `docs/standards/commit-rules.md` + `documentation-workflow.md` |
| Release process change | `CHANGELOG.md`, release notes template |
| Review process change | `CONTRIBUTING.md` (when it exists) |

### Milestones

| When | Update |
|------|--------|
| App live-tested + hardened | External status page (Notion) within 24h |
| Feature completed | `ROADMAP.md` (move from In Progress to Done/remove), `README.md` if user-facing |
| Release tagged | `CHANGELOG.md`, Git tag |

## Freshness Rules

### Always up-to-date (no exceptions)

- `README.md` — first impression, must never mislead
- `SECURITY.md` — contact info, response timeline
- `LICENSE` — legal accuracy
- Per-app `README.md` Setup instructions — users follow these literally

### Can lag briefly (days)

- `ROADMAP.md` — target: monthly refresh, tolerated: up to 30 days stale
- External status page — target: 24h after milestone

### Refreshed periodically (event-based)

- `CHANGELOG.md` — at release
- `docs/bugfixes/*` — at event (lifetime)

## Sync Points

Checkpoints where documentation consistency is verified.

### Per-commit (mandatory)

Before every commit, the AI or contributor asks:

- Does this change affect any Live document?
- Does it invalidate a Reference document (standards)?
- Does it need a Snapshot document (bugfix)?

If yes → update in same commit.

### Per-push (recommended)

Before pushing to `main`:

- `README.md` reflects current state
- `ROADMAP.md` reflects current priorities
- All standards are consistent

### Periodic (monthly)

- `ROADMAP.md` review: is it still the actual priority?
- Notion status: consistency with repo state
- Stale bugfix-docs (OPEN for > 30 days): parked or escalated

### Per release (when applicable)

- `CHANGELOG.md` update
- Standards review
- Cross-doc consistency check

## Checklist for Common Changes

### Checklist: Adding a new app

- [ ] Create `apps/<app>/` directory with compose, env, README, UPSTREAM, gitignore
- [ ] Update `README.md` apps table (alphabetical or grouped)
- [ ] If app was in `ROADMAP.md` as planned → remove from there
- [ ] Bugfix-doc if any issues during bring-up
- [ ] Update external status (Notion) within 24h

### Checklist: Bumping an image version

- [ ] Change `APP_TAG` in `.env.example`
- [ ] Update `UPSTREAM.md` (Based on version, Last checked)
- [ ] Run test-script, document any regressions
- [ ] If breaking change: `CHANGELOG.md` entry

### Checklist: Changing a standard

- [ ] Update the specific standards file
- [ ] Grep repo for old pattern, update every occurrence
- [ ] Cross-ref check in other standards
- [ ] Update `README.md` conventions section if user-facing

### Checklist: Fixing a bug

- [ ] Write bugfix-doc with Symptom/Cause/Fix/Lesson
- [ ] Update app `README.md` Known Issues (if user-facing)
- [ ] Fix in code
- [ ] Commit: fix + bugfix-doc together

## AI Responsibility

When working on changes, the AI must:

1. **Identify doc dependencies** — after a code change, ask: what docs does this affect?
2. **Update in same commit** — not in a follow-up commit "later"
3. **Flag inconsistencies** — if touching a file reveals outdated docs nearby, mention it to the user
4. **Refuse to commit with known stale docs** — ask user first: "I notice README is out of date, should I fix it as part of this commit?"

### Anti-patterns (AI must avoid)

- "We'll update the docs later" — no
- Committing code without checking if README/ROADMAP still accurate — no
- Updating docs in a separate commit without linking it to the code change — avoid (use same commit when possible)
- Leaving ROADMAP with "Planned" items that are already done — not allowed

## Documentation Ownership

Every document has an implicit owner:

| Document | Primary Owner | When to Touch |
|----------|---------------|---------------|
| `README.md` | Maintainer | Any user-visible change |
| `ROADMAP.md` | Maintainer | Planning, milestones |
| `SECURITY.md` | Maintainer | Policy updates |
| `docs/standards/*` | Maintainer | Standard evolution |
| `docs/bugfixes/*` | Whoever fixed | At bug event |
| App `README.md` | App contributor | When changing that app |
| App `UPSTREAM.md` | App contributor | At version bumps |
| External status page | Maintainer | Milestones |

## Related Standards

- [`commit-rules.md`](commit-rules.md) — commit process, branch model
- [`new-app-checklist.md`](new-app-checklist.md) — checklist when adding apps
