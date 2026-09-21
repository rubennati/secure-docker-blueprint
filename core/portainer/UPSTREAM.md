# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/portainer/portainer-ce
- **GitHub:** https://github.com/portainer/portainer
- **Docs:** https://docs.portainer.io/
- **License:** zlib
- **Edition gating:** Portainer lists role-based access control, Active Directory with automatic user sync, pre-configured SSO provider templates, and authentication and activity logs as Business Edition features — https://www.portainer.io/features · checked 2026-09-21
- **Commercial model:** paid self-hosted edition; a separate free tier for homelab, personal and learning use is offered — https://www.portainer.io/business-enterprise-it-pricing · checked 2026-09-21
- **Origin:** New Zealand · Portainer.io Ltd · non-EU
- **Domain:** Infrastructure
- **Role:** Docker management web interface, reaching Docker through a filtered socket proxy
- **Based on version:** `2.39.7` (Community Edition)
- **Last checked:** 2026-04-16

Note: this setup uses Portainer **CE** (Community Edition). Portainer Business Edition (`portainer/portainer-ee`) is a different paid product with additional features and a different license — not used here.

## What we use

- Official `portainer/portainer-ce` image, pinned tag
- `lscr.io/linuxserver/socket-proxy` as the Docker API gateway
- File-based data storage (`./volumes/data/`) — Portainer does not need an external database

## What we changed and why

| Change | Reason |
|--------|--------|
| Socket proxy (LinuxServer.io variant) instead of direct socket mount | Standard hardening pattern — Portainer never touches `/var/run/docker.sock` |
| `command: --host tcp://socket-proxy:2375` | Tells Portainer to use the proxy; it otherwise auto-detects the local socket |
| `read_only: true` + `tmpfs` on socket proxy | Defense in depth; the proxy container has no writable root filesystem |
| TLS profile `tls-modern` + `acc-tailscale` + `sec-4` | Admin tool, VPN-only, strict rate limiting |

## Why `linuxserver/socket-proxy` not `tecnativa/docker-socket-proxy`

Both are HAProxy-based socket filters. Either would work. The LinuxServer.io variant was chosen for this app because its permission set uses the same env-var names as the `ALLOW_START` / `ALLOW_STOP` / `ALLOW_RESTARTS` extensions which Portainer needs for container lifecycle operations.

If you prefer `tecnativa/docker-socket-proxy`, replace the image and consult its documentation for equivalent variable names.

## Version / tag notes

- **`2.39.5` → `2.39.7`, a patch on the same line.** CVE-2026-72533 (critical) let a
  non-canonical Docker API version prefix bypass the Docker API proxy authorization, and
  is fixed in 2.39.7. 2.39.6 upgrades the Go toolchain past CVE-2026-42505 and
  CVE-2026-39822, updates `go-git` past CVE-2026-71556, and closes a remaining gap in the
  CVE-2026-44849 fix by broadening bind-mount restrictions for non-admin users to Compose
  and Swarm stack deployments. 2.45.0 exists and is a feature release. Moved on 2026-09-13.
- `SOCKET_PROXY_TAG` moved from `3.2.15` to `3.4.4` in the same step —
  `linuxserver/socket-proxy` had two minor lines of drift and this stack's whole point is
  the filter in front of the Docker API.

## Upgrade checklist

1. Check the Portainer CE release notes: https://github.com/portainer/portainer/releases
2. Back up `./volumes/data/` — this is the complete Portainer state (users, settings, endpoints, stacks)
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Portainer auto-migrates its database on startup — watch `docker compose logs app --tail 100` for migration messages
6. Log in, confirm endpoints still work, confirm user list intact

### Rollback

Portainer's database migrations are generally one-way. To roll back: restore `./volumes/data/` from backup **and** revert `APP_TAG` to the previous version.

## Related images

- `lscr.io/linuxserver/socket-proxy` — safe to update within the same major version

## Useful commands

```bash
# Shell into Portainer container
docker compose exec app sh

# Inspect socket proxy permissions currently in effect
docker compose exec socket-proxy env | grep -E "^(CONTAINERS|SERVICES|NETWORKS|VOLUMES|IMAGES|SYSTEM|EXEC|POST|DELETE|ALLOW_)"

# Backup the Portainer data directory
tar czf portainer-backup-$(date +%Y%m%d).tgz ./volumes/data/

# Reset admin password (emergency recovery, instance must be stopped)
# Portainer CE has no built-in password reset — follow the documented procedure:
# https://docs.portainer.io/advanced/reset-admin
```
