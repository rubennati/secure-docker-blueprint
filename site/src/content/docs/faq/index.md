---
title: FAQ
description: Common questions about secrets, networking, upgrades, and configuration.
---

Answers to common questions about the Secure Docker Blueprint stack.

## Why Docker Secrets and not plain environment variables?

Environment variables are visible to any process in the container and are commonly captured in logs, debug output, and crash reports. Docker Secrets write credentials to a file (`/run/secrets/<name>`) accessible only to the target container, avoiding that exposure. The blueprint uses the `_FILE` pattern where upstream supports it and documents deviations where it does not.

## Can I use only some of the apps?

Yes. Every application is independent. You need the core stack (Traefik at minimum) for routing and TLS, but each app beyond that is opt-in.

## Can I run this without CrowdSec?

Yes. CrowdSec is part of the core stack but removing the bouncer labels from Traefik and skipping `core/crowdsec/` is a valid configuration for development or trusted networks.

:::note
This page is a placeholder. Additional FAQ entries are planned for the v0.9.0 Operator Site launch.
:::
