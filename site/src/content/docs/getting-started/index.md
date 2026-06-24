---
title: Getting Started
description: The basic operating path for Secure Docker Blueprint — from first server to first running service.
---

Start here if you want to understand the basic operating path before running a service with Secure Docker Blueprint.

## The basic path

1. **Prepare the server** — Docker 24.0+ with Compose v2 on a Linux host (Debian 12/13 is tested). You also need a domain with DNS pointing to the server.

2. **Bring up the foundation** — Traefik handles routing and TLS for every service that follows. Start it first, before adding any applications. See the [Traefik guide](/core/traefik/) for setup, including the IPv4-vs-dual-stack and certificate-strategy decisions.

3. **Check Traefik** — Once Traefik is running, the `proxy-public` Docker network exists and the dashboard should load over HTTPS. Every application connects to Traefik through that network.

4. **Add the first application** — Every application follows the same pattern: copy `.env.example` to `.env`, configure your domain and credentials, then `docker compose up -d`. Add one service at a time.

5. **Verify before relying on it** — Check that the service is healthy (`docker compose ps`) and accessible in a browser. Do not add real data until the service is confirmed working.

6. **Back up before real use** — Configure a backup before putting real data into any service. A backup that has never been tested should not be treated as a recovery plan.

7. **Update deliberately** — Before updating any service, read the release notes for breaking changes. Back up first, then bump the version tag and restart.

## Choose your starting point

### New server

Start with [Traefik](/core/traefik/) and the shared foundation. Get it running and verified before adding the first application. The foundation only needs to be set up once — every application you add later uses it. Add [CrowdSec](/core/crowdsec/) once Traefik is confirmed working — optional, and not a blocker for adding your first application.

### Existing Blueprint server

The foundation is already in place. Verify that Traefik is running and the `proxy-public` network exists, then follow the application guide for the service you want to add.

### Existing app / update

Before updating: read the release notes, back up the database and data directory, then bump the version tag and restart. Verify the service is working before considering the update complete.

## Start with the first guides

[Traefik](/core/traefik/) is the foundation — set it up first regardless of which application you're adding. [CrowdSec](/core/crowdsec/) is the optional next step for intrusion detection. The first available application guide covers Vaultwarden — a password manager that walks through setup, hardening, backup, restore, and updates.

[Go to the Traefik guide →](/core/traefik/) · [Go to the Vaultwarden guide →](/applications/vaultwarden/)
