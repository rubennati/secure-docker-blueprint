# CI Pipeline

All checks run automatically on pull requests targeting `dev` or `main`, and on
every push to `main`.

```text
pull_request (dev, main) ──┐
push         (main)      ──┼──▶  CI
workflow_dispatch        ──┘
```

Both `dev` and `main` are protected by an active ruleset that requires a pull
request, requires all ten jobs below, and requires the branch to be up to date
before merging. Neither ruleset has a standing bypass actor, so the pull-request
run is what decides whether a change can land on either branch.

That is why `dev` has no post-merge run: the branch had to be current, so the
pull-request run already tested the integration that lands, and a second run
would repeat it. `main` keeps its push run anyway: it checks the actual commit
that lands rather than a pull-request merge preview, which matters for job 1 —
gitleaks scans that commit's own message, and a squash or rebase merge creates
one that was never itself scanned. The extra cost is accepted on the branch
that is published, tagged and released from.

There is no nightly (or any other) schedule on this workflow. All ten jobs are
deterministic checks of the current git tree — none makes a network call or
depends on elapsed time — so a run against a tree that already passed them
produces no new evidence, and the ruleset above means no tree reaches either
branch without having passed them first. `workflow_dispatch` stays available
for an ad hoc re-run. Contrast this with `trivy.yml`, `codeql.yml` and
`scorecard.yml`, which keep a weekly schedule on top of their change-triggered
runs: they verify state that can change independent of a commit here (newly
published CVEs, updated CodeQL query packs, external Scorecard inputs), which
is exactly the case a schedule is for.

A superseded run on the same open pull request is cancelled — the newer commit
is the one that should be checked, and the concurrency group is scoped so this
can never cancel the push run on `main` or a manual dispatch.

CodeQL runs on pull requests to both branches and reports its findings. It is
deliberately **not** a required check and does not block a merge.

---

## Jobs

### 1 — Secret scan (`gitleaks`)

Runs [gitleaks](https://github.com/gitleaks/gitleaks) across the full commit
history (`fetch-depth: 0`) to detect accidentally committed credentials —
API keys, passwords, tokens, private keys.

**Blocks merge:** yes  
**Tool:** `gitleaks/gitleaks-action@v2`

---

### 2 — Compose validation

Runs `docker compose config --quiet` once per stack directory, over the 59
directories `python3 scripts/ci/check-structure.py --list` reports. That is the
single discovery in this repository; jobs 2 and 3 and `check-baseline.py` all use
it. The `find` this job used to run returned 56 files against the checkers' 71 —
the fourteen Seafile split-compose fragments and `backup/urbackup` were never
syntax-validated.

Validation is per directory rather than per file because a split-compose
fragment does not stand alone: `apps/seafile/seadoc.yml` declares a service that
depends on `db`, which lives in `seafile-server.yml`. Running inside the directory
also picks up `COMPOSE_FILE` from the `.env`, so what parses is what the operator
starts.

Before validation, any `.env.example` in the same directory is temporarily
copied to `.env` so variable substitution does not cause false failures.

**What it catches:** YAML syntax errors, unknown keys, missing required variables,
invalid volume/network references.  
**Blocks merge:** yes

#### Opt-in overlay variants

A second step runs `scripts/ci/check-overlays.py --require-docker`. The discovery
above deliberately excludes overlays — a file applied *on top of* a stack, such as
`activitypub.yml` or `network-host.yml` — because they are not part of the stack
and several are alternatives to one another.

Each overlay is instead validated as its own deployment variant: `docker compose
config` merges the stack with that one overlay, and the result is judged. Merging
through Compose rather than in YAML is the point — the merge rules differ per key,
and `!reset` / `!override` change them again, so an approximation would disagree
with what an operator runs.

Every overlay is merge-validated, including one that only redefines networks. The
mandatory baseline is then applied to the services the overlay **adds or
changes**; services it leaves alone are already covered by the canonical run, and
an overlay that changes none is proved to resolve without inventing service checks
it could never fail. That split is what catches a patch-only overlay — a block
with no image, which adds no service and reads as harmless — handing an existing
service the Docker socket, setting `privileged: true`, or clearing its memory
ceiling.

Local runs without Docker report that they could not run and exit 0;
`--require-docker` in CI turns that into a failure.

**What it catches:** a merge Compose refuses (including an overlay patching a
service the stack does not define), an added service outside the baseline, and an
existing service the overlay weakens.  
**Blocks merge:** yes

---

### 3 — Structure check

Two checks run in one job:

| Check | Rule |
|---|---|
| README + .env.example | Every directory containing a `docker-compose.yml` must have both files |
| No `:latest` tags | `image:` lines must reference a pinned tag — `:latest` is forbidden |

The `:latest` grep matches only real `image:` lines (leading whitespace required),
so commented-out examples are not flagged.

**Blocks merge:** yes

---

### 4 — Security baseline

Runs `scripts/ci/check-baseline.py` — a custom Python/PyYAML script that
validates every compose file against the rules in
[`docs/standards/security-baseline.md`](security-baseline.md).

#### Rules checked

| Level | Rule | What triggers it |
|---|---|---|
| **FAIL** | `no-new-privileges` missing | Service lacks `security_opt: [no-new-privileges:true]` |
| **FAIL** | `privileged: true` | Any service with privileged mode enabled |
| **FAIL** | Direct Docker socket mount | `/var/run/docker.sock` mounted outside an exception |
| **WARN** | `network_mode: host` | Container shares the host network namespace |
| **WARN** | `pid: host` | Container shares the host PID namespace |

The same job runs `scripts/ci/check-crowdsec-config.py --templates`. It renders
`core/traefik` into a scratch copy three times — with the shipped `.env.example`,
then with `CROWDSEC_BOUNCER_ENABLED=true` and a placeholder key, then with the
switch off again over that render — and parses each result: the shipped default
yields no plugin and no `crowdsec-*` middleware, the switch yields the plugin plus
both middlewares keyed, and switching off removes both. It needs `envsubst`, which
the runner image provides.

`FAIL` blocks the pipeline. `WARN` is reported in the Job Summary but does not block.

#### GitHub Actions Job Summary

The script writes a Markdown summary to `$GITHUB_STEP_SUMMARY` after every run.
It contains two tables:

- **Violations** — every FAIL and WARN with file, service, rule, and detail
- **Accepted exceptions** — every documented exception with its full three-field
  justification (see below)

---

## Adding a new exception

Deviations from the baseline rules are allowed when they are reviewed and
explicitly documented. **Never suppress a finding silently.**

Open `scripts/ci/check-baseline.py` and add an entry to the appropriate table:

| Table | Use for |
|---|---|
| `SOCKET_EXCEPTIONS` | Direct `/var/run/docker.sock` mounts |
| `NO_NEW_PRIVILEGES_EXCEPTIONS` | Missing `no-new-privileges:true` |
| `HOST_MODE_EXCEPTIONS` | `network_mode: host` or `pid: host` |

### Required fields

Every exception entry must carry all three fields:

```python
"your-service-name": {
    "reason":       "Why the control cannot be applied to this service.",
    "alternatives": "What other mitigations or approaches were evaluated and why they were rejected.",
    "risk":         "Explicit statement that the risk is accepted, and why it is acceptable or low.",
},
```

### Example

```python
NO_NEW_PRIVILEGES_EXCEPTIONS: dict[str, dict[str, Exception]] = {
    "apps/myapp": {
        "app": {
            "reason":       "The entrypoint sets file ownership at first run — no-new-privileges "
                            "prevents the setuid calls this requires.",
            "alternatives": "A custom entrypoint that pre-creates directories was evaluated but "
                            "would need to be maintained across every image update.",
            "risk":         "Accepted — medium risk, mitigated by network isolation. The container "
                            "has no direct internet exposure.",
        },
    },
}
```

The key is the **relative path to the directory** containing `docker-compose.yml`
(e.g. `apps/myapp`, not `apps/myapp/docker-compose.yml`).

**Blocks merge:** yes, on `dev` and on `main`.

---

### 5 — Sentinel value check

Fails when a committed `.env` still contains `__REPLACE_ME__` — a placeholder that
reached the repository is a configuration nobody filled in.

**Blocks merge:** yes

---

### 6 — Canonical structure

Runs `scripts/ci/check-structure.py`. Severity is per rule rather than per
category: `:latest` or major-only tags, a plaintext secret in `.env.example`, a
`.gitignore` that does not cover `.secrets/`, a datastore on `proxy-public`, a
service without resource limits, and a memory limit without a stated swap policy
(`memswap_limit`) all fail.

The tag rule reads **every committed `*.env*.example` file in a stack**, not just
`.env.example`, and matches both pinning styles — `<NAME>_TAG` and the whole
reference in `<NAME>_IMAGE`. Neither was true before: 84 example files were
outside the check, and `APP_IMAGE=x:latest` passed where `APP_TAG=latest` failed,
for the same defect. Someone evaluating a stack from the local path is the person
least able to tell which version they ended up running. The structural rules —
section order, `COMPOSE_PROJECT_NAME` first — still describe `.env.example`
alone, because they describe that file's shape rather than reproducibility.

`local-pin-drift` fails when a stack's local file pins a different version of an
image its production file also pins. It joins on the image repository, so a
local stack that deliberately runs a *different* image is never compared. The
rule is in [`compose-structure.md`](compose-structure.md); the reason it needed
a checker is that the Version Chain never named `.env.local.example`, so 41 pins
drifted behind production without a decision. A missing healthcheck and `env_file:` are reported as
warnings — the numeric values behind the limits still need measuring on a real
host, which is v0.10.0; whether a policy is stated at all is settled.

**Blocks merge:** yes, on FAIL rules only

---

### 7 — Status model

Four generated views, each checked against the files that own it.

`scripts/ci/lifecycle-report.py --check` fails on a status claim that is not
backed: an owner and its mirror disagreeing, a ✅ without `Last verified`, or a
`LIFECYCLE.md` left stale against its sources.

`scripts/ci/sovereignty-report.py --check` fails when a stack states no licence
or origin, or when `sovereignty.json` is stale.

`scripts/ci/security-coverage.py --check` fails when `docs/security-coverage.md`
no longer matches the compose files it is counted from. The hardening figures
were maintained by hand until then and went stale twice in three days, because a
stack landing between two edits moves a denominator nobody remembers.

`scripts/ci/site-catalogue.py --check` fails when a stack has no `Domain` or
`Role` in its `UPSTREAM.md`, when a catalogue entry names a stack that no longer
exists, or when `catalogue.json` is stale. The staleness half now also covers each
stack's operational footprint, which is derived from its compose files rather than
recorded anywhere, so adding a database to a stack updates its catalogue entry or
fails the check. This is what keeps the operator site
from falling behind the repository: a stack cannot land in `dev` while being
absent from the site's catalogue.

**Blocks merge:** yes

---

### 8 — Checker coverage

Runs `scripts/ci/check-coverage.py`. Inverts the question every other job asks —
not "does this stack comply?" but "is there content nothing looks at?".

A directory counts as covered when either the structure checker enumerates it or
the lifecycle report includes it. Neither alone suffices: the structure checker
keys on compose files and cannot see a host-installed component, while the
lifecycle report covers that component but verifies nothing about its tags or
secrets.

| Level | Rule | What triggers it |
|---|---|---|
| **FAIL** | `unchecked-dir` | A directory under a stack root holds tracked files and neither checker enumerates it |
| **FAIL** | `unknown-root` | A tracked top-level directory is neither a stack root nor a declared non-stack area |
| **WARN** | `structure-blind` | Covered by the lifecycle report only — no compose file, so tags and secrets are verified by hand |

Adding a new top-level category therefore fails CI until the category is either
added to a checker's roots or declared in `NON_STACK_ROOTS` with the reason.
Three coverage gaps surfaced by accident within one day, and each had let real
stacks go unchecked for months.

**Blocks merge:** yes, on `dev` and on `main`.

---

### 9 — Docs QA

Three checks over the documentation:

| Check | Command | Scope |
|---|---|---|
| Markdown style | `npx markdownlint-cli2` | every tracked Markdown file |
| Internal links and anchors | `scripts/ci/check-links.py` | relative paths and heading anchors — external URLs fail for reasons unrelated to the commit and are excluded |
| Prose register | `scripts/ci/check-prose.py --hints` | every tracked Markdown file |
| Checker regression tests | `python3 -m unittest discover -s scripts/ci` | the prose checker's own behaviour |

#### What the prose check blocks

A phrase from the [writing-style](writing-style.md) list anywhere in a
reader-facing file — the root documents, every stack `README.md` and everything
under `site/`. That inventory is clear, so the gate runs over the whole
repository rather than over a diff.

Maintainer files report the same findings as warnings and do not block. A
findings log or an audit records how something was established, including the
wording of the finding it quotes, and its subject is that record.

Prose is matched per unit, not per line: a paragraph, a list item or a block
quote is joined before the phrase list is applied, so a phrase split by an
ordinary line wrap is found. A heading, a table row, a fenced block and a blank
line end the unit, so no phrase is assembled from text the author kept apart.

`--changed-only --base <ref>` remains available for local review of a single
change. The checker matches phrases; whether a paragraph belongs to the purpose
of its section is [the relevance test](documentation-workflow.md#the-relevance-test),
which no checker can perform and which stays a review step.

**Blocks merge:** yes, on `dev` and on `main`.

---

### 10 — Workflow supply chain

Runs `scripts/ci/check-workflows.py` over `.github/workflows/`. A workflow is
build infrastructure with write access to the repository, so it is checked the
way the stacks are.

Three rules:

| Rule | What triggers it |
|---|---|
| Action pinned to a mutable ref | `uses:` naming a tag or branch instead of a commit SHA — a tag can be moved to different code after review |
| SHA without a version comment | a pinned SHA with no `# vX.Y.Z` beside it, which leaves nobody able to tell which release is pinned or when it aged |
| Workflow without `permissions:` | no explicit token scope, so the job inherits the repository default rather than stating what it needs |

**Blocks merge:** yes, on `dev` and on `main`.

---

## Running locally

```bash
# Install dependency (once)
pip install pyyaml

# Run from the repo root
python3 scripts/ci/check-baseline.py
python3 scripts/ci/check-structure.py
python3 scripts/ci/lifecycle-report.py --check
python3 scripts/ci/security-coverage.py --check
python3 scripts/ci/check-coverage.py

# What the Docs QA prose gate will see — uncommitted work included
python3 scripts/ci/check-prose.py --changed-only --base HEAD
```

Output:

```text
  ✓ 48 files checked, no violations

  48 files  ·  0 failures  ·  0 warnings  ·  12 skipped
```

Failures print the file, service, rule, and remediation hint.
Skipped entries are documented exceptions — run with the script open to
see the full justification for each.

---

## Workflow file

`.github/workflows/ci.yml`
