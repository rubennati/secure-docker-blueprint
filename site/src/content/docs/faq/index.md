---
title: FAQ
description: Common questions about Secure Docker Blueprint — networking, scope, project status, and this site.
---

## About the Blueprint

### Does this work with Tailscale?

Yes, throughout. Every service guide can be locked to Tailscale-only access, and [Traefik supports dual-stack IPv6](/core/traefik/) specifically so Tailscale's IPv6 addresses are preserved correctly — a real failure mode this Blueprint documents and fixes, not a hypothetical one.

### Do I need a Cloudflare account?

No. Cloudflare DNS-01 is the [Traefik](/core/traefik/) quickstart path because it doesn't require a public port 80, but per-domain certificates via the standard HTTP-01 challenge work with no Cloudflare account at all — see "Going further" on that guide.

### Is this production-ready?

The project is pre-1.0: the core structure and the services marked ready (✅) are stable, but paths, env variables, and defaults can still change before v1.0. See the repository's [ROADMAP.md](https://github.com/rubennati/secure-docker-blueprint/blob/main/ROADMAP.md) for the exact v1.0 criteria and current status.

### Will my data be backed up automatically?

No, not yet, for most services — stated explicitly in each guide rather than assumed. [Vaultwarden's guide](/applications/vaultwarden/) covers what to back up manually and how; a documented, tested restore procedure is still on the roadmap.

### Can I deploy just a few services to a new server, without the whole repository?

Not via automated tooling yet — a `deploy.sh` rsync helper is on the [roadmap](https://github.com/rubennati/secure-docker-blueprint/blob/main/ROADMAP.md). Today: clone the repository, then copy only the `core/` and `apps/` (or `business/`) directories you actually need to the target server.

### What does it cost?

The Blueprint itself is free — [Apache 2.0](https://github.com/rubennati/secure-docker-blueprint/blob/main/LICENSE). You pay for your own server and domain; individual self-hosted services may carry their own license — check each service's `UPSTREAM.md` in the repository.

## About this site

### Is this site the technical source of truth?

No. The repository is. Compose files, configuration, and implementation details live at [github.com/rubennati/secure-docker-blueprint](https://github.com/rubennati/secure-docker-blueprint). This site is a guided layer on top of it.

### Why is this site smaller than the repository?

The repository covers 40+ services. This site is deliberately curated to the services and topics that benefit most from guided, narrative documentation — not everything needs a guide page.

### Why start with Vaultwarden?

It's commonly the first service people self-host, it stores credentials, and it requires a tested backup and restore setup — a good reference target for what an operator guide on this site should look like.

### Can I use the repository directly without this site?

Yes. The repository is self-contained — this site exists for people who prefer structured guides over reading compose files and READMEs directly.
