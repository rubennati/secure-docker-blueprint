# CI Pipeline

All checks run automatically on every push to `dev` and `main`, on pull requests
targeting `main`, and nightly at 03:00 UTC.

```
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

Runs `docker compose config --quiet` on every `docker-compose.yml` found under
`core/`, `apps/`, `business/`, and `monitoring/`.

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

## Running locally

```bash
# Install dependency (once)
pip install pyyaml

# Run from the repo root
python3 scripts/ci/check-baseline.py
```

Output:

```
  ✓ 48 files checked, no violations

  48 files  ·  0 failures  ·  0 warnings  ·  12 skipped
```

Failures print the file, service, rule, and remediation hint.
Skipped entries are documented exceptions — run with the script open to
see the full justification for each.

---

## Workflow file

`.github/workflows/ci.yml`
