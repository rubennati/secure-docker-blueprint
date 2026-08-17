# Decisions

Architecture and governance decisions with their reasoning, newest first. The full
rationale for structural decisions lives in [`../docs/architecture.md`](../docs/architecture.md);
this file is the index and covers decisions that have no other home.

---

## 2026-08 · Binary controls and values have separate owners

`security-baseline.md` owns the controls that are on or off: `no-new-privileges`,
`cap_drop`, secrets through Docker Secrets or `_FILE`, socket access, network
isolation. `compose-structure.md` owns every rule that carries a number, together
with the derivation that produces it.

Resource limits were defined in both. `security-baseline.md` held a profile table
with fixed `memory`, `cpus` and `pids` values and called the block optional;
`compose-structure.md` held a role table with the same limits, their basis, and
called it required. Neither file appeared in the File Map for this fact, so the two
versions had no defined relationship and drifted apart on whether a CPU limit is set
by default.

The split follows what each file can answer. A binary control is met or it is not,
and a checker decides it. A value has a derivation behind it and a failure mode when
it is set too low, which is the treatment the deriving text already carries.

This applies beyond the resource block: a rule that carries a number belongs in
`compose-structure.md`.

## 2026-08 · Memory and pids bound the host, CPU does not

An unbounded memory leak runs until the kernel OOM-killer fires, and the process it
selects is not necessarily the one that allocated. A fork bomb exhausts the global
pid space, after which the host starts no further process, including a login shell.
`memory` and `pids` are set on every service for that reason.

A CPU limit addresses a different failure. Under contention the scheduler distributes
cycles, so a container spinning on the CPU makes other containers slow rather than
unavailable. `cpus` is therefore not part of the baseline.

Two dozen services carry one anyway, with the values of the profile table that was
removed — a derivation, not a measurement. `compose-structure.md` admits that state
explicitly and requires the compose file to declare it beside the value, so a reader
can tell a derived ceiling from a measured one. v0.9.0 resolves it per service.

`security-baseline.md` stated that `deploy.resources` "caps memory and CPU so a
single container cannot exhaust the host under load or during a memory leak". That
holds for memory and not for CPU, and it was the reasoning behind the `cpus` column
in its profile table. Both were removed with the section.

## 2026-08 · The Traefik service port stays a literal

`traefik-labels.md` states that the container-internal port is hardcoded per app,
because it is a property of the image rather than of the deployment. 39 of 51 label
lines used `${APP_INTERNAL_PORT}` instead, including `apps/_reference`, and the
variable was defined in no standard.

The tree was brought to the standard rather than the reverse. `APP_INTERNAL_PORT` is
removed from every compose file, from the four healthchecks that read it, and from
every `.env.example`. Changing the value moves the label away from the port the image
listens on, so it breaks routing instead of relocating it.

## 2026-08 · No review gate on `main`

Branch protection on `main` requires seven status checks and no approving review.
With a single maintainer, a required review is satisfied by the author approving
their own pull request, which records an approval that nobody performed. The status
checks are the part of the gate that reports a result.

`CHANGELOG.md` recorded five checks and one approving review. That was not the live
configuration.

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
baseline-aligned criteria are the single gate between them. Full definition in
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
