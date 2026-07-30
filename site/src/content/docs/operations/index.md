---
title: What running this involves
description: The work that outlives the installation — backups and the restore that proves them, diagnosing a break, updates, certificates, and what has no guide yet.
---

Installation is the short part. What follows is the recurring work, and it splits
by whether it belongs to the host or to one particular service.

## Host-wide, and covered here

**[Backup and restore](/operations/backup/)** — Borgmatic installed on the host:
the repository, the keys, dumping databases out of running containers, the timer,
and the restore. A backup nobody has restored from is a hypothesis, not a
recovery plan, so the restore is the part that matters.

**[When something is broken](/operations/troubleshooting/)** — which layer to
suspect and in what order. Most of the time spent on a broken service goes into
looking at the wrong layer, not into the fix.

## Per service, and on that service's page

Updating, verifying and diagnosing depend on what the service is, so each guide
carries its own:

- **Verify** — the checks that confirm the installation actually worked
- **Updates** — reading the release notes, dumping the database, moving the
  version tag, in the order that service needs
- **Troubleshooting** — the failures that service really produces

## Needs nothing from you

**Certificate renewal.** Traefik requests and renews automatically once the
[certificate strategy](/infrastructure/traefik/#certificate-strategy) is set.
There is no cron job to add and no expiry to diarise.

## Has no guide here

**Monitoring and alerting.** The repository ships the stacks — uptime checks,
dashboards, and the run monitoring that Borgmatic reports into — with their own
READMEs. Nothing on this site walks through them.

**Log retention beyond the proxy.** Traefik's access log has a logrotate
configuration in [preparing a server](/getting-started/server-setup/#going-further).
Application logs are bounded by the Docker daemon settings from that same page and
otherwise left alone.

## Where to go from here

- Setting up a service and wondering when to arrange the backup: before the first
  real record goes in, not after — [backup and restore](/operations/backup/)
- Reading what a guide claims has been tested:
  [the FAQ explains the evidence line](/faq/)
