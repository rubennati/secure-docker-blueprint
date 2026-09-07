# CrowdSec firewall bouncer — management-plane lockout — 2026-08-28

Host-level CrowdSec enforcement removed administrative access over the VPN management
interface. The record exists for the architecture it produced, not for the sequence of
events.

---

## Symptom

After a reboot, SSH over the management interface's IPv4 address stopped answering.
The same host stayed reachable over the management interface's IPv6 address. Nothing
else was affected: the proxy, the containers and public routing were healthy throughout.

Stopping `crowdsec-firewall-bouncer` restored IPv4 access immediately.

## Root cause

A legitimate detection banned an administrator's own address, and the enforcement rule
had no ingress-interface restriction, so it applied to the management interface as well
as the public one.

```text
crowdsecurity/http-probing  →  ban on the admin address
                            →  nftables set
                            →  chain at `hook input`, no iifname match
                            →  packets from that address dropped on EVERY interface
```

The detection was correct. An administrator's browser producing 403 and 404 responses is
what `http-probing` measures, and the scenario has no way to know the source is trusted.

## Contributing factors

Each one alone would have been survivable. Together they made the lockout reachable.

| Factor | Detail |
|---|---|
| Management plane not separated | The enforcement chain matched on source address only, so it applied to every ingress interface. |
| VPN ranges absent from the default whitelist | `crowdsecurity/whitelists` covers `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`. Tailscale's `100.64.0.0/10` is CGNAT and its IPv6 range is a ULA; neither is included. |
| A safeguard that did not exist | The repository documented `safe_range` as a hard guarantee. It is not a configuration key in `crowdsec-firewall-bouncer 0.0.25`. The host carried a five-entry `safe_range` list that nothing read. |
| Unknown keys pass validation | The configuration containing `safe_range` — and `deny_mode`, also not a key — reported `config is valid`. A passing config test proved only that the YAML parsed. |
| The rule protected nothing it was for | The chain sat at `hook input`. Published container ports are DNAT'd and traverse `FORWARD`, so no proxy traffic was ever filtered. It had the failure mode without the benefit. |
| Boot persistence made it reliable | The bouncer had been exiting `0` at boot because it reached the LAPI before the container runtime started. Fixing that made a previously inert misconfiguration active on every boot. |

## Why IPv6 survived, and why that is not a recovery path

The decision named a single IPv4 address. The administrator's IPv6 address was a
different address with no decision against it, so the IPv6 set could not match it.

That is coincidence, not architecture. Within hours the same machine was banned on its
IPv6 address as well, by `crowdsecurity/http-probing` and `crowdsecurity/http-crawl-non_statics`.
Had enforcement been active then, both management paths would have closed together.

**Treat IPv4 and IPv6 as one management plane.** Validate both, always as new
connections — an existing connection passes on conntrack state and proves nothing.

## Also established

- **The bouncer removes its own nftables tables on shutdown — in *managed* mode.** Its log
  records `removing 'crowdsec' table` and `removing 'crowdsec6' table`, and none remain
  afterwards. Documentation claiming rules persist after a service stop was wrong. Later
  work established that set-only mode behaves differently and this cleanup cannot be
  assumed; see [set-only ownership](#set-only-ownership-was-the-opposite-of-what-was-assumed)
  below.
- **`nft flush ruleset` is not a rollback.** Docker and the VPN daemon own large parts of
  host netfilter state and rewrite it continuously. Recovery must name only CrowdSec's
  own objects.

## Later findings, and the assumptions they cost

Everything above was established while recovering from the lockout. The findings below
came from the rehearsals that followed, each one starting from a plausible assumption that
runtime disproved. They are kept because the assumptions are the reusable part.

### A reboot rehearsal that could not have passed

The first harmless reboot rehearsal used two units — a boot guard and a dummy standing in
for the bouncer — and an nftables object created by hand. After the reboot the object was
gone, so the criterion "the object survives" could not be evaluated.

The guard itself was never at fault. `nftables.service` is disabled on this host and
nothing recreated the object, so its absence measured the harness, not the gate. A
rehearsal that assumes ephemeral kernel state persists across a reboot is testing nothing.

The corrected harness added the missing production element:

```text
guard  →  loader  →  dummy
```

The loader recreates the object on every start, exactly as `ExecStartPre` will in
production, and the dummy is gated on the *loader* rather than the guard. Both branches
then passed across real reboots: without the confirmation token the guard exited 1, the
loader never executed, the dummy never executed and systemd reported a dependency failure;
with the token the guard exited 0, the loader recreated the object and the dummy ran after
it.

> **Rehearse the object's lifecycle, not just the gate.** A reboot test must reproduce how
> the future object comes back, or its absence afterwards proves nothing.

### set-only ownership was the opposite of what was assumed

The design assumed the bouncer would create tables and sets and merely skip the chain.
Runtime showed the operator owns the objects:

| Behaviour in set-only | Observed |
|---|---|
| both tables must already exist | without the IPv4 table: `fatal: could not find ipv4 table 'crowdsec'` |
| missing IPv4 set | created by the bouncer |
| missing IPv6 set | **not** created — `ENOENT` |
| on stop: IPv4 membership | cleared |
| on stop: IPv6 membership | **left stale** |
| on stop: both tables | **left present** |

The stale IPv6 membership is the dangerous half. Left alone it would be inherited by the
next start and could become active enforcement without ever having been re-checked against
CrowdSec.

The fix is a blueprint-owned `ExecStartPre` that destroys and recreates both tables in one
atomic transaction, and an `ExecStopPost` that destroys them. Runtime confirmed the whole
cycle: on restart the old IPv4 set fell to zero while IPv6 still held its stale members,
cleanup then destroyed both tables, the recreated tables carried **new object handles**,
a tracked IPv6 member was absent from the fresh set, and it returned only after the new
synchronisation delivered it.

### "The set exists" is not "the bouncer is ready"

Population is gradual: first elements after ~1.05 s, roughly 14 % of the IPv4 data at
~1.4 s, complete at ~11.4–11.7 s. A companion gated on table existence, set existence, set
non-emptiness or a fixed sleep would install DROP rules against a mostly empty blocklist.

The obvious alternative — the bouncer's own `N decisions added` completion line — is also
insufficient on its own, for a reason the next finding explains.

### A `/24` that blocked one address, and a fix that was worse

A controlled `192.0.2.0/24` range decision produced exactly one set element, `192.0.2.0`.
The rest of the range was unprotected. The bouncer reported `1 decision added` and logged
nothing wrong.

The apparent fix was to give the sets `flags interval`. nftables supports it: an
interval set was shown directly to hold the whole prefix, coexist with individual
addresses, and keep per-element timeouts. But the bouncer cannot populate one — every
commit failed with `unable to commit add decisions … file exists` and **both sets stayed
completely empty**, which is worse than the degradation it was meant to repair.

And immediately after those failed commits the bouncer logged `23922 decisions added`.
That is why the readiness gate cannot trust the completion line alone, and must also
confirm that data actually landed in both sets.

> **A success log is a claim, not evidence.** Verify the effect, not the report — the same
> lesson `safe_range` taught at the configuration layer, repeated at the runtime layer.

---

## Resulting architecture

1. A native LAPI AllowList carries the VPN ranges, so decisions for them are not created
   or served. Verified: adding it also removes decisions already covered.
2. The bouncer runs in nftables `set-only` mode and maintains only the IPv4 and IPv6
   blacklist sets.
3. The blueprint owns the DROP rule, because the rule is where the scope lives.
4. Enforcement attaches to `hook forward` with an explicit ingress-interface match on the
   public interface, so management traffic cannot match it.
5. No generic INPUT chain.
6. IPv4 and IPv6 are configured identically.
7. Rollback is bounded to CrowdSec-owned objects, and firewall changes are gated by a
   timed dead man and a persistent reboot guard.
8. The blueprint owns both tables and **both** sets, rebuilds them cleanly on every
   bouncer start and destroys them on stop, so stale membership cannot reach enforcement.
9. The enforcement companion waits on a readiness gate that confirms this invocation
   completed a synchronisation which actually landed in both sets, and fails open.

The allowlist is defence in depth. The interface match is the guarantee: an allowlist is
data that can be wrong, an interface match is topology that cannot be bypassed by a
decision.

## The reusable rule

> Never attach automated source-IP enforcement globally on a host that also carries a
> private management plane. Scope it to the public ingress interface, and verify a
> claimed safeguard against the installed software before relying on it.

## Status

The corrected architecture is designed and partly verified; the scoped enforcement is not
yet runtime-accepted. Current status and the remaining acceptance sequence:
[`core/crowdsec/docs/firewall-bouncer.md`](../../core/crowdsec/docs/firewall-bouncer.md)
→ "Verification status".
