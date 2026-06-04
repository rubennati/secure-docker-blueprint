---
title: Applications
description: Hardened Docker Compose setups for self-hosted services.
---

The blueprint includes hardened Docker Compose configurations for 40+ self-hosted services.

Every application follows the same structure: pinned image tags, Docker Secrets for credentials, Traefik labels for routing, network isolation for databases and backends, and a `.env.example` covering every configurable value.

## Available applications

Application compose files and configuration live in the `apps/`, `business/`, `monitoring/`, and `backup/` directories of the repository.

The first full operator reference guide on this site covers [Vaultwarden](/applications/vaultwarden/).

:::note
This page is a placeholder. A curated application overview is planned for the v0.9.0 Operator Site launch.
:::
