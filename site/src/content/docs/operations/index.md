---
title: Operations
description: Operational topics for running the Blueprint stack day to day.
---

Work that spans every service on the host, rather than any single one.

:::caution
A service is not responsibly operated until backup and restore expectations are understood. Starting with operations before backup is backwards.
:::

- **[Backup and restore](/operations/backup/)** — Borgmatic on the host: install, configure, take a backup, and restore from it.

## What lives with each service instead

Updating, verifying and diagnosing are specific to the service, so each guide
carries its own: a **Verify** section for confirming it works, **Troubleshooting**
for the failures that service actually produces, and **Updates** for reading the
release notes and moving the version tag.

Certificate renewal needs nothing — Traefik requests and renews automatically once
the [certificate strategy](/core/traefik/) is set. Monitoring and alerting are not
covered on this site yet; the repository has the stacks and the reasoning.
