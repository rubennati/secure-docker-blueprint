---
title: Core Infrastructure
description: Guides for the foundational services every application in Secure Docker Blueprint depends on — reverse proxy, TLS, and intrusion prevention.
---

Two services, set up once per server, before any application. Together they answer two questions every self-hosted setup runs into: how multiple services share one server securely, and how you find out something is attacking it.

### Traefik

**Problem it solves:** multiple Docker services need HTTPS on the same server and the same port, without manually juggling certificates per service — and some should be reachable from the internet while others stay Tailscale-only.

Every other guide on this site assumes Traefik is already running. Nothing is reachable without it.

[Go to the Traefik guide →](/core/traefik/)

### CrowdSec

**Problem it solves:** without it, brute-force attempts, scraping, and exploit probes just happen in your logs, unnoticed, until something breaks. CrowdSec watches automatically and can block automatically.

Optional, but the layer most setups end up wanting once Traefik is stable.

[Go to the CrowdSec guide →](/core/crowdsec/)

## Where to go next

- New server: [Traefik](/core/traefik/) first — everything else depends on it.
- Traefik already running: add [CrowdSec](/core/crowdsec/) for intrusion detection, or skip straight to [Applications](/applications/).
