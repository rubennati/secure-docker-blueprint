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
                              ▼
                    ┌───────────────────┐
                    │      Traefik      │  TLS, routing, access rules
                    └─────────┬─────────┘
                              │  proxy-public   (shared network)
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          app A web       app B web       app C web
              │               │               │
        app-a-internal   app-b-internal  app-c-internal   (isolated, one per app)
              │               │               │
        database, cache  database, cache  database, cache
```

The applications publish no ports. **From outside the host**, an application is
reached through the proxy and nowhere else, which is why there is exactly one
place where TLS is configured, one place where rate limits live, and one place
to look when something is unreachable.

Inside the shared proxy network it is not a guarantee: containers on one Docker
network address each other directly, so a compromised front end can reach
another front end without the proxy in between. That is the lateral path the
architecture leaves open, and it is treated as part of the threat model below.

**Two networks per application, and they do different jobs.**
`proxy-public` is shared: the proxy and each application's web-facing container
sit on it, and that is all. Each application also gets its own internal network
that has no route to the internet and no route to any other application. The
database and cache live only there.

An application that gets compromised cannot reach another application's
database, because there is no network path to it. Not a rule someone has to
remember — an absent route.

## Who is allowed to reach what

Each service picks an access policy, and the proxy enforces it before the request
reaches the container. In practice this is one variable in that service's `.env`:

| Policy | Reachable by |
|---|---|
| `acc-public` | anyone on the internet |
| `acc-local` | the local network |
| `acc-tailscale` | clients on your VPN only |
| `acc-private` | a defined address range |
| `acc-deny` | nothing — the route exists but answers no one |

**The defaults differ per service, and are not all restrictive.** Of the five
services with a guide here, Vaultwarden and Invoice Ninja ship
`acc-tailscale`, Nextcloud ships `acc-private`, and Seafile Pro and OnlyOffice
ship `acc-public` — the last two because they are built around sharing with
people who are not on your VPN. Check the value in that service's `.env.example`
rather than assuming; it is one line, and it decides who can reach the thing.

:::caution
An access policy is a proxy setting, not a firewall. `acc-public` removes the
proxy's own address check; it does not open a port that something upstream is
blocking, and `acc-tailscale` does not stop packets that never reach Traefik.
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
   decides which addresses to ban. It only sees what the access policy let
   through, which is why it earns its place on public services and very little
   behind a VPN.
3. **Single sign-on** can be attached per route for applications that need it.
   The repository ships a stack for it; there is no guide here.
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
