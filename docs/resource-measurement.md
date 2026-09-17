# Measuring resource limits

How to turn a running host into the numbers v0.10.0 needs. This is the procedure;
the values themselves and the rule that derives them are owned by
[`standards/compose-structure.md`](standards/compose-structure.md#block-rules).

Every service carries a `memory` and a `pids` ceiling, so nothing is unbounded —
`python3 scripts/ci/check-structure.py` reports any service that loses one. What
v0.10.0 closes is their basis: the ceilings in place come from the derivation rule,
and the `cpus` values that remain are marked in the compose files as derived rather
than measured.

## Why this is not a desk task

A wrong limit does not fail loudly. A memory cap below the real peak produces an
OOM kill that looks like an application crash, usually under exactly the load that
made it matter. A CPU cap set too low produces latency nobody attributes to a
config file written months earlier.

That is the whole reason v0.10.0 sits late in the roadmap: the numbers have to come
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
3. Round to the nearest value in the role table in
   [`standards/compose-structure.md`](standards/compose-structure.md#block-rules)
   rather than writing `733M`. The roles exist so a reviewer can see at a glance
   which class a service belongs to.
4. Where the measurement lands **above** its role, the role is not wrong — that
   service is in a different class than assumed. Note which, so the table can be
   corrected at its owner.
5. Decide the swap policy in the same pass. `memswap_limit` equal to `memory` is
   the default; a higher value needs the peak that justifies it. Leaving it unset
   grants the container as much swap again as its memory limit, which is the one
   allowance nobody chose.

One-shot and migration containers still carry the same three limits — `core/authentik`'s
`init-perms` runs a chown in under a second and states `memory`, `pids` and
`memswap_limit` like everything else, because stating them costs nothing. What
differs is sizing them for the one thing the container does, not exempting it
from the requirement — a limit sized for a steady-state guess is how a
migration or restore stops halfway.

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

`reservations.memory` is **not** a guarantee. Docker maps it to a soft limit that
matters only when the host is under memory pressure: the kernel reclaims from
containers above their reservation before it touches ones below it. Nothing holds
the memory open in advance, and a container may sit below its reservation and still
be reclaimed if nothing else is reclaimable. Keep it well under the limit and read
it as a reclaim preference, not a floor.

`memswap_limit` is the memory-plus-swap ceiling, not a separate swap budget:
`memory: 512m` with `memswap_limit: 512m` means no swap, and `768m` means 256 MB of
swap on top.

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

## Does this deployment still enforce what the repository defines

A limit in a compose file is not a limit in the kernel. A container keeps the
`HostConfig` it was created with, so an edited file changes nothing until the
container is **recreated** — neither `docker compose restart` nor a Docker daemon
restart applies a new value.

Three sources, in order, and the answer is the disagreement between them:

```bash
# 1. What the repository defines, with variables resolved
docker compose config | grep -A6 -E 'memswap_limit|resources:'

# 2. What the running container actually enforces
docker inspect <container> --format \
  'mem={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} restart={{.HostConfig.RestartPolicy.Name}} oomkilled={{.State.OOMKilled}} restarts={{.RestartCount}}'

# 3. What the kernel enforces, when the two disagree
cat /sys/fs/cgroup/system.slice/docker-$(docker inspect -f '{{.Id}}' <container>).scope/memory.max
```

Across every running container at once:

```bash
for c in $(docker ps --format '{{.Names}}'); do
  docker inspect "$c" --format \
    '{{printf "%-28s" .Name}} mem={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} oomkilled={{.State.OOMKilled}} restarts={{.RestartCount}}'
done
```

Read it against three expectations:

| Observation | Meaning |
|---|---|
| `mem=0` | no limit in force — the container predates the limit, or was never recreated |
| `swap` at twice `mem` | swap left implicit; the container may page as much again as its cap |
| `swap` equal to `mem` | the stated policy is in force |
| `pids=<nil>` or `0` | no PID bound — a fork bomb reaches the host |
| `oomkilled=true` | the cap was reached; either the workload grew or the limit is too low |
| a climbing `restarts` with `oomkilled=true` | a restart loop against the cap, not a healthy service |

A container the repository knows nothing about — no compose project label — is drift
of a different kind, and worth resolving before reading anything else.

## Recording it

Per service, in the same change set as the limit itself:

- The peak that was measured, and under which load state
- Anything that landed in a different profile than expected

`docs/maintenance-log.md` carries the session-level summary. A limit
committed without a note of what it was measured against is indistinguishable
from a guessed one six months later — which is the failure this whole procedure
exists to avoid.
