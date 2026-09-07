# Host-Firewall Remediation — nftables bouncer

Host-level enforcement of CrowdSec decisions, in front of Docker and Traefik.

> **Status.** The architecture below is designed and partly verified. The scoped
> enforcement rules have **not** been runtime-accepted on any host. What is verified
> and what is not is listed under [Verification status](#verification-status). Do not
> enable enforcement from this document before that sequence has passed.

---

## What the firewall bouncer does

CrowdSec separates detection from enforcement. The engine reads logs, matches
scenarios and writes **decisions** — a list of source addresses and how long each
should be blocked. The engine blocks nothing.

The firewall bouncer moves enforcement of that list earlier in the packet path:

```text
CrowdSec decision  →  nftables set  →  DROP on public ingress
                                       →  Docker and Traefik never receive the packet
```

That is the whole contribution: **source-IP decision enforcement, moved earlier**. It
is not a port policy and does not replace one. It cannot decide that a port should be
closed; it only decides that a known-bad source may not continue through a port that
is already open.

## Where each layer acts

Four components with distinct responsibilities. Confusing them is how the wrong one
ends up carrying a job it cannot do.

| Layer | Question it answers | Acts on |
|---|---|---|
| **Provider firewall** (cloud security group) | which public ports may enter at all | ports, before the host |
| **CrowdSec host enforcement** (this document) | which banned source addresses may continue through public ingress | source addresses, on the host |
| **Traefik CrowdSec middleware** | which HTTP requests are refused, and why | requests, after TLS |
| **Management plane** (VPN interface) | who administers the host | a separate interface |

The provider firewall and the host bouncer are complementary rather than alternatives:
one decides which doors exist, the other decides who may walk through them. The Traefik
middleware keeps its own value after both — it sees the decrypted request, can answer
403 with a reason, and leaves an access-log line. The host bouncer leaves nothing to
read, because nothing arrived.

---

## The management-plane invariant

> **Automated CrowdSec blocklists must never be able to remove administrative access.**
>
> This has to hold by firewall topology, not by the contents of an allowlist.

A management interface — Tailscale, WireGuard, any VPN — is a trusted plane. CrowdSec
decisions are generated automatically, from scenarios and from a community blocklist
neither the operator nor this repository controls. Wiring the two together without a
structural separation means an automatic decision can sever administration.

This is not hypothetical. A legitimate `crowdsecurity/http-probing` detection fired on
an administrator's own VPN address — an administrator's browser producing 403 and 404
responses looks exactly like probing, because that is what the scenario measures. With
a global enforcement chain in place, that decision removed the management path.

**Interface scoping is stronger than an allowlist.** The two differ in kind:

- An allowlist is *data*. It can be missing, misspelled, scoped to the wrong list, or —
  as happened here — a configuration key the software silently ignores.
- An interface match is *topology*. A packet arriving on the management interface cannot
  match a rule that requires the public interface, whatever any list contains.

Both are used. The interface match is the guarantee; the allowlist is depth.

### VPN ranges are not RFC1918

CrowdSec's default `crowdsecurity/whitelists` parser covers `127.0.0.0/8`, `10.0.0.0/8`,
`172.16.0.0/12`, `192.168.0.0/16` and `::1`. Tailscale uses the CGNAT range
`100.64.0.0/10` and a ULA range under `fd7a:115c:a1e0::/48`. **Neither is in the default
whitelist**, and CGNAT space belongs to real ISP customers, so those addresses do appear
in community blocklists.

### A parser whitelist is not a universal exclusion

CrowdSec offers two mechanisms that both read as "never act on this address", and they
cover different sets of decisions.

| Mechanism | Applies to |
|---|---|
| Parser whitelist (`crowdsecurity/whitelists`, or a custom parser under `parsers/`) | events the engine derives from the log lines that pass through that parser |
| LAPI AllowList (`cscli allowlists`) | every decision the LAPI serves, whatever produced it |

A parser sits in the engine's own log-processing path. Decisions pulled from the central
API — the community blocklist, enabled by default — never traverse that path: they arrive
as finished decisions. A parser whitelist therefore cannot exempt an address that appears
on a community list, and the bouncer will enforce it.

**When an address or range must be excluded regardless of where the decision came from,
the AllowList is the mechanism that covers that.** A parser whitelist remains the right
tool for suppressing detections the engine would otherwise derive from your own traffic —
a monitoring probe or a known crawler hitting your logs.

The engine-level control is a native LAPI AllowList:

```bash
docker exec crowdsec cscli allowlists create tailnet \
  -d "Trusted VPN management plane"
docker exec crowdsec cscli allowlists add tailnet 100.64.0.0/10 fd7a:115c:a1e0::/48
docker exec crowdsec cscli allowlists check <an-address-in-range>
```

Substitute your own VPN ranges. Adding an allowlist also removes decisions already
covered by it — verified on CrowdSec v1.7.8, which reported `2 decisions deleted by
allowlists` on creation.

---

## Why Docker traffic needs FORWARD, not INPUT

**A maintainer reading only this section must come away unable to reintroduce an
INPUT-only rule and believe Docker is protected.**

A published container port is not a host service. Docker installs a DNAT rule, so the
packet's destination is rewritten to the container address before filtering, and the
packet is then **forwarded** rather than delivered locally:

```text
eth0 → nat PREROUTING → DOCKER (DNAT :443 → container) → routing → FORWARD → container
                                                                     ↑
                                                     this is where enforcement belongs
```

Traffic that terminates on the host — SSH, a VPN's own UDP port — takes the other path
and traverses INPUT. **Published container ports never traverse INPUT.**

The consequence, measured on a running host: an enforcement chain attached to
`hook input` filtered no Traefik traffic at all, while remaining able to drop
management traffic. It had the failure mode without the benefit.

DNAT rewrites only the **destination**. The source address is untouched, so a rule in
FORWARD still matches the real public sender.

---

## set-only architecture

The bouncer's default mode is *managed*: it creates its own table, set and chain, and
installs the DROP rule itself — with no interface restriction. That mode cannot satisfy
the management-plane invariant.

`set-only` mode splits ownership:

```yaml
nftables:
  ipv4:
    enabled: true
    set-only: true
    table: crowdsec
    chain: crowdsec-chain
  ipv6:
    enabled: true
    set-only: true
    table: crowdsec6
    chain: crowdsec6-chain
```

Set-only does not mean "the bouncer creates everything except the chain". Runtime
established the opposite: **the operator owns the objects, the bouncer owns only what is
inside one of them.**

| Owner | Owns |
|---|---|
| **This blueprint** | both tables, both blacklist sets, and the chains with the DROP rules — and therefore the interface scoping |
| **Firewall bouncer** | membership of the two blacklist sets, kept in sync with the LAPI |

Without a pre-existing IPv4 table the bouncer does not start at all:

```text
level=fatal msg="nftables: could not find ipv4 table 'crowdsec'"
```

The two families are not symmetric in this version. Given an existing table, the bouncer
creates a *missing IPv4 set* but never a missing IPv6 set — it fails with `ENOENT`
instead. The blueprint therefore creates **both** sets deliberately. Relying on the IPv4
auto-create would leave a per-family special case for a future maintainer to rediscover,
and it would make "state is ready" two different predicates instead of one.

The blueprint owns the DROP rule because the DROP rule is where the invariant lives. No
configuration key of the bouncer can express "public interface only"; `nftables_hooks`,
`safe_range` and any allowlist key are absent from the 0.0.25 schema. Owning the rule is
the only way to own the scope.

### The set schema

```text
table ip crowdsec {
	set crowdsec-blacklists  { type ipv4_addr; flags timeout }
}
table ip6 crowdsec6 {
	set crowdsec6-blacklists { type ipv6_addr; flags timeout }
}
```

`flags timeout` is the whole schema. The bouncer sets a timeout on every element it
inserts, so a set-level default is unnecessary and would impose one on elements that
arrive without.

:::caution
**Do not add `flags interval`.** nftables accepts it, but this bouncer version cannot
populate an interval set — every commit fails and both sets stay empty. See
[known limitations](#known-limitations).
:::

### The rules

Public interface named `eth0` below — substitute the real one.

```text
# IPv4 — chains only; the table and set come from the preparation step
destroy chain ip crowdsec cs-public-forward
add chain ip crowdsec cs-public-forward \
  { type filter hook forward priority filter - 10; policy accept; }
add rule  ip crowdsec cs-public-forward \
  iifname "eth0" ct original ip saddr @crowdsec-blacklists counter drop

# IPv6 — same architecture, not an afterthought
destroy chain ip6 crowdsec6 cs-public-forward
add chain ip6 crowdsec6 cs-public-forward \
  { type filter hook forward priority filter - 10; policy accept; }
add rule  ip6 crowdsec6 cs-public-forward \
  iifname "eth0" ct original ip6 saddr @crowdsec6-blacklists counter drop
```

`destroy` leads so the file is idempotent; it succeeds when the object is absent.

**`ct original … saddr` rather than `ip saddr`.** It reads the address from the
connection's *original* tuple, which is the initiator's:

| Connection | original saddr | Result |
|---|---|---|
| a banned peer connected inbound | the banned peer | dropped, including a session opened before the ban |
| this host connected outbound, peer later banned | this host | replies keep flowing |

The second row matters because the engine itself makes outbound connections to CrowdSec's
API and hub. A plain `ip saddr` match would drop their replies once such an address
appeared in a blocklist.

**Priority `filter - 10`** places the chain ahead of Docker's and the VPN's chains at
priority 0, so a banned packet is dropped before either does work. Conntrack (prerouting,
−200) and DNAT (prerouting, −100) have both already run, so `ct original` is populated
and the source is intact.

**No INPUT chain.** See [above](#why-docker-traffic-needs-forward-not-input). On a host
whose only host-terminating public traffic is the VPN's own port, an INPUT chain would
protect nothing and could drop VPN packets from a peer whose public address is in a
blocklist. Add one only for a specific host service that is actually exposed, matching
that service's port.

---

## Service lifecycle

**In set-only mode the bouncer does not clean up after itself.** In its default managed
mode it removes its tables on shutdown; set-only behaves differently, and the difference
is asymmetric between the two families:

| On bouncer stop | IPv4 | IPv6 |
|---|---|---|
| blacklist set membership | cleared | **left in place** |
| table | remains | remains |

Stale IPv6 membership surviving into the next start is the hazard this lifecycle exists
to remove. **Cleaning that state is a blueprint responsibility, not the bouncer's.**

### Preparation and cleanup belong to the bouncer's own unit

Two blueprint-owned commands, both added by a drop-in, so no code path can start the
bouncer without passing through preparation:

```ini
[Service]
# Appended after the vendor's own "-t" config check, which stays first.
ExecStartPre=/usr/local/sbin/cs-fw-prepare
ExecStopPost=/usr/local/sbin/cs-fw-cleanup
```

`cs-fw-prepare` applies one atomic nftables transaction that destroys both CrowdSec
tables and recreates them with their sets, then verifies the result — both sets present
and **empty**, zero chains, zero rules, zero verdicts — and exits non-zero if any of that
fails. A failing `ExecStartPre` makes the unit fail, so preparation is fail-closed: the
bouncer cannot run on state that was not rebuilt.

```text
destroy table ip  crowdsec
destroy table ip6 crowdsec6

table ip crowdsec {
	set crowdsec-blacklists  { type ipv4_addr; flags timeout }
}
table ip6 crowdsec6 {
	set crowdsec6-blacklists { type ipv6_addr; flags timeout }
}
```

`destroy` leads and is documented as not failing when the object is absent, so the
transaction is idempotent. Because destroy and create are one transaction, the set that
exists afterwards is provably new and empty — stale membership cannot cross the boundary
even if cleanup did not run.

`cs-fw-cleanup` destroys only those two tables and is idempotent. It runs on a normal
stop, on a restart, on an unexpected process failure, and — because `ExecStopPost` is
specified to run when a service fails to start — after a failed start too.

Since the scoped chains live *inside* the CrowdSec tables, destroying a table removes
chain and set together. There is never a chain left consuming a set that no longer exists.

:::danger
Cleanup must name only the two CrowdSec tables. Never `nft flush ruleset`, and never
restore a whole-host nftables snapshot over Docker and VPN state.
:::

### Why a separate preparation unit was rejected

A `Type=oneshot` unit with `RemainAfterExit=yes` stays `active` after its first run, so a
`Requires=` on it is already satisfied and systemd does **not** re-run it when the bouncer
restarts — exactly the case that must never be missed. `ExecStartPre` is inside the
bouncer's own start job and therefore runs on every start, restart and failed-start
recovery, with no extra unit to keep consistent.

### The enforcement companion

```ini
[Unit]
After=crowdsec-firewall-bouncer.service
BindsTo=crowdsec-firewall-bouncer.service
PartOf=crowdsec-firewall-bouncer.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=<readiness gate, bounded>
ExecStart=<install the chains>
ExecStop=<remove the chains>
```

The bouncer pulls it with `Wants=crowdsec-fw-scope.service` — deliberately weak, so a
companion failure leaves the bouncer running set-only with no enforcement. Fail-open beats
unintended blocking.

Each directive earns its place. `After=` orders the companion behind the bouncer, and
because shutdown is the reverse of startup, that same directive is what removes the chains
*before* the bouncer stops. `PartOf` re-runs it when the bouncer restarts; `BindsTo` stops
it when the bouncer stops unexpectedly or fails. `Requires=` would be redundant — `BindsTo`
already includes its effects.

### The readiness gate

**Set existence is not readiness.** Measured repeatedly on a live host:

| Moment after bouncer start | State |
|---|---|
| ~0 s | both sets exist, both **empty** |
| ~1.05 s | first elements appear |
| ~1.4 s | roughly 14 % of the IPv4 data present |
| ~11.4–11.7 s | fully populated |

So `table exists`, `set exists`, `set non-empty` and a fixed `sleep` are all unsafe gates:
each one releases while the blocklist is still mostly missing.

The bouncer logs a completion line, but that line alone is also insufficient — it is
emitted even when the netlink commits failed and the sets stayed empty. The gate therefore
combines four conditions:

1. a log anchor written by the current `ExecStartPre`, so only this invocation's output is
   examined and a previous start's success can never be matched;
2. the `decisions added` completion line after that anchor;
3. no `unable to commit` error in the same window;
4. functional confirmation that **both** sets actually contain data.

It is bounded — 60 s — and on timeout it exits non-zero, the companion does not activate,
and no verdict exists anywhere. The bouncer keeps running set-only.

### The engine runs in Docker, so ordering is not automatic

The package's unit orders itself `After=crowdsec.service`, which assumes a
host-installed engine. This blueprint runs the engine in a container, so that unit does
not exist and the ordering has no effect. On a cold boot the bouncer reached the LAPI
before the container runtime had started, logged `connection refused`, removed its own
tables and exited **0** — which `Restart=on-failure` would not catch, and the packaged
unit sets no `Restart=` at all.

A drop-in supplies what the vendor unit cannot know: ordering after the container
runtime, `Restart=always` with a delay, and a bounded readiness wait for the LAPI socket
itself. Waiting for the runtime is not enough — the daemon being active does not mean the
container has bound the published port.

---

## Setup

> Complete the [acceptance sequence](#acceptance-sequence) before enabling this on a
> host you rely on. The steps below install and configure; they do not by themselves
> make enforcement safe.

### 1. Install the package on the host

```bash
sudo apt install crowdsec-firewall-bouncer   # Debian 13, from Debian main
```

:::note
**The package name depends on where you get it from.** Debian 13 ships one package,
`crowdsec-firewall-bouncer`, from its own archive, and no extra repository is needed.
CrowdSec's own repository splits it by backend into `crowdsec-firewall-bouncer-nftables`
and `-iptables`, so guides written against that source name a package Debian 13 does not
have. Check with `apt policy crowdsec-firewall-bouncer` before assuming either.
:::

The `cscli not found, no automatic registration` warning during installation is expected
— the engine runs in a container, not on the host. Registration is the next step.

The package creates two files. Edit only the second:

- `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml` — managed by the package
- `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml.local` — your overrides

### 2. Generate an API key

```bash
docker exec crowdsec cscli bouncers add firewall-bouncer
```

The key is shown once. To replace a lost one, delete the entry and add it again.

### 3. Configure set-only mode

In the `.yaml.local` override:

```yaml
api_url: http://127.0.0.1:8080/
api_key: <key from step 2>
mode: nftables
deny_action: DROP

nftables:
  ipv4:
    enabled: true
    set-only: true
  ipv6:
    enabled: true
    set-only: true
```

`set-only` is the key that keeps the bouncer out of the DROP rule. Without it the bouncer
installs its own unscoped chain, which is the configuration this document exists to
replace. Check the spelling against the shipped `.yaml` — an unknown key is accepted
silently.

`api_url` points at the LAPI the engine publishes on loopback. It is a host-local surface
reachable by any process on the host, and it is not reachable from a container, which is
why the bouncer runs on the host.

### 4. Install preparation and cleanup

Install `cs-fw-prepare` and `cs-fw-cleanup` and the drop-in that calls them, as described
under [service lifecycle](#service-lifecycle). Start the bouncer once and confirm both
sets are created empty and then populate, with zero chains and zero verdicts throughout.
This step installs no enforcement.

### 5. Install the scoped chains, then enable

The companion unit installs [the rules](#the-rules) behind the
[readiness gate](#the-readiness-gate), and must be in place before the bouncer is enabled
— otherwise the sets exist with nothing consuming them, which enforces nothing. Follow the
[safe change procedure](#safe-change-procedure) rather than `systemctl enable --now`.

---

## Safe change procedure

**No firewall change may depend on the current SSH session surviving.** Two independent
safeguards, both required.

### Live dead man

<!-- markdownlint-disable-next-line MD029 -->
1. Arm an independent timed rollback **before** applying anything, and prove it armed
   with `systemctl list-timers`.
2. Apply the change.
3. Validate from a **second, independent client** — never the session applying it.
4. Cancel the rollback only after every gate passes.

Mandatory gates, all as **new** connections, because an existing one passes on
conntrack state and proves nothing:

- management-plane SSH over IPv4
- management-plane SSH over IPv6
- public IPv4 HTTPS
- public IPv6 HTTPS
- one Docker/Traefik route
- a banned public source is dropped

The IPv4 and IPv6 management gates are both listed on purpose. In the incident that
produced this document, IPv6 kept working only because no decision existed for that
address yet; the same machine was banned on IPv6 shortly afterwards. **IPv6 is not a
recovery path.**

### Reboot guard

A timer does not survive a reboot, so a reboot test needs a persistent gate: an enabled
oneshot ordered *before* the bouncer, which the bouncer `Requires=` and is ordered
`After=`.

| Confirmation token | Guard | Result |
|---|---|---|
| present | exits 0 | bouncer may start, companion may start |
| absent | runs the bounded rollback, **exits non-zero** | bouncer is not started; companion cannot start |

The non-zero exit is the whole mechanism. `systemd.unit(5)` states that if a required
unit *fails to activate* and `After=` is set, the dependent unit is not started. Two
traps follow from the same paragraph:

- The check must be **script logic returning an exit code**, never `ConditionPathExists=`.
  A failing condition is a skip, not a failure, and does not gate a `Requires=` dependent.
- `systemctl disable` removes `[Install]` symlinks only. It neither stops a unit nor
  prevents activation pulled in by another unit's `Requires=`, so it cannot serve as the
  gate.

The guard and the temporary dependency are **rollout tools**. Remove both after
acceptance — a permanent `Requires=` on a removed unit makes the bouncer fail to start on
every later boot.

### Rehearse the guard before trusting it

A guard that has never fired is an assumption. Rehearse it with an inert object — an
nftables chain containing a `counter` and no verdict, which cannot affect connectivity —
and a dummy gated service standing in for the bouncer.

The rehearsal must mirror the **three** production units, not two:

```text
guard  →  loader  →  dummy
```

The loader stands in for `ExecStartPre` and recreates the inert object on every start. A
two-unit rehearsal that creates the object by hand proves nothing across a reboot: nothing
recreates it, so its absence afterwards is the harness failing rather than the guard. Gate
the dummy on the *loader*, not on the guard, so the chain is the one production will use.

Prove **both** branches across real reboots: without the token the guard exits non-zero,
the loader never executes, the dummy never executes and systemd reports a dependency
failure; with the token the guard exits 0, the loader recreates the object, and the dummy
runs after it.

---

## Recovery

Bounded rollback. Every command names a CrowdSec-owned object:

```bash
sudo systemctl disable --now crowdsec-fw-scope.service
sudo systemctl disable --now crowdsec-firewall-bouncer.service
sudo nft destroy table ip  crowdsec
sudo nft destroy table ip6 crowdsec6
```

`nft destroy` succeeds when the object is absent, so this is safe to run repeatedly and
safe for an unattended guard.

:::danger
**Never `nft flush ruleset`, and never restore a whole-ruleset snapshot.** Docker and the
VPN daemon rewrite host netfilter state continuously. Flushing removes their rules along
with CrowdSec's, and restoring a snapshot reinstates a view of their state that has since
moved on. Recovery must name only CrowdSec's own objects.
:::

The fastest partial lever is stopping the bouncer alone. `ExecStopPost` destroys both
tables, and because the companion's chains live inside them they go with them — but that
is the blueprint's cleanup doing the work, not the bouncer. In set-only mode the bouncer
leaves its tables behind, and leaves IPv6 membership stale. Without the cleanup in place,
stop the service **and** destroy both tables explicitly.

---

## SSH detection — what makes host-firewall remediation worth it

Without SSH detection, this layer only enforces bans triggered by Traefik access logs —
the same decisions reverse-proxy remediation already covers. It adds real value when it
also catches
threats that never touch Traefik. SSH brute force is the primary case.

This is opt-in because not every deployment has a publicly reachable SSH port.

### When to enable

Enable if any of the following are true:

- Port 22 (or any SSH port) is reachable from the internet
- You have seen repeated failed logins in `/var/log/auth.log`
- You want to ban IPs that combine SSH probing with web attacks

Skip if SSH is accessible only via Tailscale or WireGuard and no unauthenticated path
to it exists from the internet.

### Step 1 — Add the sshd collection

In `.env`, extend `CROWDSEC_COLLECTIONS`:

```bash
# Before:
CROWDSEC_COLLECTIONS=crowdsecurity/traefik crowdsecurity/http-cve ...

# After — append crowdsecurity/sshd:
CROWDSEC_COLLECTIONS=crowdsecurity/traefik crowdsecurity/http-cve ... crowdsecurity/sshd
```

### Step 2 — Mount the SSH log into the container

First confirm where SSH authentication events are written on your system:

```bash
ls -l /var/log/auth.log
# Debian 12, Ubuntu 22.04+: auth.log exists → use /var/log/auth.log
# If "No such file or directory":
#   Ubuntu with systemd-journald only: check journalctl -u ssh
#   Some systems write to /var/log/syslog instead → use /var/log/syslog
#   Rocky/AlmaLinux: /var/log/secure
```

The file must exist **before** the CrowdSec container starts and must be readable by
the GID configured in `.env` (`CROWDSEC_LOG_GID`). Verify the file is readable:

```bash
stat -c '%G %a' /var/log/auth.log
# Note the group name and check that CROWDSEC_LOG_GID matches that group's GID:
getent group <group-name>
```

> **Note on journald-only systems:** If your distro writes SSH logs exclusively to the
> systemd journal (no flat log file), CrowdSec cannot read them via file acquisition.
> Enable traditional syslog forwarding (`ForwardToSyslog=yes` in
> `/etc/systemd/journald.conf`) or use the CrowdSec journald acquisition source instead
> — which requires additional configuration not covered here.

In `docker-compose.yml`, uncomment the SSH log volume mount (adjust the path if your
system uses `/var/log/syslog` or `/var/log/secure`):

```yaml
# Before (commented out):
# - /var/log/auth.log:/var/log/auth.log:ro

# After:
- /var/log/auth.log:/var/log/auth.log:ro
```

### Step 3 — Activate the acquisition source

In `config/acquis.yaml`, uncomment the SSH block:

```yaml
---
filenames:
  - /var/log/auth.log
labels:
  type: syslog
```

### Step 4 — Restart the engine

```bash
docker compose up -d --force-recreate crowdsec
```

Wait ~5 minutes for the collection to install and the parser to begin reading.

### Step 5 — Verify SSH detection

```bash
# 1. Is auth.log being parsed?
docker exec crowdsec cscli metrics show acquisition
# Expected: a row for file:/var/log/auth.log with lines_read > 0

# 2. Is the sshd collection installed?
docker exec crowdsec cscli collections list | grep sshd
# Expected: crowdsecurity/sshd  ✔  enabled

# 3. Are SSH scenarios active?
docker exec crowdsec cscli scenarios list | grep ssh
# Expected: crowdsecurity/ssh-bf, crowdsecurity/ssh-slow-bf (and others)
```

SSH bans appear automatically once brute-force patterns are detected. The threshold
is 5–10 failed attempts depending on the scenario. The firewall bouncer picks up new
decisions within ~10 seconds:

```bash
# Check for active SSH bans (look for reason "crowdsecurity/ssh-bf"):
docker exec crowdsec cscli decisions list
```

### Optional: verify the full detection chain end-to-end

This confirms that the complete path works: auth.log event → parser → engine decision
→ firewall bouncer rule. It does not require brute-forcing a real SSH service.

**Method:** inject a synthetic failed-login line directly into the log file that
CrowdSec is monitoring, then check whether the engine parses it and produces an alert.

```bash
# 1. Note the current alert count (baseline)
docker exec crowdsec cscli alerts list | wc -l

# 2. Write a single synthetic failed-login line in the format sshd uses.
#    Use a documentation IP (203.0.113.x range) — never a real address.
#    The exact format must match what your sshd version writes.
echo "$(date '+%b %d %H:%M:%S') $(hostname) sshd[99999]: Failed password for invalid user testuser from 203.0.113.99 port 54321 ssh2" \
  | sudo tee -a /var/log/auth.log

# 3. Wait ~30 s for CrowdSec to parse the new line, then check:
docker exec crowdsec cscli metrics show acquisition
# Expected: lines_read for auth.log has increased by 1

# 4. A single line will not trigger a ban (threshold is 5–10 events).
#    To confirm parsing without triggering a scenario, check the parser hit count:
docker exec crowdsec cscli metrics show parsers
# Expected: crowdsecurity/sshd-logs shows a hit for the injected line

# 5. Clean up — the synthetic line is harmless but tidy to remove:
sudo sed -i '/testuser.*203\.0\.113\.99/d' /var/log/auth.log
```

> **What a real SSH ban looks like once traffic flows:**
> After genuine brute-force attempts accumulate, `cscli decisions list` will show an
> entry with `reason: crowdsecurity/ssh-bf`. Within ~10 s, the banned IP will
> appear as an element in the nftables set — verifiable with
> `sudo nft list set ip crowdsec crowdsec-blacklists` (see "`nft list chain`
> vs. `nft list set`" note in the Verify section above).

---

---

## Edge cases

### IPv6

If your host has an IPv6 address reachable from the internet, the firewall bouncer
covers IPv6 automatically — CrowdSec creates both `ip` (IPv4) and `ip6` (IPv6) chains.
Verify both exist after a ban:

```bash
sudo nft list ruleset | grep -E "table ip"
# Expected: entries for both `ip crowdsec` and `ip6 crowdsec`
```

No additional configuration is needed; the bouncer handles both address families.

### Private ranges are not automatically exempt

There is **no `safe_range` option.** It is absent from the 0.0.25 configuration schema,
and a configuration containing it passes `-t` validation reporting `config is valid`
while having no effect whatsoever. The same applies to `deny_mode`; the real key is
`deny_action`.

**Unknown YAML keys are silently accepted.** A configuration test proves the file parses.
It does not prove that a safeguard written in it is read by anything. Verify a claimed
option against the installed package before relying on it.

Exemptions come from the two mechanisms that do exist: a LAPI AllowList at the engine,
and the interface match in the DROP rule.

---

## Troubleshooting

Confirmed cases only.

| Symptom | Cause | Resolution |
|---|---|---|
| Administrator's own address is banned | A scenario matched real management traffic. 403 and 404 responses from an admin browser look like probing to `http-probing`. | Add the VPN ranges to a LAPI AllowList; existing covered decisions are removed with it |
| A configured safeguard has no effect | Unknown YAML key, silently accepted at validation | Check the key against the installed package's shipped default configuration |
| Bouncer exits `0/SUCCESS` seconds after boot | It reached the LAPI before the container runtime started; it treats that as a clean exit | Drop-in with ordering, a bounded LAPI readiness wait, and `Restart=always` — `on-failure` never fires on exit 0 |
| Bans disappear after stopping the service | Expected. Blueprint cleanup destroys both tables on stop | Restart it; do not rely on rules persisting |
| A `/24` ban blocks only one address | Range decisions degrade to their network address in this bouncer version | None available — see [known limitations](#known-limitations) |
| Repeated `can't collect dropped packets` in the log | The metrics collector looks for a counter in a bouncer-owned chain, which set-only does not create | Harmless; leave metrics enabled |
| `set-only` configured but a base chain appears | The mode was not applied | Stop, roll back, and re-check the key spelling against the shipped schema before continuing |
| Public traffic to a container is not filtered | Enforcement attached to INPUT; published ports traverse FORWARD | Move the rule to `hook forward`, keeping the ingress-interface match |
| Management access lost while enforcement is active | A decision exists for a management address **and** the DROP rule lacks an ingress-interface match | Stop the bouncer to restore access, then fix the rule scope — not the decision |

---

## Known limitations

Both are properties of `crowdsec-firewall-bouncer 0.0.25-5+b11`, established on a live
host. Neither is a management-lockout risk.

### CIDR and range decisions are not enforced at the host

A CrowdSec decision with `--scope range` reaches the set as **its network address only**.
A controlled test with `192.0.2.0/24` produced exactly one element, `192.0.2.0`; every
other address in the range was absent. The bouncer reported `1 decision added` and logged
no error.

nftables is not the constraint. An interval-capable set represents the whole prefix
correctly, holds individual addresses alongside it, and keeps per-element timeouts — all
verified directly. But this bouncer version cannot populate such a set: every commit fails
with `unable to commit add decisions … file exists` and both sets stay empty, which is
strictly worse than the degradation it would fix. The compiled binary contains no
interval-set support, and the distribution offers no newer package.

**Host enforcement therefore covers individual source-IP decisions, IPv4 and IPv6.** It
does not provide correct range enforcement, and must not be described as full parity with
CrowdSec's decision model. This is a coverage limit, not a safety one: it blocks less than
intended, never more, and cannot affect the management plane.

### A harmless recurring metrics warning

Set-only logs `can't collect dropped packets for ipv4/ipv6 from nft` every collection
interval, because the collector expects a counter in a bouncer-owned chain that set-only
never creates. Setting `prometheus.enabled: false` silences it completely and set
synchronisation continues — but it also removes the entire bouncer metrics endpoint.
**Keep metrics enabled and accept the noise**; observability is worth more than a quiet
log.

---

## Verification status

| Property | Status |
|---|---|
| LAPI AllowList covers VPN ranges; covered decisions removed on creation | **verified**, CrowdSec v1.7.8 |
| Detection still bans a non-allowlisted source after allowlisting | **verified** by controlled test |
| `nftables.ipv4.set-only` / `ipv6.set-only` exist in the package schema | **verified**, `crowdsec-firewall-bouncer 0.0.25-5+b11` |
| `safe_range` and `deny_mode` are not configuration keys | **verified** |
| Unknown YAML keys pass validation | **verified** |
| Published container ports traverse FORWARD, not INPUT | **verified** on a running host |
| Managed mode removes its tables on stop; **set-only does not** | **verified** |
| Global managed mode can block the management plane | **verified** — it happened |
| `set-only` installs no chain, no rule and no verdict | **verified** on a live host |
| Operator must pre-create both tables; IPv6 set is never auto-created | **verified** |
| Set-only stop clears IPv4 membership but leaves IPv6 stale | **verified** |
| Blueprint preparation and cleanup lifecycle, incl. restart | **verified** — stale IPv6 state cannot survive |
| Readiness gate, both release and bounded failure | **verified**, fail-open |
| Reboot guard, both branches across real reboots | **verified** |
| Range decisions degrade to the network address | **verified** by controlled test |
| Scoped chains install and carry exactly one rule per family, each with the ingress-interface match, at `hook forward` priority `filter - 10` | **verified** on a live host |
| No CrowdSec chain on `hook input`, and no CrowdSec rule referencing the management interface | **verified** by auditing the whole ruleset |
| Restart ordering with enforcement active — chains removed, state rebuilt, chains restored behind the gate | **verified** |
| Companion failure leaves the bouncer set-only with no chain and no verdict | **verified**, fail-open |
| `ct original … saddr` — outbound half: a host- or container-originated connection to a listed remote is not dropped | **verified** |
| `ct original … saddr` — inbound half: an established connection dropped once its source is listed | **not verified** |
| Enforcement against a real banned source, IPv4 and IPv6 | **not verified** — needs a source whose traffic the operator controls |
| Management-plane adverse test initiated *by* an independent client | **not verified** — host-initiated flows only |

### Acceptance sequence

1. VPN LAPI AllowList — **done**
2. Harmless reboot-guard rehearsal, both branches — **done**
3. `set-only` observation: sets created, no base chain, then stop — **done**
4. State-lifecycle rehearsal: preparation, restart, cleanup, readiness gate — **done**
5. Scoped FORWARD enforcement installs and behaves structurally as designed — **done**,
   under a timed rollback, then removed again
6. Adverse management test — a new connection *initiated by an independent client* over
   the management interface works while that client's address sits in the set
7. Public ban test — a banned source is dropped before TLS, IPv4 and IPv6
8. Reboot test with the guard in place
9. Acceptance — remove the guard and the temporary dependency

**Lifecycle, readiness and the shape of the enforcement rules are verified; enforcement
against real traffic is not.** Steps 6 to 8 all need one thing the test host did not
have: a second machine whose traffic the operator controls, reachable both over the
management network and from the public internet. Step 5 does not need repeating.

---

## Removal

```bash
# 1. Stop and disable the service
sudo systemctl disable --now crowdsec-firewall-bouncer

# 2. Remove the nftables tables entirely (chain, rule, and set together —
#    more thorough than flushing, appropriate here since the package is
#    being removed anyway and nothing needs to keep enforcing)
sudo nft delete table ip crowdsec 2>/dev/null || true
sudo nft delete table ip6 crowdsec6 2>/dev/null || true

# 3. Uninstall the package
# Debian 13 / Trixie:
sudo apt remove crowdsec-firewall-bouncer
# Upstream/packagecloud install:
# sudo apt remove crowdsec-firewall-bouncer-nftables

# 4. Remove the bouncer registration from the engine
docker exec crowdsec cscli bouncers delete firewall-bouncer
```

Core and reverse-proxy remediation are unaffected by removal.
