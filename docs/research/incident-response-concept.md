# Incident response, container isolation and forensics — planned

**Status: planned, not implemented.** A concept for the Secure Docker Blueprint, written
at the end of step 8 from what the lab host showed (`docs/labs/ingress/2026-11-01-results.md`). Nothing here ran on the host; the
facts it builds on are marked "measured" where the lab produced them.

## Goal

Next to the access policies, which decide who may reach an application, an independent
mechanism that lets an operator **contain** one container, one application or one stack
when it is suspected compromised — without shutting it down where that would destroy
evidence — **preserve** what is needed to investigate it, find **what else** is affected,
and **reconnect** it in a controlled way afterwards.

## What the blueprint already provides that isolation can build on

| Fact | Source |
|---|---|
| One edge network per stack, joined only by the stack and Traefik; databases and caches on `internal` networks without egress | measured (audit: internal networks reach nothing outside; `proxy-public` resolves no application) |
| Only Traefik publishes ports; everything else reaches the outside through Traefik or an explicit `*-egress` network | measured (nmap from a bridge container: 80/443 only) |
| Removing a stack's edge network from `EDGE_NETWORKS` and recreating Traefik cuts its route, at the cost of a seven-second interruption for every router | measured (N2, F-tests) |
| `access-blocked` exists as a kill switch per router | implemented |
| A host ruleset in its own table, loaded without a flush, with a timed way back | measured (F1–F9) |
| CrowdSec decisions per address, global | implemented |
| No checkpointing: Docker's experimental mode off, CRIU not installed, `runc` only | read on the host |

## Three containment levels

| Level | Cuts | Keeps |
|---|---|---|
| **Ingress** | requests from clients to the application (Traefik route) | the application's outbound connections, its database, its processes |
| **Egress** | the application's connections to the internet and to other stacks | inbound for the operator's investigation; the database |
| **Full** | everything except a forensic path the operator opens deliberately | the processes and their memory |

## Mechanisms compared

| Mechanism | How | Strengths | Limits |
|---|---|---|---|
| Router-level kill switch | the router's access policy to `access-blocked` (label change, container recreate) or a file-provider override router of higher priority | per application; no other router touched; fully in Traefik's logs | a label change recreates the container (destroys runtime state); only ingress through Traefik; a container on a shared network still reaches it |
| Remove from Traefik's edge network | `docker network disconnect <stack>-edge traefik-core` | immediate, no recreate of the suspect; ingress gone | Traefik's own reconnect at its next recreate (`EDGE_NETWORKS`); affects nothing else, but must be reverted deliberately |
| `docker network disconnect` of the suspect | disconnect the container from every network but one quarantine network | processes keep running; precise | a container with `network_mode: host` or `container:` cannot be isolated this way; the application may crash on lost connections (volatile state lost); DNS names on the remaining networks still resolve |
| Dedicated quarantine network | an `internal` network with only the suspect and a forensic container | the operator can still talk to it; no egress | needs the disconnect step first; IPv6 must be disabled on it or equally `internal` |
| nftables quarantine table | a table of its own on the forward hook dropping traffic to and from the container's addresses (both families), matched by its veth or its addresses | no change to Docker's objects; survives a container restart only if matched by name; works for published ports too | addresses change on restart; must not touch Docker's or the VPN's tables; `docker-proxy` paths (userland proxy) bypass it — the blueprint sets `userland-proxy: false` |
| Pause | `docker pause` (cgroup freezer) | freezes processes and memory without killing them | timers and connections time out; the container looks hung to its peers; not a network isolation |
| Stop | `docker stop` | certain | volatile state (memory, open connections, unwritten caches) lost |

A full isolation has to cover: both address families, the published ports (Traefik only
in the blueprint, but a stack with its own binding — the nine "bound" stacks — needs its
port closed too), every network the container is on, a `host` or `container:` network
mode, and alternative paths (a shared network such as `proxy-public`, the Docker socket
through the socket proxy, a VPN client inside a container).

## Evidence and chain of custody

Order of volatility, highest first, and what the blueprint's tools could collect:

1. **Memory** — container processes' memory: `gcore` or `/proc/<pid>/mem` from the host,
   or a VM snapshot of the whole host (provider) — only before any stop or restart.
2. **Runtime state** — `docker inspect`, `docker top`, `/proc/<pid>/{status,net,fd}`,
   `ss` in the container's namespace (`nsenter -n`), conntrack entries.
3. **Network and logs** — Traefik's access log (client addresses since the SNAT fix),
   CrowdSec alerts and decisions, the container's log driver output, the journal.
4. **File system changes** — `docker diff`, `docker export` of the container's layers; the
   blueprint's read-only root filesystems narrow this to tmpfs and volumes.
5. **Volumes and databases** — a copy of the bind mounts, a database dump through the
   stack's documented backup entry.
6. **Configuration** — the stack's directory, `.env` (secrets kept separate), the image digest.

Chain of custody: every collected file hashed (SHA-256) at collection, a manifest with
time, collector, command and source, stored outside the host (read-only medium or
another system), and the isolation steps themselves logged with the same rigour.
Isolation changes volatile data: a disconnect may make the application log errors, retry
and overwrite caches — collect memory and runtime state **before** or **while** isolating.

**Checkpoint/CRIU**: `docker checkpoint create` needs Docker's experimental mode and CRIU;
neither is present on the lab host. CRIU restores a process tree with memory and open
files, but fails on many real applications (open TCP connections without
`--tcp-established`, GPU, some `io_uring`, `memfd`, nested namespaces) and is a large
attack surface itself. **VM snapshots** at the provider capture everything including
memory on some providers, but the whole host, not one container, and they leave the
provider's custody model to the operator.

## Finding what else is affected

Group containers by software component, so that "every container with PHP" or "every
image with libxml2 below version X" is one query:

- **Labels** the stacks already carry (`com.docker.compose.project`, the image) plus a
  proposed `sdb.component=` label per stack;
- **SBOMs** per image (Trivy `--format cyclonedx`) stored with the pin;
- **Runtime facts** — which processes actually run (`docker top`), which libraries are
  loaded (`/proc/<pid>/maps`), which networks connect it to databases and other stacks.

The dependency graph follows from the compose files: application → its `internal`
network → database and cache; `*-egress` → outside; shared networks (`proxy-public`) →
every other member. A compromised application with a database means the database and its
dumps are evidence too.

## Reconnection

After the investigation: rotate the application's secrets, rebuild from the pinned image
(never resume the suspect container), restore data from a backup older than the incident
if integrity is in doubt, reconnect step by step (egress last), watch the access log and
CrowdSec, and record the decision.

## Triggering it

A future CLI (`scripts/incident.sh isolate|collect|reconnect <stack>`) and, on top of it,
an API reachable over the tailnet only — optionally triggered from an iPhone Shortcut.
Requirements before that is safe:

- **Authorization**: a dedicated key or token per operator, scoped to these actions; no
  general shell; a second factor for "full isolation" of a whole host.
- **Audit log**: every request, its result and the evidence hashes, written outside the
  host.
- **Rollback**: every isolation step has its inverse, and a timed automatic revert unless
  confirmed (the firewall block's pattern) — so a mistaken trigger cannot lock the
  operator out.
- **Misuse protection**: rate limit, no action against the management path (SSH, the VPN,
  the console), dry-run by default.
- **Independent confirmation**: after isolating, an outside client and a tailnet client
  measure what is still reachable — the same two-client method as step 8.

## Architecture variants

| Variant | Description | For | Against |
|---|---|---|---|
| A — Docker-native | disconnect + quarantine network + `pause`, driven by a script | simple, no new component | addresses and names change on restart; no host-level guarantee |
| B — nftables-native | one quarantine table on the forward hook, per container sets of addresses | covers every path at the host, both families, independent of Docker's objects | must be kept in sync with container addresses; mistakes reach other containers |
| C — layered | Traefik kill switch (ingress) + nftables egress set + optional disconnect | each level separately; reversible step by step | more moving parts |
| D — host-level | VM snapshot and provider firewall | complete | whole host only; provider-specific |

## Open research questions

1. Does `docker network disconnect` of a running container leave conntrack entries that
   keep existing connections alive, and for how long?
2. Can an nftables set follow a container across restarts by cgroup or veth name rather
   than by address?
3. Which of the blueprint's applications survive a `pause` of minutes without corrupting
   data?
4. Is CRIU usable for the blueprint's single-binary services (Go, Rust) and not for PHP or
   JVM stacks — measured, not assumed?
5. What is the smallest audit trail that a court-grade chain of custody would accept for a
   self-hosted setup?
6. How does a Tailscale-only API stay reachable when the incident is in the VPN itself?
