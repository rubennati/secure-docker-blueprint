# Decisions

Architecture and governance decisions with their reasoning, newest first. The full
rationale for structural decisions lives in [`../docs/architecture.md`](../docs/architecture.md);
this file is the index and covers decisions that have no other home.

---

## 2026-08 · Host CrowdSec enforcement is scoped to the public interface

The firewall bouncer runs in nftables `set-only` mode and maintains only the IPv4 and
IPv6 blacklist sets. This repository owns the DROP rule, attached to `hook forward` with
an explicit ingress-interface match on the public interface. There is no generic INPUT
chain, and no rule can match the management interface.

The alternative — the package's default managed mode — installs a source-address chain at
`hook input` with no interface restriction. That shape removed administrative access when
a legitimate detection banned an administrator's own VPN address, and it filtered no
proxy traffic at all, because published container ports are DNAT'd and traverse `FORWARD`
rather than `INPUT`. It carried the failure mode without the benefit.

Rejected: relying on an allowlist for the management plane. An allowlist is data and can
be wrong — the previous design trusted `safe_range`, which is not a configuration key in
the installed package and was silently ignored while validation reported success. A LAPI
AllowList for the VPN ranges is kept as defence in depth; the interface match is the
guarantee, because it is topology rather than data.

Rejected: `nft flush ruleset` or whole-snapshot restore as a rollback. Docker and the VPN
daemon rewrite host netfilter state continuously, so recovery names only CrowdSec's own
units and tables.

Deferred: the scoped enforcement is designed, not runtime-accepted. The acceptance
sequence and what is verified today live in `core/crowdsec/docs/firewall-bouncer.md`; the
incident evidence is in `docs/bugfixes/crowdsec-firewall-bouncer-2026-08-28.md`.

## 2026-08 · CrowdSec gets a dedicated core-to-core network

The engine joins `crowdsec-security` and no longer joins `proxy-public`. The network
is an ordinary IPv4 bridge, declared by `core/traefik` and joined by `core/crowdsec`
with `external: true`. Traefik and the engine are the intended members; application
stacks stay on `proxy-public` and never attach.

`proxy-public` is the network every routed application joins, and the CrowdSec LAPI,
AppSec and Prometheus ports answered all of them. Authentication already bounded what
that reach was good for — a bouncer key reads decisions and can neither create nor
delete one, and AppSec returns 401 without a valid remediation key — so this is
control-plane segmentation rather than the closing of an exploit. It also returns the
deployment to the upstream expectation that the AppSec component answers the reverse
proxy and nothing else.

Rejected: leaving the engine on `proxy-public`, which keeps the unauthenticated
metrics and pprof endpoints on port 6060 reachable from every application container.
Rejected: `internal: true` plus a separate egress network — it denies a route neither
member uses, and closed membership already bounds reachability.

Deferred: extending the shared-external-network identity check to this network. It
carries two members named in this repository, so the ambiguity that rule prevents
cannot arise. Revisit if an independent participant is ever added. Deferred also: what
becomes of the Prometheus endpoint on 6060, since the v0.8.0 monitoring milestone
wants to scrape it and that decision belongs there.

AppSec keeps `listen_addr: 0.0.0.0:7422` and the LAPI keeps its `127.0.0.1` host
publication for the host-firewall remediation bouncer. Neither is an oversight: the bind cannot
be loopback across containers, and the host publication is a mechanism no container
reaches.

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

## 2026-09 · Capabilities, with one reference implementation each

The blueprint is a set of capabilities — Foundation, Reverse Proxy, Identity & Access,
Threat Detection & Remediation, Web Application Security, Network Security — and each has
at most one product that this repository actually configures and tests. The capability
answers whether a deployment needs the function; the product is replaceable. Both
questions were previously answered by naming a product.

`docs/architecture.md` owns the model: the capability table, the Foundation boundary, the
exposure classification, the state-ownership rule and the application contract. Stack
READMEs stay product documentation. The directory split by access pattern is unchanged —
the capability model is a layer above it, not a replacement for it.

Three states are kept apart: **implemented** (configured and exercised here),
**documented alternative** (described so a fork can choose it, not maintained here) and
**evaluation candidate** (no claim of support). Current: Traefik, Authentik and CrowdSec
implemented; CrowdSec AppSec the current Web Application Security reference with Coraza +
OWASP CRS a documented alternative — mature engine, but the Traefik open-source
integration is not mature enough to adopt; Suricata an evaluation candidate for passive
network IDS, not implemented and not baseline. SIEM, XDR and SOC platforms are out of
scope: different operating model, and a secure Docker host does not need one.

**An application does not intrinsically require Traefik.** It requires the reverse-proxy
capability when served over a network, and most stacks ship a local compose file that uses
no proxy at all. The concrete integration vocabulary stays Traefik-specific
(`APP_TRAEFIK_*`, `acc-tailscale`) because the implementation genuinely is — renaming
waits for a second implementation that creates the need.

## 2026-09 · CrowdSec has a Core and two independent remediation points

"Phase 1 / 2 / 3" is retired from current documentation. It implied an order that the
repository's own text contradicted: the two enforcement components are peers, and neither
depends on the other.

    Core  →  Reverse-Proxy Remediation
          →  Host-Firewall Remediation

Core detects, decides and serves decisions over the LAPI. **Core alone blocks nothing** —
that sentence belongs early in every CrowdSec entry document, because a detector with no
remediation attached is a detector.

Which remediation applies follows from exposure, not from a sequence: a public HTTP
application behind the proxy is covered by reverse-proxy remediation without any host
firewall work; a service terminating on the host and reachable publicly is the case
host-firewall remediation exists for. Both may run together, at different enforcement
points, and that remains a choice.

The verified host-firewall work is reclassified, not revised: ingress scoping, structural
management-plane exclusion, the FORWARD path, set-only ownership, the prepare/cleanup
lifecycle, the readiness gate, fail-open, the range limitation and the rollback and reboot
models all stand unchanged under Host-Firewall Remediation. Historical records keep the
old numbering — it is accurate for the architecture of their time.

## 2026-09 · The dashboard follows the certificate strategy, like every router

The Traefik dashboard router carried `tls.certResolver` unconditionally, so a
wildcard deployment issued a second certificate for its dashboard hostname and
published that name in Certificate Transparency — the exact outcome the wildcard
path exists to avoid. No rationale for the exception existed anywhere; the
configuration could not express the consistent alternative, because `validate.sh`
required the variable to be non-empty.

The dashboard now follows the selected strategy: empty resolver under a covering
wildcard, its own resolver otherwise. Coverage is checked as the actual
relationship between `TRAEFIK_DASHBOARD_HOST` and `ACME_WILDCARD_DOMAIN`, not as
"a wildcard is configured somewhere" — the two are independent free-form
variables, and `*.example.com` matches exactly one label. An explicit resolver
under a covering wildcard stays supported and warns, because refusing it would
fail validation on every existing installation over a privacy preference rather
than a fault.

Migration is forward-looking only. Traefik loads every certificate in `acme.json`
at startup regardless of router references and renews it on expiry alone, and it
documents no way to retire a single stored certificate. An existing dashboard
certificate therefore keeps being served and renewed, and a published hostname
stays in the append-only logs.

**How this was found matters for how the next report is read.** External field
feedback reported an HTTP-01 deployment silently receiving Traefik's default
certificate and proposed enabling `certresolver` across the Compose files. That
proposal was declined: the operator had chosen a documented alternative path and
skipped its documented requirement, and the commented label is what makes the
wildcard path work. Investigating the claim is what surfaced the real defect,
one the report never mentioned — in the dashboard, not the applications.
Evidence to investigate, not a specification to implement.

## 2026-08 · Host-firewall remediation stays scoped, and ships without range enforcement

Host CrowdSec enforcement keeps its shape: `hook forward`, priority `filter - 10`,
an explicit ingress-interface match on the public interface, no generic INPUT
chain. The interface match is the management-plane guarantee; the LAPI AllowList
for the VPN ranges is defence in depth behind it.

The blueprint owns both nftables tables, **both** blacklist sets and the scoped
chains. The bouncer owns set membership and nothing else. Both sets are created
deliberately even though this bouncer version can auto-create the IPv4 one, so no
per-family special case survives into operation and "state is ready" stays a
single predicate.

The set schema is `flags timeout` for both families. **`flags interval` must not
be used.** nftables supports it and represents CIDR correctly, but the installed
bouncer cannot populate an interval set — the commits fail and the sets stay
empty, which is worse than the problem it would solve.

The consequence is accepted rather than worked around: host-firewall remediation enforces
**individual source-IP decisions**, IPv4 and IPv6. Range decisions degrade to
their network address at this layer. That is a coverage limit and not a lockout
risk — it blocks less than intended, never more, and cannot reach the management
plane. Proceeding on individual-IP enforcement does not wait for range support,
and no unverified future package is planned around.

## 2026-08 · Artefacts stand alone; the test environment is evidence, not specification

Every file is written for whoever opens it, and states the final result and the
facts needed to use, operate or verify it. The route taken — experiments, the
test host, rejected alternatives, how it differs from another file — is working
context and stays out. A `docker-compose.local.yml` says how to run it, and
nothing else.

The environment this repository is developed and tested on is evidence about the
software, never part of its specification. No requirement, dependency, default,
deployment assumption or documentation obligation follows from it alone. The
test host runs every stack behind one proxy; a reader takes one stack. The
working unit for repository-facing docs: an instruction has to be true for
someone running exactly one stack.

## 2026-08 · A local test stack per stack, where one means anything

`docker-compose.local.yml` beside the production file, publishing on
`127.0.0.1` with plain credentials, so an application can be tried without a
proxy, DNS or certificate. Shape and header in
`docs/standards/compose-structure.md`; the Local column in `LIFECYCLE.md` is
generated, so the coverage figure cannot drift.

Stacks that show nothing run alone have none — a reverse proxy, an agent
reporting to a central instance, something needing host networking, a client for
another stack's data. A reasoned absence is the outcome, not a gap.

## 2026-04 · Hub-and-spoke networking per app

`proxy-public` shared and external; `app-internal` per app with `internal: true`.
Databases never join the public network and never publish a host port.

## 2026-04 · Config in git, secrets and data never

The compose file and `.env.example` are the portable artifact. `.env`, `.secrets/`
and `volumes/` stay on the host.

## 2026-04 · Security-first with documented exceptions

Hardening is the default; relaxing a control requires a written, per-app exception.
Deviations are never silent.
