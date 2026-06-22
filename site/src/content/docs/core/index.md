---
title: Core Infrastructure
description: Guides for the foundational services every application in Secure Docker Blueprint depends on — reverse proxy, TLS, and intrusion prevention.
---

You set these up once per server, before adding any application.

### Traefik

Reverse proxy and TLS for every service. Set this up first — nothing else is reachable without it.

[Go to the Traefik guide →](/core/traefik/)

### CrowdSec

Intrusion detection and blocking, layered on top of Traefik. Optional.

[Go to the CrowdSec guide →](/core/crowdsec/)

## Where to go next

- New server: start with [Traefik](/core/traefik/).
- Traefik already running: add [CrowdSec](/core/crowdsec/), or go straight to [Applications](/applications/).
