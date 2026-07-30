---
title: What you are setting up
description: What a Blueprint server consists of, and the order the steps have to happen in — each one exists because the next cannot be done, or undone cheaply, without it.
next:
  link: /getting-started/server-setup/
  label: Preparing a server
---

A finished setup is one Linux host running one reverse proxy, with each service
behind it on its own network, its credentials mounted as files rather than set in
the environment, and a backup you have restored from at least once.

Nothing here publishes a port to the internet except the proxy. That single
decision is what makes the rest of it manageable — one place for certificates,
one place for access rules, one place to look when something is unreachable.

## The path, in the order it has to happen

The order is not a preference. Each step exists because the next one cannot be
done — or cannot be undone cheaply — without it.

1. **[Prepare the host](/getting-started/server-setup/).** Debian with Docker and
   Compose, DNS pointed at the machine, and — if anyone will connect over a VPN —
   IPv6 enabled in Docker *before* the first container runs. Enabling it later
   restarts the daemon and stops everything on the host.

2. **[Set up Traefik](/infrastructure/traefik/).** It terminates TLS and routes
   every service that follows. Applications here publish no ports of their own,
   so until the proxy and its `proxy-public` network exist, there is nothing for
   them to attach to.

3. **Add one application.** Every guide has the same shape: copy `.env.example`
   to `.env`, set the domain and credentials, `docker compose up -d`, then run the
   guide's *Verify* section. One at a time — two unfamiliar stacks failing
   together is much harder to read than one.

4. **[Arrange a backup before real data goes in](/operations/backup/).** Not
   after. The moment a service holds something you would miss is the moment an
   untested restore starts costing something.

5. **[Add CrowdSec](/infrastructure/crowdsec/) if anything is public.** Optional,
   and worth its keep exactly when a service is reachable from the open internet.
   Behind a VPN-only access policy it sees almost nothing, because almost nothing
   gets that far.

## If you are not starting from scratch

**A server that already runs this blueprint.** The foundation is done — confirm
the proxy is up and its network exists, then go to the guide for the service you
are adding:

```bash
docker network inspect proxy-public --format '{{.Name}}'
```

**Updating a service you already run.** Read the upstream release notes for
breaking changes, take a backup, then move the version tag. Each guide has an
*Updates* section with the specifics — the database dumps and the order of
operations differ per service.

**Something is broken.** Start at the layer rather than the application:
[when something is broken](/operations/troubleshooting/).

## Before deciding anything

- [What every server needs](/infrastructure/) — the two server-wide pieces, and
  which of them is genuinely required
- [What each application is for](/applications/) — the problem each one solves
- [Choosing between services](/applications/choosing/) — where several
  services here do the same job
- [How a server fits together](/architecture/) — the proxy, the networks and the
  secrets, and why applications publish no ports of their own
