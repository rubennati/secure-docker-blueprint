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
| `core/` | Infrastructure every other service depends on | Privileged — manages other containers, network, TLS |
| `apps/` | User-facing applications | Standard — Traefik-routed, DB + volume access |
| `business/` | Business operations tools | Standard — same pattern as `apps/`, distinct operational scope |
| `monitoring/` | Observability and alerting | Cross-stack — reads metrics and logs from other containers |
| `backup/` | Data protection | Privileged — reads volumes across services, writes to remote targets |

`monitoring/` and `backup/` are top-level (not under `apps/`) because their access patterns are fundamentally different: they reach across service boundaries and need broader permissions than a typical user-facing app.

**Which category does a new service belong to?** One test question each, applied in order:

| Directory | Test |
|---|---|
| `core/` | Does the stack — or a large part of it — break without this, or does it control Docker itself, or is it shared identity, certificates, DNS or WAF? |
| `monitoring/` | Does it observe one or more other services? |
| `backup/` | Does it protect data belonging to other services? |
| `business/` | Is a company needed for this to be useful at all? (issuing invoices, customer helpdesk, compliance) |
| `apps/` | Everything else — would a homelab user *and* a company both use it? |

The rule was sharpened after an earlier attempt placed `business/` by analogy to `monitoring/` and left ten existing apps stranded. Categorising by **access pattern** rather than by audience is what makes it hold.

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
| **Host** | the prerequisites a Docker host must meet — a supported and patched system, management access that is not the public attack surface, a host firewall policy, working time and name resolution | thin, see below |
| **Docker** | privileges, capabilities, socket access, image pinning | [`standards/security-baseline.md`](standards/security-baseline.md) |
| **Network** | hub-and-spoke layout, isolation, which service belongs on which network | [`standards/networking.md`](standards/networking.md) |
| **Secrets** | how a credential reaches a container without entering the image or the environment | [`standards/security-baseline.md`](standards/security-baseline.md) |
| **Backup** | what is protected, from what, and how a restore is proven | [`../backup/README.md`](../backup/README.md) |
| **Updates** | version pinning and the upgrade path per stack | each stack's `UPSTREAM.md` |
| **Lifecycle** | what has been established about each stack | [`standards/status-model.md`](standards/status-model.md) |

**Host is deliberately thin.** It owns generic invariants — a management path should not be
reachable the same way the public service is; a host firewall policy exists and someone
owns it. It is not configuration management, and not a hardening distribution.

A service may *implement* a Host invariant through an integration. CrowdSec's host-firewall
remediation is one: it enforces decisions in the host firewall, within a scope the Host
policy defines. It does not become the host firewall policy.

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

`core/` is a privilege category, not the capability model — it holds what manages other
containers, the network or TLS. Which capability each service implements is the table
[above](#capabilities-and-reference-implementations).

| Service | Implements | Why it is in `core/` |
|---|---|---|
| Traefik | Reverse Proxy — TLS termination, routing, access and security middleware | Terminates TLS and reaches every routed container |
| Socket Proxy | Foundation/Docker — mediated socket access | Keeps the Docker socket off the services that need container metadata |
| CrowdSec | Threat Detection & Remediation, and currently Web Application Security | Reads logs across stacks; its decisions are enforced elsewhere |
| Authentik | Identity & Access | An identity provider several applications can share |
| OnlyOffice | a shared application backend, not a capability | Embedded by Nextcloud and Seafile over WOPI |

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
