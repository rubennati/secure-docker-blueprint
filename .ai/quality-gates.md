# Quality Gates

What must pass before work is considered done. Full documentation of each CI job is
in [`../docs/standards/ci.md`](../docs/standards/ci.md).

## Run locally before proposing completion

```bash
python3 scripts/ci/check-baseline.py         # security baseline per container
python3 scripts/ci/check-structure.py        # canonical structure, tags, secrets
python3 scripts/ci/lifecycle-report.py --check   # status consistency + LIFECYCLE freshness
python3 scripts/ci/check-coverage.py         # content no checker covers
python3 scripts/ci/check-links.py            # broken relative links and anchors
npx markdownlint-cli2                        # markdown style
python3 scripts/ci/check-workflows.py        # action pinning, workflow permissions
python3 scripts/ci/check-prose.py            # register — what CI gates on
```

`--hints` adds the suggested replacement to each finding, in either mode.

Requires PyYAML: `pip install --require-hashes -r scripts/ci/requirements.txt`

After any status change or version pin:

```bash
python3 scripts/ci/lifecycle-report.py --write
```

Compose files:

```bash
docker compose config --quiet          # in the stack directory
```

## CI jobs

| Job | Blocks on |
|---|---|
| Secret scan (gitleaks) | credentials anywhere in history |
| Compose validation | a compose file that does not parse or resolve |
| Required files | a stack without `README.md` or `.env.example` |
| Sentinel value check | `__REPLACE_ME__` in a committed `.env` |
| Security baseline | missing `no-new-privileges`, `privileged: true`, socket-proxy violations |
| Canonical structure | `:latest` or major-only tags, plaintext secrets, unprotected `.secrets/`, a datastore on the public network |
| Status model | owner and mirror disagreeing on a status, ✅ without a verification date, stale `LIFECYCLE.md`; warns when `UPSTREAM.md` duplicates the README's backup procedure |
| Checker coverage | a content directory no checker enumerates, a top-level directory declared nowhere |
| Docs QA | markdown style drift, a link to a missing file, a link to a missing heading, a prose-register phrase anywhere in a reader-facing file |
| Workflow supply chain | an action pinned to a mutable tag, a SHA without a version comment, a workflow without `permissions:` |

The required-check names must match the job `name:` fields in
`.github/workflows/ci.yml` exactly. Renaming a job without updating branch
protection leaves every pull request waiting on a check that can never report.

> `Checker coverage`, `Docs QA` and `Workflow supply chain` run but are **not yet in the required set** — adding it to
> branch protection is a repository setting, not a file in here.

## Prose register — two modes

`scripts/ci/check-prose.py` matches the phrase list owned by
[`writing-style.md`](../docs/standards/writing-style.md) and separates two file
classes in both modes:

| Class | Files | Effect |
|---|---|---|
| Reader-facing | root `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, every `<stack>/README.md`, everything under `site/` | failure — the run exits non-zero |
| Maintainer | everything else, including `docs/` and `.ai/` | warning — the exit code stays 0 |

**Full run** — the gate:

```bash
python3 scripts/ci/check-prose.py --hints
```

Every Markdown file in the repository. This is what the `Docs QA` job runs: a
phrase in a reader-facing file fails it, a phrase in a maintainer file is
reported and does not. The reader-facing inventory is clear, which is what makes
the whole tree gateable.

**Differential run** — for reviewing one change locally:

```bash
python3 scripts/ci/check-prose.py --changed-only --base HEAD
```

Only the lines the diff adds or changes. `--base HEAD` covers uncommitted work.
There is no default base — a missing or unresolvable one exits 2 rather than
checking a wrong range. An untracked file is in no diff; the run names it and
says to `git add` it.

Prose is matched per unit — a paragraph, a list item or a block quote is joined
first, so a phrase split by an ordinary line wrap is found. A heading, a table
row, a fence or a blank line ends the unit.
`python3 -m unittest discover -s scripts/ci` covers that behaviour and runs in CI.

What neither mode covers:

- Both match an exact phrase list. They find those formulations and no others —
  passing says nothing about whether a file reads well.
- Neither can decide whether a paragraph belongs to the purpose of its section.
  That is the [relevance test](../docs/standards/documentation-workflow.md#the-relevance-test),
  and it stays a review step carried out by whoever makes the change.

## Not blocking, deliberately

- **Trivy** runs weekly with `exit-code: 0` — informational until the existing
  CRITICAL findings have been assessed once.
- **Structure warnings** (missing resource limits, missing healthchecks) are
  reported, not enforced. They need values measured on a real host — v0.9.0.
- **`legacy-stamp`** — a stack carrying the pre-v0.5.1 `Last checked:` field.
  Converting it asserts the evidence is real, which is a judgement per app.

## The gate that is not automatable

An app is `ready` only after a clean install and a working core function on a real
host. Every release since v0.2.0 is defined that way. No checker can substitute for
it, and no configuration is finished without it.
