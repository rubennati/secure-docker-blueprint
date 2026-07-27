# Measuring resource limits

How to turn a running host into the numbers v0.9.0 needs. This is the procedure;
the values themselves are owned by the profile table in
[`standards/security-baseline.md`](standards/security-baseline.md).

Roughly 121 services currently carry no `deploy.resources.limits` — the current
count comes from `python3 scripts/ci/check-structure.py`, and v0.9.0 is the pass
that closes it.

## Why this is not a desk task

A wrong limit does not fail loudly. A memory cap below the real peak produces an
OOM kill that looks like an application crash, usually under exactly the load that
made it matter. A CPU cap set too low produces latency nobody attributes to a
config file written months earlier.

That is the whole reason v0.9.0 sits late in the roadmap: the numbers have to come
from a running install, and a guessed limit is worse than no limit because it
introduces a failure mode that did not exist before.

## What to record

Three numbers per service, and **peaks, not averages**. An average tells you what
the container usually does; the limit has to survive what it occasionally does.

| Value | Read from | Why the peak matters |
|---|---|---|
| Memory | `MEM USAGE` | The one that kills. Startup, migrations and imports spike well above steady state |
| CPU | `CPU %` | Relative to one core: `100%` is one full core, so `cpus: "1.00"` |
| PIDs | `PIDS` | Fork-heavy apps (PHP-FPM, worker pools) sit far above their idle count under load |

## The sampler

`docker stats` without `--no-stream` is a live view, not a record. Sample it into a
file instead, and leave it running for the whole session:

```bash
mkdir -p ~/resource-samples
while true; do
  docker stats --no-stream \
    --format '{{.Name}};{{.MemUsage}};{{.CPUPerc}};{{.PIDs}}' \
  | sed "s/^/$(date -Iseconds);/" >> ~/resource-samples/stats.csv
  sleep 10
done
```

Peak per container, once enough has accumulated — columns are container, memory
in MiB, CPU percent, PIDs:

```bash
awk -F';' '
{
  split($3, m, "/"); v = m[1]
  u = v; sub(/^[0-9.]+/, "", u); gsub(/ /, "", u)
  n = v + 0
  if (u == "GiB") n *= 1024; else if (u == "KiB") n /= 1024; else if (u == "B") n /= 1048576
  if (n   > mem[$2]) mem[$2] = n
  if ($4+0 > cpu[$2]) cpu[$2] = $4+0
  if ($5+0 > pid[$2]) pid[$2] = $5+0
}
END { for (k in mem) printf "%-28s %9.1f %8.2f %6d\n", k, mem[k], cpu[k], pid[k] }
' ~/resource-samples/stats.csv | sort
```

The unit conversion is not decoration. `docker stats` mixes `KiB`, `MiB` and `GiB`
in the same column, so a naive numeric comparison ranks `800MiB` above `1.5GiB`
and hands back a limit roughly half the real peak. The column also carries
`usage / limit`, which is why only the part before the slash is read.

## The load states that matter

Sampling an idle container is the trap. It produces a limit that holds until the
first real workload and then kills the container. Capture at minimum:

- [ ] **Cold start** — the highest memory figure for many apps, because migrations
      and index builds run once and run big
- [ ] **Steady state** — a few hours of doing nothing in particular
- [ ] **Real work** — the app's actual core function: an import, a large upload, a
      backup run, a search across the whole dataset, several users at once

A service whose only sample is "cold start plus idle" is not measured. Record that
it is unmeasured rather than deriving a limit from it.

## From sample to limit

1. Take the peak, not the average.
2. Add headroom — **roughly 2x** for memory, which is what
   `apps/_reference/docker-compose.yml` states. Not because the container needs
   twice as much, but because the cap exists to stop runaway growth, not to
   right-size the application.
3. Round to the nearest profile in the
   [security baseline table](standards/security-baseline.md), rather than writing
   `733M`. The profiles exist so a reviewer can see at a glance which class a
   service belongs to.
4. Where the measurement lands **above** its profile, the profile is not wrong —
   that service is in a different class than assumed. Note which, so the table can
   be corrected at its owner.

One-shot and migration containers get no limit at all. Capping something that has
to finish once is how a restore stops halfway.

## Where the number goes

Into `deploy.resources` in the service's own `docker-compose.yml`, in the
**Resources** block — never a top-level `pids_limit`, which conflicts with a
`deploy:` block and errors.

```yaml
deploy:
  resources:
    limits:
      memory: 512m
      cpus: "0.50"
      pids: 100
    reservations:
      memory: 128m
```

`reservations` is the soft floor the scheduler tries to keep available; keep it
well under the limit.

## Confirming a limit rather than assuming it

A limit is verified when the service has run its core function *with the limit in
place* and not been killed.

```bash
# Did anything get OOM-killed since the limits went in?
docker inspect <container> --format '{{.State.OOMKilled}} {{.RestartCount}}'
journalctl -k | grep -i "killed process"
```

`OOMKilled: true` means the limit is too low, full stop — not that the application
leaks. Raise it, record the new peak, and note what workload produced it.

## Recording it

Per service, in the same change set as the limit itself:

- The peak that was measured, and under which load state
- Anything that landed in a different profile than expected

`docs/maintenance.md` Progress Log carries the session-level summary. A limit
committed without a note of what it was measured against is indistinguishable
from a guessed one six months later — which is the failure this whole procedure
exists to avoid.
