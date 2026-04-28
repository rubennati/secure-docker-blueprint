# Blueprint Architecture

This document explains the structural decisions behind the blueprint — why the directories are split the way they are, how services connect at the network level, and how the security layers stack. It is the "why" behind the "what" visible in the rest of the repo.

---

## Design Goals

- **Fork-ready**: Clone, copy `.env.example` to `.env`, fill secrets, `docker compose up -d`. No undocumented prerequisites.
- **Portable**: No host-specific assumptions beyond "Debian + Docker". Runs on a VM, a VPS, or bare metal.
- **Security-first**: Hardening is the default. Relaxing a control requires a documented exception.
- **Standards-consistent**: Every service follows the same compose structure, env layout, secrets pattern, and naming convention. A new app that follows the standards fits in without friction.

---

## Directory Structure

Five top-level categories, split by **how** each tool accesses the system — not by who uses it:

| Directory | Responsibility | Access pattern |
|---|---|---|
| `core/` | Infrastructure every other service depends on | Privileged — manages other containers, network, TLS |
| `apps/` | User-facing applications | Standard — Traefik-routed, DB + volume access |
| `business/` | Business operations tools | Standard — same pattern as `apps/`, distinct operational scope |
| `monitoring/` | Observability and alerting | Cross-stack — reads metrics and logs from other containers |
| `backup/` | Data protection | Privileged — reads volumes across services, writes to remote targets |

`monitoring/` and `backup/` are top-level (not under `apps/`) because their access patterns are fundamentally different: they reach across service boundaries and need broader permissions than a typical user-facing app.

---

## Networking Model

Every multi-service app uses a **hub-and-spoke** network layout. Two Docker networks per app, with a strict separation of concerns:

```
Internet
    │
    ▼
 Traefik ──── proxy-public (shared, external: true) ────► App server (web-facing)
                                                                │
                                                         app-internal (isolated, internal: true)
                                                                │
                                               DB · Redis · Workers · internal services
```

**`proxy-public`** — shared across all apps. Only Traefik and each app's web-facing service join this network. Traefik routes inbound requests to the right container.

**`app-internal`** — one per app, `internal: true`. DB, Redis, workers. Completely isolated: no route to the internet, no route between apps. A compromised app cannot reach another app's database.

Databases and caches **never** join `proxy-public`. They have no exposure beyond their own app stack.

---

## Security Layers

Inbound traffic passes through four independent, additive layers before reaching an application:

```
Request
    │
    ▼
[1] Traefik          TLS termination, security header chains (sec-0…sec-5),
                     rate limiting, access policies (public / local / Tailscale / private / deny)
    │
    ▼
[2] CrowdSec         Threat intelligence, IP reputation, L7 WAF via Traefik bouncer plugin.
                     Bans propagate in real time from the LAPI to the bouncer.
    │
    ▼
[3] Authentik        Forward-Auth middleware for apps that require SSO.
                     Optional per router — not every app needs it.
    │
    ▼
[4] Container        no-new-privileges, cap_drop: ALL, internal network isolation,
                     read-only root filesystem where the image supports it.
```

Each layer is independent. CrowdSec works without Authentik. Authentik works without CrowdSec. Container hardening applies regardless of what sits in front.

---

## Core Services and Their Roles

| Service | Role | Why it is in `core/` |
|---|---|---|
| Traefik | Reverse proxy, TLS termination, routing | Every app depends on it for external access |
| Socket Proxy | Mediates Docker socket access for Traefik | Required by Traefik and any management tool that needs container metadata |
| CrowdSec | Threat detection engine + L7 bouncer | Cross-stack security — analyzes logs from all services |
| Authentik | SSO / Identity Provider | Forward-Auth middleware reused by multiple apps |
| OnlyOffice | Collaborative document editing server | Embedded in Nextcloud and Seafile via iframe |

---

## Per-App Structure

Every app follows the same directory layout regardless of category:

```
<category>/<app>/
├── docker-compose.yml   # hardened, standards-aligned
├── .env.example         # all variables documented inline, no real values
├── .gitignore           # volumes/, .secrets/, .env
├── README.md            # setup steps, verify commands, architecture notes
├── UPSTREAM.md          # upstream image, changelog link, license
├── .secrets/            # gitignored — generated locally per install
└── volumes/             # gitignored — persistent application data
```

**Config lives in Git. Secrets and data never do.**

The compose file and `.env.example` are the portable artifact. The `.env`, `.secrets/`, and `volumes/` are per-installation and stay on the host.

---

## Backup Design Principle

Backup is cross-cutting by nature — it reads from every data-producing service. The blueprint's approach:

- Each app gets its **own isolated backup repository** (Borgmatic or Kopia), not a shared monorepo.
- Retention policies are set **per app** — a database may need daily backups with 90-day retention, a static site weekly with 30 days.
- Restore is **surgical** — recovering one app does not touch another app's backup chain.
- A compromised backup target for one app does not expose all apps.

See [`backup/README.md`](../backup/README.md) for tool choices and the picking matrix.
