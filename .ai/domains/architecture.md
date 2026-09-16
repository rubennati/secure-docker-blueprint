# Domain — Architecture

**Spec:** [`docs/architecture.md`](../../docs/architecture.md) — the owner of every
structural decision. [`decisions.md`](../decisions.md) is the index with reasoning.

## Design goals, in order

1. **Fork-ready** — clone, copy `.env.example`, fill secrets, `docker compose up -d`.
   No undocumented prerequisites.
2. **Portable** — no host-specific assumptions beyond Debian + Docker. Anything
   host-bound is an explicit, documented exception.
3. **Security-first** — hardening is the default; relaxing a control requires a
   written exception.
4. **Standards-consistent** — a new app that follows the standards fits without
   friction.

## Categorisation

Five top-level directories, split by **how** a tool accesses the system, not by who
uses it. `monitoring/` and `backup/` are top-level because they reach across service
boundaries and need broader permissions than a user-facing app.

The test question per category is in
[`docs/architecture.md`](../../docs/architecture.md#directory-structure) — apply them
in order rather than guessing from the name.

## Conceptual domains are not directories

[`docs/architecture.md`](../../docs/architecture.md#physical-layout-conceptual-domains-and-navigation-are-three-different-layers)
is binding here. Development / Custom Applications, AI & Local AI and Document
Processing are documentation and navigation vocabulary today, not categories —
do not create a directory, a template or a stack for one because it has a name.
A domain earns a directory by failing the categorisation test above, the same
as anything else. `docker-compose.local.yml` is a deployment mode of an
existing app, not Development — the two are not the same problem.

## Networking

Hub-and-spoke per app: `proxy-public` shared and external for web-facing services,
`app-internal` with `internal: true` for everything else. Databases and caches never
join the public network and never publish a host port.

## Security layers

Four independent, additive layers: Traefik (TLS, header chains, rate limits, access
policies) → CrowdSec (reputation, L7 WAF) → Authentik (Forward-Auth, optional per
router) → container hardening. Each works without the others.

## Choice-matrix

Where several tools compete, several are included and the operator picks by
preference. Do not consolidate to one option. The narrow exception is deduplicating
backup tools, where a second repository means a second retention policy and a second
restore rehearsal.

## Before changing anything structural

Read `docs/architecture.md` and `decisions.md`. A structural change is a proposal to
the maintainer, with alternatives and trade-offs — not an implementation detail.
