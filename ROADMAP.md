# Roadmap

## In Progress

### CrowdSec – Intrusion Detection & Prevention

Three-phase security setup for the entire stack:

| Phase | Component | Status |
|-------|-----------|--------|
| Phase 1 | Security Engine (`core/crowdsec/`) | **Done** — standalone detection |
| Phase 2 | Traefik Bouncer Plugin | Planned — requires Traefik changes |
| Phase 3 | Firewall Bouncer (host nftables) | Planned — host-level install |

**Architecture:**
```
Internet
   ↓
Traefik + CrowdSec Plugin    ← Phase 2: HTTP enforcement
   ↓
Docker Services
   ↓
Host nftables                 ← Phase 3: IP-level enforcement
   ↓
CrowdSec Engine               ← Phase 1: Detection (logs → decisions)
```

**Phase 2 (next)** requires:
- CrowdSec plugin in Traefik static config (experimental section)
- CrowdSec middleware in Traefik dynamic config
- Bouncer API key from the engine
- Traefik access logs in JSON format

**Phase 3** requires:
- `crowdsec-firewall-bouncer-nftables` apt package on host
- Bouncer API key from the engine
- Not a Docker container — documentation only in the blueprint

---

## Evaluating

### Admin Path Protection via Traefik

Restrict admin/backend URLs to specific access policies while keeping the public frontend open. Uses Traefik's `PathPrefix` routing with separate middleware chains.

**Examples:**
- WordPress `/wp-admin` and `/wp-login.php` → `acc-tailscale` or Authentik Forward-Auth
- Paperless entire UI → `acc-tailscale` (already internal-only)
- Ghost `/ghost` admin panel → `acc-tailscale`

**Approach:** Two Traefik routers per app — one for public paths (`acc-public`, `sec-2`) and one for admin paths (`acc-tailscale`, `sec-4` or Authentik Forward-Auth). Configurable via `.env` variables.

### Mutual TLS (mTLS) – Certificate-Based Access

Client certificate authentication as an additional access layer. Only devices with a trusted client certificate can connect — stronger than IP allowlists or passwords.

**Use cases:**
- API endpoints that only specific servers should reach
- Admin panels with hardware-bound authentication
- Zero-trust access without VPN dependency

**Approach:** Traefik TLS option with `clientAuth` requiring certificates signed by a custom CA. The `core/acme-certs` tool could be extended to also generate client certificates.

### Backup Strategy – Multi-Layer with Verification

Comprehensive backup concept covering all levels of the stack, with automated restore testing.

**Layer 1: Host-level**
- Full system backup (configs, Docker data, secrets)
- Scheduled via restic, borgbackup, or similar
- Offsite target (S3, Backblaze B2, NFS)

**Layer 2: App-level**
- Per-app backup scripts in each app directory (`ops/scripts/backup.sh`)
- Consistent snapshots: stop app → dump → backup → start
- Standardized output to `./volumes/backups/`

**Layer 3: Database-level**
- Automated `pg_dump` / `mysqldump` via sidecar or cron container
- Point-in-time recovery where supported
- Encrypted dumps stored alongside app backups

**Layer 4: Verification**
- Automated restore tests on a schedule (spin up temp containers, restore, verify)
- Checksums and integrity validation
- Alerting on failed backups or missed schedules

**Open questions:**
- Single backup tool (restic?) or per-layer tools?
- Central backup service in `core/` or per-app scripts?
- How to handle secrets backup securely (encrypted, separate from data)?

### IPv6 – Dual-Stack and IPv6-Only Setups

Full IPv6 support across the stack, including IPv6-only deployments.

**Scope:**
- Docker network configuration for dual-stack (IPv4 + IPv6) and IPv6-only
- Traefik entrypoints and routing with IPv6
- Firewall rules (nftables) covering both protocols
- DNS (dnsmasq) with AAAA records
- CrowdSec compatibility with IPv6 decisions
- Per-app testing for IPv6-only operation

**Open questions:**
- Which apps have known IPv6 issues?
- Docker's native IPv6 support maturity (enable in `daemon.json`?)
- NAT64/DNS64 needed for IPv6-only connecting to IPv4 services?

### Container Resource Management

Define a resource limiting strategy to prevent any single container from taking down the host.

**Scope:**
- CPU limits and reservations (`deploy.resources.limits.cpus`)
- Memory limits and reservations (`deploy.resources.limits.memory`)
- PIDs limit (prevent fork bombs)
- Temporary storage limits (`tmpfs` size)
- I/O throttling (`blkio` limits for disk-heavy services like databases)

**Approach to define:**
- Sensible defaults per service category (database, web app, cache, worker)
- Hardware-aware profiles (small/medium/large) or percentage-based?
- Commented examples in each compose file vs. central reference table?
- Monitoring integration — how to find the right values (observe first, then limit)?

**Goal:** No single container can consume 100% CPU or RAM. OOM-killer targets the container, not the host.

### Docker Rootless Mode

Evaluate running Docker in rootless mode for improved host security — the Docker daemon and all containers run without root privileges.

**Current state:**
- Docker rootless is functional but has known limitations
- Not all images/apps work correctly (volume permissions, port binding < 1024, network modes)
- Some of our patterns may need adjustment (socket proxy, `network_mode: host`)

**Evaluation goals:**
- Test each app in the blueprint for rootless compatibility
- Document which apps work, which need workarounds, which don't work
- Provide a rootless setup guide alongside the standard setup
- Decide: optional alternative or future default?

---

## Ideas

### Alternative Container Runtimes

Evaluate alternative runtimes and orchestrators beyond standard Docker:

- **Podman** — Daemonless, rootless by default, Docker CLI compatible. Could replace Docker entirely. How well does it work with Traefik, Compose, and our socket proxy pattern?
- **Docker Swarm** — Built-in orchestration for multi-node setups. Adds service discovery, rolling updates, and secrets management. Relevant when scaling beyond a single host.
- **Kubernetes (K8s / K3s)** — Full container orchestration. K3s as lightweight option for homelab. Major architectural shift — Helm charts instead of Compose files. Only makes sense at significant scale or for learning.

_These are long-term considerations. The current Docker Compose approach covers single-host and small-scale deployments well._
