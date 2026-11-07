---
title: How a server fits together
description: The shape of a running Blueprint host — one proxy at the front, two networks per application, credentials as files, and access decided in one place.
---

Every guide on this site produces a piece of the same picture. This page is the
picture, so that a command you are asked to run has somewhere to sit.

None of it is required reading before installing something. It is worth reading
before *changing* something.

## One way in

```text
                     internet / VPN
                           │
   host firewall (optional, installed by the operator)
                           │  ports 80/443, published on proxy-public
                           ▼
   ┌───────────────────────────────────┐
   │ Traefik   TLS · access policy     │
   │           rate limit · headers    │   crowdsec-security
   │           CrowdSec bouncer ───────┼──► CrowdSec engine
   │           forward-auth (opt.) ────┼──► Authentik     LAPI · AppSec
   └─────────────────┬─────────────────┘   (optional)      (engine: Coraza)
                     │  one edge network per stack
                     │  (default; proxy-public is the shared choice)
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   app A web     app B web     app C web
       │             │             │
   A-internal    B-internal    C-internal      isolated, one per app
       │             │             │
   db, cache     db, cache     db, cache
                     └─ B-egress: outbound only, where a stack needs one
```

Web applications publish no ports. **From outside the host**, a web application is
reached through the proxy and nowhere else, which is why there is exactly one
place where TLS is configured, one place where rate limits live, and one place
to look when something is unreachable. The exceptions are the stacks whose
protocol is not HTTP — UniFi, OpenCanary and the access gateways under `core/`
(Teleport, Warpgate, ShellHub and others): each publishes its ports on a
host address the operator must set, and their examples ship `0.0.0.0`.

Containers on one Docker network address each other directly. On its own edge
network a front end reaches the proxy and nothing else; a stack placed on the
shared `proxy-public` network can reach the other front ends there without the
proxy in between. That is the lateral path the shared choice leaves open, and it
is treated as part of the threat model below.

**Two networks per application, and they do different jobs.**
By default each stack has its own edge network, which the proxy joins (`EDGE_NETWORKS`
in `core/traefik/.env` — a stack whose network is not listed there is unreachable).
Only the proxy and the stack's web-facing container sit on it. `proxy-public` is
the shared choice for stacks that reach each other by name. Each application also gets its own internal network
that has no route to the internet and no route to any other application. The
database and cache live only there. Where a backend service must reach the
outside — a worker that sends mail, for example — it joins a second, outbound
network of its own stack as well, and that stack's guide says why.

An application that gets compromised cannot reach another application's
database, because there is no network path to it. Not a rule someone has to
remember — an absent route.

The optional [host firewall](/security/host/) is rendered with the proxy
configuration and installed separately. Host tests on 2026-11-03/04 covered its
rules, VPN access over both address families and a reboot. Those results describe
that deployment; a new server still needs its own exposure and access checks.

## Who is allowed to reach what

Each service picks an access policy, and the proxy enforces it before the request
reaches the container. In practice this is one variable in that service's `.env`:

| Policy | Reachable by |
|---|---|
| `access-public` | anyone on the internet |
| `access-trusted` | the ranges you declare in `core/traefik/.env` (`TRUSTED_RANGES`) — your LAN, written out |
| `access-vpn` | clients on your VPN only |
| `access-trusted-vpn` | the declared ranges and your VPN |
| `access-blocked` | nothing — the route exists but answers no one |

**Check each service's default before starting it.** Vaultwarden, Paperless-ngx,
Invoice Ninja and Ghost ship `access-vpn`. Nextcloud, Seafile and Seafile Pro ship
`access-trusted-vpn`, which admits the VPN and the additional client ranges you
configure; it does not automatically admit Docker networks. WordPress, BookStack
and Immich ship `access-public`. Read `APP_TRAEFIK_ACCESS` in the service's
`.env.example`, then set the policy in your `.env` for the audience you intend.

:::caution
An access policy is a proxy setting, not a firewall. `access-public` removes the
proxy's own address check; it does not open a port that something upstream is
blocking, and `access-vpn` does not stop packets that never reach Traefik.
Network reachability and access policy are separate questions, and a service can
fail either one independently.
:::

## Credentials are files, not environment variables

Where the image allows it, a password is written into a file that is mounted into
the container, and the application is pointed at the file path rather than given
the value. It keeps the secret out of `docker inspect`, out of the process
environment, and out of shell history.

Not every image supports it. Some can only read a credential from the
environment; those stacks keep the value in a `.env` file that is never committed,
and the stack's own documentation names the deviation and why it stands. The
difference is visible in each guide's installation steps — `.secrets/` for one,
`.env` for the other.

**Configuration is in version control. Secrets and data are not.** The Compose
file and `.env.example` are what you clone; the `.env`, the `.secrets/` directory
and the `volumes/` directory are created on the host and stay there. That split
is also why a restore has to cover more than the database.

## Layers, and what each one actually catches

Four things sit between a request and the application, and they are independent —
each works whether or not the others are there.

1. **The proxy** terminates TLS and applies security headers, rate limits and the
   access policy above. Always present; everything else is optional.
2. **[CrowdSec](/infrastructure/crowdsec/)** reads the proxy's access log and
   decides which addresses to ban; a plugin inside the proxy enforces the bans
   once switched on. It only sees what the access policy let through, which is
   why it earns its place on public services and very little behind a VPN. Its
   optional AppSec component inspects requests with Coraza as the rule engine —
   part of CrowdSec, not a separate service — and ships with virtual-patching
   rules, not the OWASP Core Rule Set.
3. **Single sign-on** — [Authentik](/infrastructure/authentik/) — can be attached
   per route as a forward-auth middleware in the proxy. Optional, and off until
   switched on; when Authentik does not answer, the route fails closed.
4. **The container itself** runs without the ability to gain new privileges, with
   Linux capabilities dropped, and with a read-only root filesystem where the
   image tolerates one.

The last one is the layer that still applies when the first three have been got
wrong.

## What this shape costs you

Being honest about the trade is part of the design:

- **The proxy is a single point of failure.** Nothing is reachable while it is
  down, and restoring it is the first step in any recovery, not a later one.
- **One host means one blast radius.** The networks separate the applications
  from each other; they do not separate them from the machine.
- **Every service is one more thing to update.** The version pinning that makes
  deployments reproducible also means nothing updates itself.

## Where to go from here

- [What every server needs](/infrastructure/) — the two server-wide pieces
- [Preparing a server](/getting-started/server-setup/) — the host decisions that
  are expensive to reverse, IPv6 in particular
- [Backup and restore](/operations/backup/) — what the split between config,
  secrets and data means when you have to recover
- [What self-hosting does not answer](/sovereignty/) — the questions this
  architecture deliberately does not settle
