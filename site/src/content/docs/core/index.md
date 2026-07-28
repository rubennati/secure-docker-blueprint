---
title: Core Infrastructure
description: Guides for the foundational services every application in Secure Docker Blueprint depends on — reverse proxy, TLS, and intrusion prevention.
---

Traefik and CrowdSec are set up once per server before any application — together they cover how multiple services share one server securely and how you detect attacks. OnlyOffice is an additional optional shared service, needed only when applications require in-browser Office document editing.

## Traefik

**Problem it solves:** multiple Docker services need HTTPS on the same server and the same port, without manually juggling certificates per service — and some should be reachable from the internet while others stay Tailscale-only.

Every other guide on this site assumes Traefik is already running. Nothing is reachable without it.

[Go to the Traefik guide →](/core/traefik/)

## CrowdSec

**Problem it solves:** without it, brute-force attempts, scraping, and exploit probes just happen in your logs, unnoticed, until something breaks. CrowdSec watches automatically and can block automatically.

Optional, but the layer most setups end up wanting once Traefik is stable.

[Go to the CrowdSec guide →](/core/crowdsec/)

## OnlyOffice

**Problem it solves:** applications such as Seafile Pro need a running OnlyOffice server to open `.docx`, `.xlsx`, and `.pptx` files in the browser — without one, Office files open read-only or not at all.

Optional shared service. One instance serves multiple consuming applications simultaneously.

[Go to the OnlyOffice guide →](/core/onlyoffice/)

## Where to go next

- New server: [Traefik](/core/traefik/) first — everything else depends on it.
- Traefik already running: add [CrowdSec](/core/crowdsec/) for intrusion detection, or skip straight to [Applications](/applications/).
- Setting up Seafile Pro or another Office-editing app: [OnlyOffice](/core/onlyoffice/) provides the shared document editing backend.
