---
title: Getting Started
description: Deploy the Secure Docker Blueprint core stack and add your first application.
---

This guide covers the steps to get the core stack running and add your first application.

## Prerequisites

- A Linux host with Docker and Docker Compose installed
- A domain name with DNS you control
- Basic familiarity with the command line

## Core stack

The core stack consists of three services that every application depends on:

1. **Traefik** — reverse proxy and TLS termination
2. **CrowdSec** — threat detection and IP blocking
3. **Authentik** — identity provider for forward auth

Full configuration details and compose files are in the repository under `core/`.

## Adding an application

Every application in the blueprint follows the same workflow:

```bash
cd apps/<app-name>
cp .env.example .env          # Edit: domain, security settings
# Create secrets under .secrets/
docker compose up -d
```

See the repository README for a complete Quick Start walkthrough.

:::note
This page is a placeholder. Full getting-started content is planned for the v0.9.0 Operator Site launch.
:::
