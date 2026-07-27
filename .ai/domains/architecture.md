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
uses it. The test question per category:

| Directory | Test |
|---|---|
| `core/` | Does the stack break without it, or does it control Docker, identity, certificates or DNS? |
| `apps/` | Would a homelab user *and* a company both use it? |
| `business/` | Does it need a company to be useful at all? |
| `monitoring/` | Does it observe other services? |
| `backup/` | Does it protect data from other services? |

`monitoring/` and `backup/` are top-level because they reach across service
boundaries and need broader permissions than a user-facing app.

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
