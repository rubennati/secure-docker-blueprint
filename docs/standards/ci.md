# CI Pipeline

All checks run automatically on every push to `dev` and `main`, on pull requests
targeting `main`, and nightly at 03:00 UTC.

```text
push (dev/main) ──┐
pull_request      ├──▶  CI
schedule 03:00 UTC┤
workflow_dispatch ┘
```

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

---

### 5 — Sentinel value check

Fails when a committed `.env` still contains `__REPLACE_ME__` — a placeholder that
reached the repository is a configuration nobody filled in.

**Blocks merge:** yes

---

### 6 — Canonical structure

Runs `scripts/ci/check-structure.py`. Severity is per rule rather than per
category: `:latest` or major-only tags, a plaintext secret in `.env.example`, a
`.gitignore` that does not cover `.secrets/`, and a datastore on `proxy-public`
all fail. Missing resource limits, missing healthchecks and `env_file:` are
reported as warnings — they need values measured on a real host, which is v0.9.0.

**Blocks merge:** yes, on FAIL rules only

---

### 7 — Status model

Runs `scripts/ci/lifecycle-report.py --check`. Fails on a status claim that is not
backed: an owner and its mirror disagreeing, a ✅ without `Last verified`, or a
`LIFECYCLE.md` left stale against its sources.

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

**Blocks merge:** not yet — the job runs, but adding it to the required set is a
branch-protection setting.

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

**Blocks merge:** not yet — the job runs, but adding it to the required set is a
branch-protection setting.

---

## Running locally

```bash
# Install dependency (once)
pip install pyyaml

# Run from the repo root
python3 scripts/ci/check-baseline.py
python3 scripts/ci/check-structure.py
python3 scripts/ci/lifecycle-report.py --check
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
