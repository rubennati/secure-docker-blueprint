# Lifecycle Overview

## Purpose
This document is a compact, current-state lifecycle snapshot for selected stacks.
It is not a policy document and does not replace stack-specific procedures.
For setup, upgrade, backup, restore, and security implementation details, use each stack's `README.md` and `UPSTREAM.md`.

## Status Values

### Public Status
- `preview`: available for evaluation; not yet trust-grade for routine use.
- `ready`: clean-install and core usage verified; key lifecycle docs and baseline security posture are in place.
- `ops-ready`: `ready` plus restore test evidence.

### Internal Status
- `scaffolded`: structure exists.
- `verified`: clean-install and core function verified.
- `baseline-aligned`: verified + security baseline aligned (or explicit documented deviations).
- `ops-proven`: baseline-aligned + restore test evidence.

### Operational Sub-Statuses
- `Security Baseline`: `unknown` | `aligned` | `aligned-with-deviations` | `not-aligned`
- `Backup Docs`: `missing` | `partial` | `documented`
- `Restore Docs`: `missing` | `partial` | `documented`
- `Restore Tested`: `unknown` | `not-tested` | `tested-pass` | `tested-fail`
- `Version Status`: `unknown` | `pinned-current-known` | `pinned-behind-known` | `pinned-check-needed`

## Lifecycle Overview

| Stack | Category | Public Status | Internal Status | Pinned Version | Last Verified | Security Baseline | Backup Docs | Restore Docs | Restore Tested | Version Status | Docs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `apps/paperless-ngx` | `apps` | `ready` | `baseline-aligned` | `APP_TAG=2.20.13` | `2026-05-03` | `aligned-with-deviations` | `documented` | `documented` | `unknown` | `pinned-check-needed` | [README](apps/paperless-ngx/README.md), [UPSTREAM](apps/paperless-ngx/UPSTREAM.md) |
| `apps/seafile` | `apps` | `ready` | `baseline-aligned` | `APP_IMAGE=seafileltd/seafile-mc:13.0.20` | `2026-04-16` | `aligned-with-deviations` | `documented` | `documented` | `unknown` | `pinned-check-needed` | [README](apps/seafile/README.md), [UPSTREAM](apps/seafile/UPSTREAM.md) |
| `core/traefik` | `core` | `ready` | `baseline-aligned` | `TRAEFIK_IMAGE=traefik:v3.6` | `2026-04-16` | `aligned` | `documented` | `partial` | `unknown` | `pinned-check-needed` | [README](core/traefik/README.md), [UPSTREAM](core/traefik/UPSTREAM.md) |

## Source of Truth Notes
- Stack implementation truth: stack `docker-compose.yml` + `.env.example`.
- Lifecycle procedure truth: stack `README.md` and `UPSTREAM.md`.
- Security baseline definition: `docs/standards/security-baseline.md`.
- This file is a summary index and should stay link-first.

## Known Model Gaps / Next Steps
- `Restore Tested` evidence is not yet explicitly tracked in one canonical place for all stacks.
- `Version Status` depends on explicit latest-known tracking cadence; current values are conservative.
- Internal lifecycle values are useful, but evidence mapping should be periodically reviewed against `docs/maintenance.md`.
