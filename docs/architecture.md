# Blueprint Architecture

This document owns the capability model: which security and operational capabilities the
blueprint provides, which product currently implements each one, how they connect, and what
an application may assume about them. It also explains why the directories are split the way
they are and how services connect at the network level.

It is the "why" behind the "what". Product configuration belongs to each stack's own
`README.md` — this document names a reference implementation without describing how to set
it up.

---

## Design Goals

- **Fork-ready**: Clone, copy `.env.example` to `.env`, fill secrets, `docker compose up -d`. No undocumented prerequisites.
- **Portable**: No host-specific assumptions beyond "Debian + Docker". Runs on a VM, a VPS, or bare metal.
- **Security-first**: Hardening is the default. Relaxing a control requires a documented exception.
- **Standards-consistent**: Every service follows the same compose structure, env layout, secrets pattern, and naming convention. A new app that follows the standards fits in without friction.

---

## Directory Structure

Five top-level categories, split by **how** each tool accesses the system — not by who uses it:

| Directory | Responsibility | Access pattern |
|---|---|---|
| `core/` | Shared platform and control plane — capabilities scoped to the installation, not to one stack | Privileged or cross-stack — controls Docker, the host or other containers, or serves a capability other stacks route through, authenticate against, resolve names with, or store secrets in |
| `apps/` | User-facing applications | Standard — Traefik-routed, DB + volume access |
| `business/` | Business operations tools | Standard — same pattern as `apps/`, distinct operational scope |
| `monitoring/` | Observability and alerting | Cross-stack — reads metrics and logs from other containers |
| `backup/` | Data protection | Privileged — reads volumes across services, writes to remote targets |

`monitoring/` and `backup/` are top-level (not under `apps/`) because their access patterns are fundamentally different: they reach across service boundaries and need broader permissions than a typical user-facing app.

**Which category does a new service belong to?** One test question each, applied in order:

| Directory | Test |
|---|---|
| `core/` | Does it control Docker, the host or other containers, or does it provide a shared network, TLS, identity, DNS, security or secrets capability for the installation rather than for its own users? Scope decides, not dependency: a member may be optional, and two members may be alternatives to each other. |
| `monitoring/` | Does it observe one or more other services? |
| `backup/` | Does it protect data belonging to other services? |
| `business/` | Is a company needed for this to be useful at all? (issuing invoices, customer helpdesk, compliance) |
| `apps/` | Everything else — would a homelab user *and* a company both use it? A stack that serves its own users belongs here, including a diagnostic fixture deployed to prove another stack works: that is a lifecycle property, and no category test asks about lifecycle. |

The rule was sharpened after an earlier attempt placed `business/` by analogy to `monitoring/` and left ten existing apps stranded. Categorising by **access pattern** rather than by audience is what makes it hold.

---

## Physical layout, conceptual domains and navigation are three different layers

Three separate questions get asked about this repository, and conflating them is
what stranded `business/` once already (above). Each has its own owner and its
own reason to change.

| Layer | Question it answers | Owner | Changes when |
|---|---|---|---|
| **Physical layout** | how does a stack access the system? | this document, the five directories | a stack's access pattern differs from every existing category |
| **Conceptual domain** | how does a reader group this in their head? | documentation, `.ai/decisions.md` | a subject-matter grouping helps a reader, independent of any directory |
| **Website navigation** | how does a reader find this? | `site/` | reader research shows a different grouping helps — already independent today, see the site's Infrastructure/Applications/Operations split |

The physical layout is `core/apps/business/monitoring/backup`, unchanged, and is
the only one of the three that CI knows about at all: `check-structure.py` and
`check-coverage.py` enforce that every stack sits under one of the five roots and
that no root goes unchecked. Which of the five a given stack belongs in is a
judgement against the table above, not something CI can decide. A conceptual
domain can exist purely as documentation
and navigation vocabulary, with no stack in it, for as long as that stays
useful to a reader — it earns a directory the same way any category does: by
failing every test in the [Directory Structure](#directory-structure) table.

**Conceptual domains today**, alongside the five that already map to a
directory (Infrastructure → `core/`, Applications → `apps/`, Business →
`business/`, Monitoring → `monitoring/`, Operations & Recovery → `backup/`):

- **Development / Custom Applications** — has a physical home, `development/`,
  for the patterns it owns. See below.
- **AI & Local AI** — no stack, deliberately. See below.
- **Document Processing** — real capabilities, no reusable pipeline. See below.

AI & Local AI and Document Processing do not justify a new top-level directory.
Development has one, for a different reason than the access-pattern test the
five categories use — see below.

### AI & Local AI is latent on purpose

No stack exists here, and that is a decision rather than an omission.

The line runs between running a service and doing the engineering. If a real
need appears for a reusable AI service — a model runtime, a gateway, a vector
store — then deploying and hardening it is this repository's problem, and it
goes through the same categorisation test as anything else: nothing about "AI"
changes which directory it lands in, and an observability component for it would
most likely be `monitoring/`. The engineering above that line — model
evaluation, retrieval architecture, prompt design, the experiments that decide
whether any of it is worth running — belongs to a different project and is not
served by putting a Compose file here.

So the absence is not waiting on a decision. It is waiting on a deployment that
somebody actually needs, and a catalogue of candidate products assembled in
advance would be a list, not a capability. Machine learning already runs inside
existing stacks — Immich's ML worker, PhotoPrism's classification models — and
those are properties of those applications, not a domain.

### Document Processing has the capabilities, not a pipeline

The domain is real and mostly already covered, in three parts rather than the two
it was previously described as:

| Part | Where it lives |
|---|---|
| Archive and ingest — OCR, indexing, search | `apps/paperless-ngx` |
| Browser-based editing | `apps/onlyoffice`, `apps/euro-office`, `apps/collabora` |
| Electronic signature | `business/documenso`, `business/opensign` |

Apache Tika and Gotenberg belong to Paperless-ngx as its own converters, not as
shared services other stacks call — which is why they have no stack of their own
and no entry in the tables.

What does **not** exist is a general document-processing pipeline: a reusable
path from an arbitrary input document through extraction, layout or table
recognition, and into a structured result. That absence is deliberate. A pipeline
is defined by the document it has to handle and the output someone needs, and
building one before a real case exists would produce a chain of tools with no
test for whether it works. Until a document use case demands something
reproducible, the domain stays a way of grouping what is already here, and the
three parts stay separate stacks rather than being merged into one.

### Development is a Supporting-tier domain, not a sixth category

The mission covers two kinds of software: existing self-hosted open-source
projects, and applications someone builds themselves. Both go through the same
**deploy → secure → operate → recover** model, but the first phase differs — an
existing project starts from a published, versioned image; software someone
builds starts from source and a build step, which
[`standards/custom-application.md`](standards/custom-application.md) owns.

**This is not what `docker-compose.local.yml` is for.** The local test stack
([`standards/compose-structure.md`](standards/compose-structure.md)) is a
deployment mode of an already-packaged application — the same `image:` tag,
published without Traefik, DNS or a certificate so it can be tried on one
machine. It answers "how do I try this app," not "how do I harden an app I
wrote."

[`development/`](../development/) is where the build phase lives as a reusable
artifact. `development/static-site/` and `development/web-api/` are complete,
working deployment shapes — a real build, a real hardened runtime, a
local-validation compose file, each proven by a minimal fixture — that a real
project copies into `apps/` or `business/` under its own name once it exists.
They are never deployed from inside this repository, and they are not stacks
in the access-pattern sense the five categories use: the [Directory
Structure](#directory-structure) test asks how a running service reaches the
system, and a pattern that is never run here has no access pattern to test.
That is also why `development/` does not become a sixth category — it sits
alongside `docs/`, `scripts/ci/` and `site/` as a Supporting-tier directory,
checked by [`scripts/ci/check-structure.py`](../scripts/ci/check-structure.py)
anyway, because unlike those three it holds real, buildable compose files
worth the same structural and security check any stack gets.

Two stacks here already build their own image, in two different shapes:
`business/vikunja` adds a layer to a published image because upstream ships
`FROM scratch`, and `apps/caldiy` consumes a governed fork's reviewed release.
[`standards/custom-application.md`](standards/custom-application.md) is derived
from those two — it covers source, build, image identity and what verifies the
image, and states that every phase after the image is unchanged. `development/`'s
patterns are a third shape built on the same standard: a reusable starting
point with no concrete application behind it yet, adopted by copying rather
than by reference.

`apps/_reference` still templates the hardening pattern around a pre-built,
versioned image — its `UPSTREAM.md`, its `_FILE`-secret assumptions and the
Trivy scan target all presume one. `development/`'s patterns hand off to it:
once a project copied out of `development/` has its own identity, everything
after the image — configuration, networking, backup documentation — follows
`apps/_reference`'s structure exactly like any other stack.

A genuinely first-party application — source with no upstream at all — no
longer starts with no shape at all. `business/vikunja` and `apps/caldiy` both
still wrap third-party software; `development/`'s patterns are what a
first-party application starts from now, established because the need for a
reusable starting point — not for one specific named application — was real
and current. This replaces the earlier position that the shape "stays absent
until a real application needs it" (`decisions.md`).

---

## Networking Model

Every multi-service app uses a **hub-and-spoke** network layout. Two Docker networks per app, with a strict separation of concerns:

```text
Internet
    │
    ▼
 Traefik ──── proxy-public (shared, external: true) ────► App server (web-facing)
    │                                                           │
    │                                                    app-internal (isolated, internal: true)
    │                                                           │
    │                                       DB · Redis · Workers · internal services
    │
    └─────── crowdsec-security (core-to-core, external: true) ──► CrowdSec engine
```

**`proxy-public`** — shared across all apps. Only Traefik and each app's web-facing service join this network. Traefik routes inbound requests to the right container. IPv4-only by default; dual-stack IPv4+IPv6 is opt-in and recommended for new deployments — Tailscale ingress needs it to preserve real client IPs over IPv6, where Cloudflare ingress does not (it recovers the real IP from a trusted forwarded header instead). See [`core/traefik/docs/ipv6-dual-stack.md`](../core/traefik/docs/ipv6-dual-stack.md).

**`app-internal`** — one per app, `internal: true`. DB, Redis, workers. Completely isolated: no route to the internet, no route between apps. A compromised app cannot reach another app's database. Always IPv4-only — nothing outside the Docker host connects to these services directly.

**`crowdsec-security`** — a dedicated core-to-core network carrying one conversation: Traefik's bouncer plugin to the CrowdSec LAPI and AppSec engine. `core/traefik` declares it, `core/crowdsec` joins it as an external network, and no application stack joins it. The engine is on no other network, so its control-plane ports answer the reverse proxy and nothing else on the host's Docker networks. An ordinary IPv4 bridge rather than `internal: true` — the engine needs outbound access for hub updates, the Central API and blocklists. The network type and the rule for adding another are owned by [`docs/standards/networking.md`](standards/networking.md).

Traefik is the only service on both planes. Databases and caches **never** join `proxy-public`. They have no exposure beyond their own app stack.

---

## Capabilities and reference implementations

The blueprint is a set of **capabilities**. Each one answers a security or operational
question on its own, and each has at most one maintained **reference implementation** —
the product this repository actually configures, tests and documents.

The distinction matters because it separates two questions that are easy to conflate:
*does my deployment need this capability?* and *which product provides it?* The first is
architectural, the second is replaceable.

| Capability | Question it answers | Reference implementation | Status |
|---|---|---|---|
| **Foundation** | how does this host run containers safely at all? | the standards in `docs/standards/` | prerequisite |
| **Reverse Proxy** | how does a request reach the right service, over TLS, under a policy? | Traefik (`core/traefik/`) | implemented |
| **Identity & Access** | who is allowed to use this service? | Authentik (`core/authentik/`) | implemented, per app |
| **Threat Detection & Remediation** | which sources are known bad, and where is that enforced? | CrowdSec (`core/crowdsec/`) | implemented |
| **Web Application Security** | is *this request* an attack, regardless of who sent it? | CrowdSec AppSec | implemented, opt-in |
| **Network Security / IDS** | what is happening on the wire that no log records? | — | candidate, not implemented |

Capabilities are independent. Integrations connect them, and an integration is named,
documented and owned. CrowdSec is not a Traefik feature; Authentik is not a proxy layer;
a web application firewall is not the same control as blocking a source address.

**One maintained implementation per capability.** Alternatives may be documented without
being implemented — that keeps the maintenance surface bounded. Three states are kept
apart deliberately:

| State | Meaning |
|---|---|
| **implemented** | configured, documented and exercised in this repository |
| **documented alternative** | described so a fork can choose it; not maintained here |
| **evaluation candidate** | under consideration; no claim of support |

SIEM, XDR and SOC platforms are outside this blueprint. They carry a different operating
model — agents, central collection, an analyst rota — and a secure Docker host does not
require one.

---

## Foundation

Foundation is the substrate. It is what a host needs before any of the capabilities above
make sense, and it does not know which of them are installed.

| Part | Owns | Canonical source |
|---|---|---|
| **Host** | the prerequisites a Docker host must meet — a supported and patched system, management access that is not the public attack surface, a host firewall policy, working time and name resolution, and enough capacity held back for management and recovery | thin, see below |
| **Docker** | privileges, capabilities, socket access, image pinning | [`standards/security-baseline.md`](standards/security-baseline.md) |
| **Network** | hub-and-spoke layout, isolation, which service belongs on which network | [`standards/networking.md`](standards/networking.md) |
| **Secrets** | how a credential reaches a container without entering the image or the environment | [`standards/security-baseline.md`](standards/security-baseline.md) |
| **Backup** | what is protected, from what, and how a restore is proven | [`../backup/README.md`](../backup/README.md) |
| **Image provenance** | where a deployable image comes from, and what pins it, when this repository builds it rather than pulling one | [`standards/custom-application.md`](standards/custom-application.md) |
| **Updates** | version pinning and the upgrade path per stack | each stack's `UPSTREAM.md` |
| **Lifecycle** | what has been established about each stack | [`standards/status-model.md`](standards/status-model.md) |

**Host is deliberately thin.** It owns generic invariants — a management path should not be
reachable the same way the public service is; a host firewall policy exists and someone
owns it. It is not configuration management, and not a hardening distribution.

A service may *implement* a Host invariant through an integration. CrowdSec's host-firewall
remediation is one: it enforces decisions in the host firewall, within a scope the Host
policy defines. It does not become the host firewall policy.

### Workload pressure must not consume what recovery needs

**A host under load from its own workloads has to stay administratively reachable.**
Losing an application is an incident; losing the ability to log in, read logs and stop
the offending container turns it into an outage that ends with a power cycle.

Container-level limits bound each workload, and that is where most of the protection
lives — a service reaching its own ceiling fails alone. What they do not do is reserve
anything: nothing in a per-container limit keeps memory available for the trusted
management path, the container runtime, logging, or the tools used to stop a workload.
On a default host, management services and container workloads compete in the same
place.

The invariant is Foundation's:

> Enough host capacity remains available for management and recovery that an operator
> can always reach the machine, see what is happening, and stop the workload causing it.

The mechanism is **not decided**. The candidate is a separate cgroup hierarchy for
container workloads with memory protection on the slice holding management services —
the kernel supports it, and the interfaces are stable. It is not a default here, and
it is not installed anywhere, because it has not been rehearsed: a protection that has
never been tested under real pressure is an assumption.

What a rehearsal has to establish, on a disposable host:

1. container workloads land in the intended hierarchy, and management services do not;
2. controlled memory pressure inside a container reaches that container's boundary;
3. the trusted management path stays usable throughout;
4. the container runtime stays administratively usable;
5. logs remain readable;
6. the offending workload can be stopped;
7. what happens when the reserve mechanism itself is absent or misconfigured.

Until that has run, the invariant is documented and the enforcement is per-container.
Products are examples: a VPN, an SSH daemon and a container runtime are roles, and a
deployment may fill them differently.

---

## Exposure decides which controls apply

A control is not chosen by working through a list in order. It follows from what a
deployment actually exposes.

| Classification | Meaning |
|---|---|
| **Prerequisite** | without it the system does not run safely — Foundation, and a reverse proxy for anything reachable over a network |
| **Exposure-driven control** | warranted because a specific exposure exists, and largely pointless without it |
| **Optional enhancement** | real value, not implied by every deployment |
| **Advanced** | higher operational cost, tuning burden or blast radius |

Worked through:

- A service that terminates **on the host** and is reachable from the internet is not
  behind the reverse proxy — the proxy never sees it. Protecting it is a host firewall
  question, and CrowdSec's host-firewall remediation is the relevant control. Whether any
  such service is exposed at all is a Host/Foundation decision first.
- A public **HTTP application behind the reverse proxy** is covered by reverse-proxy
  remediation. That does not require host-firewall remediation.
- **Management access over a private path** does not remove the need for either, but it
  does constrain them: an enforcement rule must not be able to reach the management path.
  That is an invariant, independent of which VPN or interface a deployment uses.

Both CrowdSec remediation points may run together. They enforce at different places and
see different things. Running both is a choice, not a requirement.

---

## Defence in depth, where the layers differ

Layering is worth it when the layers do genuinely different jobs. For each one, four
questions have an answer: what does it observe, what does it decide, where does it
enforce, and what happens when it fails.

| Combination | Why it is not redundant |
|---|---|
| Source reputation **+** one web application firewall | reputation is cheap and catches known-bad senders; the firewall catches an unknown sender's first request |
| Reverse-proxy **+** host-firewall remediation | same decisions, different enforcement points: one sees the request and can explain the refusal, the other acts before a connection exists and covers ports the proxy never handles |
| Reputation/behaviour **+** passive network IDS | logs and packets are different evidence — but only if someone reads the alerts |

Two engines doing the *same* job at the same point is not depth. Two inline web
application firewalls means twice the inspection, two rule sets to tune, and a block from
one hiding the other.

---

## One owner per piece of changing state

**A changing security state has exactly one canonical owner.** Other components may read
it; they do not write it.

| State | Owner |
|---|---|
| Firewall tables, sets and enforcement chains | the blueprint's own firewall integration |
| Membership of a blacklist set | the remediation component that maintains it |
| Threat decisions | the detection engine's API |
| Exemptions that must hold regardless of decision origin | the engine's allowlist mechanism |
| Routing, middleware chains, certificates | the reverse proxy |
| Application configuration, secrets and volumes | the application |

Where two tools would write the same state, one of them is wrong. That is the test to
apply before adding a second product to an existing capability.

---

## The application contract

An application **consumes** capabilities. It does not contain them.

An application may assume:

- a network exists on which a reverse proxy can find it;
- routing metadata it declares is honoured;
- named middleware — access policy, security headers, threat enforcement — can be
  referenced by name;
- secrets arrive as files;
- its logs are readable by security tooling.

An application is expected to provide:

- a way to run it without a reverse proxy at all, for local use;
- a healthcheck;
- the Foundation baseline;
- a documented `.env.example`.

An application must not:

- contain a reverse proxy, a detection engine or an identity provider;
- create a shared proxy or control-plane network;
- define global middleware;
- depend on an infrastructure container's lifecycle unless it genuinely requires it.

The consequence: **an application does not intrinsically require Traefik.** It requires the reverse-proxy capability when it is served over a network, and
Traefik is what this blueprint currently implements. Most stacks also ship a local compose
file that uses no proxy at all.

---

## Core Services and Their Roles

`core/` holds capabilities whose scope is the installation rather than one stack:
control of Docker, the host or other containers, and shared network, TLS, identity,
DNS, security or secrets. A member may be optional, and two members may be
alternatives to each other — optionality does not disqualify a capability, because
scope is what the category is about. It is a scope and privilege category, not the
capability model; which capability each service implements is the table
[above](#capabilities-and-reference-implementations).

Grouped by role, every member accounted for:

| Role | Members | Why it is in `core/` |
|---|---|---|
| Request path | Traefik (with its socket proxy), CrowdSec | Terminates TLS and reaches every routed container; the socket proxy keeps the Docker socket off services that only need container metadata; CrowdSec reads logs across stacks and its decisions are enforced elsewhere |
| Shared identity | Authentik (reference implementation), Keycloak (maintained alternative) | An identity provider several applications authenticate against |
| Shared names and certificates | dnsmasq, acme-certs | Resolves names for the installation; issues certificates for the devices that never pass through Traefik |
| Shared secrets | Infisical | Optional central alternative to per-stack Docker Secrets — it holds other stacks' credentials |
| Docker control plane | Dockhand + Hawser, Portainer + Portainer Agent | Control the Docker daemon, locally or on remote hosts; each pair is a UI plus its agent |

The socket proxy is a service inside `core/traefik`, not a directory of its own.
`acme-certs` is being extracted to its own repository ([`ROADMAP.md`](../ROADMAP.md)) —
a maintenance decision, not a classification one.

---

## Per-App Structure

Every app follows the same directory layout regardless of category:

```text
<category>/<app>/
├── docker-compose.yml   # hardened, standards-aligned
├── .env.example         # all variables documented inline, no real values
├── .gitignore           # volumes/, .secrets/, .env
├── README.md            # setup steps, verify commands, architecture notes
├── UPSTREAM.md          # upstream image, changelog link, license
├── .secrets/            # gitignored — generated locally per install
└── volumes/             # gitignored — persistent application data
```

**Config lives in Git. Secrets and data never do.**

The compose file and `.env.example` are the portable artifact. The `.env`, `.secrets/`, and `volumes/` are per-installation and stay on the host.

---

## Backup Design Principle

Backup is cross-cutting by nature — it reads from every data-producing service. The blueprint's approach:

- Each app gets its **own isolated backup repository** (Borgmatic or Kopia), not a shared monorepo.
- Retention policies are set **per app** — a database may need daily backups with 90-day retention, a static site weekly with 30 days.
- Restore is **surgical** — recovering one app does not touch another app's backup chain.
- A compromised backup target for one app does not expose all apps.

See [`backup/README.md`](../backup/README.md) for tool choices and the picking matrix.
