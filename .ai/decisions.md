# Decisions

Architecture and governance decisions with their reasoning, newest first. The full
rationale for structural decisions lives in [`../docs/architecture.md`](../docs/architecture.md);
this file is the index and covers decisions that have no other home.

---

## 2026-07 · Two troubleshooting documents, one entry point

`TROUBLESHOOTING.md` is the symptom index and the place to start: what you
observe, its cause, its fix, including app-specific traps. `docs/standards/troubleshooting.md`
is the method — which layer is broken, and the commands that interrogate each one.
Both were catalogues without a stated relationship; neither is merged, because the
deep links from Traefik, CrowdSec and the IPv6 documentation already follow that
split. Owners are in the File Map.

## 2026-07 · Register follows the section purpose, not the repository

The neutral-language rule was written for German drafts and its scope over the
English documentation was never stated. Resolved at `writing-style.md`: imperative
and direct address where the reader performs steps, declarative and neutral where
they establish what is true. No repository-wide language rule overrides a section
contract.

## 2026-07 · Backup agent runs on the host

A containerised backup agent needs `/:/host:ro` or `--privileged` to reach other
stacks' data — which makes it a container able to read every secret in the
deployment. The security baseline already treats the Portainer Agent's host mount as
its one documented deviation of that kind.

Database consistency still reaches into containers: Borgmatic's `container:` option
(2.0.8+) resolves the address through Docker and dumps without published ports.

**Open:** this conflicts with the portability design goal in `architecture.md`
("no host-specific assumptions beyond Debian + Docker"). Needs to be recorded there
as an explicit exception, or revisited — carried in `state.md` as the open decision
on the host-installed agent.

## 2026-07 · Backup covers two directions

`backup/` covers the host outward (Borgmatic) and the operator's own devices inward
(UrBackup). They solve different problems; neither replaces the other. Kopia stays
a named alternative for operators wanting a UI or object storage.

## 2026-07 · One status model, two axes

Public status (what an operator can rely on) and internal status (what the
maintainer has established) are separate axes with a defined mapping. The ten
The baseline-aligned criteria are the single gate between them. Full definition in
[`../docs/standards/status-model.md`](../docs/standards/status-model.md).

**Reason:** three status systems previously ran in parallel with no derivation
between them, so drift was structural rather than accidental.

## 2026-07 · LIFECYCLE.md is generated

Derived from the owning files by `scripts/ci/lifecycle-report.py`, never hand-edited.
The previous hand-maintained version covered 6 of 54 stacks, was three months stale,
and claimed backup documentation that no stack had.

## 2026-07 · One canonical app template

`apps/_reference/` is the only template — runnable, not a paper skeleton. The former
`docs/templates/` was folded into it.

## 2026-06 · IPv6 dual-stack is opt-in

`proxy-public` stays IPv4-only by default so existing installations are unaffected;
`network-dual-stack.yml` enables IPv4+IPv6. Tailscale ingress needs it to preserve
real client IPs. See `core/traefik/docs/ipv6-dual-stack.md`.

## 2026-04 · Five top-level categories, split by access pattern

Not by audience. `monitoring/` and `backup/` are top-level rather than under `apps/`
because they reach across service boundaries and need broader permissions.
Established in v0.2.0 as the Structure Stable Baseline — forks can rely on it.

## 2026-04 · Choice-matrix instead of defaults

Where several tools compete, multiple options are included and the operator picks by
preference. Applies to dashboards, photo galleries, wikis, form builders, uptime
monitoring. Documented per category README.

**Narrow exception:** for deduplicating backup tools one is recommended, because two
repositories mean two retention policies and two restore rehearsals — a real
operational cost that does not exist for monitoring tools covering different axes.

## 2026-04 · Hub-and-spoke networking per app

`proxy-public` shared and external; `app-internal` per app with `internal: true`.
Databases never join the public network and never publish a host port.

## 2026-04 · Config in git, secrets and data never

The compose file and `.env.example` are the portable artifact. `.env`, `.secrets/`
and `volumes/` stay on the host.

## 2026-04 · Security-first with documented exceptions

Hardening is the default; relaxing a control requires a written, per-app exception.
Deviations are never silent.
