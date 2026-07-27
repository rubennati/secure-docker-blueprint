# Domain — Documentation

**Specs:** [`documentation-workflow.md`](../../docs/standards/documentation-workflow.md) ·
[`maintenance.md`](../../docs/maintenance.md) File Map ·
[`status-model.md`](../../docs/standards/status-model.md)

## Same change set, not later

Code and its documentation go into the same commit. What is not written while the
reasons are fresh is lost — the rationale that is obvious today is gone in two weeks.

## One owner per fact

The File Map in `docs/maintenance.md` names the owner of every fact. A mirror never
overrides its owner. If an owning document looks wrong, propose changing it *there*.

Derived files are regenerated, never retyped:

```bash
python3 scripts/ci/lifecycle-report.py --write
```

## What each document is for

| Document | Contains |
|---|---|
| Root `README.md` | What exists, one line per service, status symbol |
| Category `README.md` | Scope of the category, choice guidance, per-tool rationale |
| App `README.md` | Setup, verify, security model, known issues, `## Backup` |
| App `UPSTREAM.md` | Source, license, version, `Last verified`, upgrade checklist |
| `CHANGELOG.md` | What shipped |
| `ROADMAP.md` | Direction — never a duplicate of the changelog |
| `docs/architecture.md` | Why the structure is the way it is |
| `docs/bugfixes/` | One incident: symptom, cause, fix, lesson |

## Writing

- English in the repository, German in chat and on the `docs` branch.
- Neutral or imperative — documentation addresses no one personally.
- Never name another product or vendor negatively. State what this project does.
- No real domains, IPs, hostnames or personal data — `example.com` and documentation
  ranges only.
- No session context, personal attribution or self-critical wording in public files.
- No links to the `docs` branch from public files — a dead end for anyone who cloned
  normally.

## Status claims

A status is a claim about evidence. `✅` requires all ten Ready Criteria, including a
`Last verified: YYYY-MM-DD (vX.Y.Z)` that reflects an actual verification — not a
version bump. When in doubt, `🚧` is the honest answer.
