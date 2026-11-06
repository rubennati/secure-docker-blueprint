# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/portainer/portainer-ce
- **GitHub:** https://github.com/portainer/portainer
- **Docs:** https://docs.portainer.io/
- **License:** zlib
- **Edition gating:** Portainer lists role-based access control, Active Directory with automatic user sync, pre-configured SSO provider templates, and authentication and activity logs as Business Edition features — https://www.portainer.io/features · checked 2026-09-21
- **Commercial model:** paid self-hosted edition; a separate free tier for homelab, personal and learning use is offered — https://www.portainer.io/business-enterprise-it-pricing · checked 2026-09-21
- **Decision facts checked:** 2026-09-21
- **Origin:** New Zealand · Portainer.io Ltd · non-EU
- **Domain:** Infrastructure
- **Role:** Docker management web interface, reaching Docker through a filtered socket proxy
- **Based on version:** `2.45.3` (Community Edition)
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
| `tls-strict` named on the router, `access-vpn`, `limit-strict` | Admin tool, VPN-only, strict rate limiting; TLS 1.3 only, as a documented exception |

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
- Moved `portainer/portainer-ce` to `2.45.3` on 2026-11-05 (released 2026-10-21, the
  current LTS line), from the 2.39 LTS line across the STS releases 2.40 to 2.44, not
  run on a host at this tag. Breaking changes: 2.41 replaced the CSRF protection —
  entries in the trusted-origins list must be full URLs with scheme, and a browser
  request whose origin does not match gets `403 Forbidden` with `CSRF check failed` in
  the log; 2.42 removed the `legacy-csrf` fallback flag. This stack sets no trusted
  origins and Traefik passes the original `Host`, so the browser origin and the
  request host are the same; if state-changing actions return 403 after the move, that
  is where to look. 2.45.3 no longer trusts certificates issued by eMudhra (emSign)
  after the compromise of eight intermediate CAs (CVE-2026-111943): an OAuth/OIDC or
  LDAPS provider, registry or Git host presenting such a certificate fails, and only
  the initial admin can then sign in. 2.45.0 fixed another Docker proxy authorization
  bypass through unrecognised API version prefixes such as `/v1.47.0/`; 2.45.3 rejects
  `volumes_from` in stacks of non-administrators when bind mounts are hidden from
  them, restricts kubeconfig tokens to the Kubernetes proxy, and moves the Go
  toolchain to 1.26.10 (CVE-2026-56857 and CVE-2026-78663, both critical, among
  others). 2.42 ported Swarm stack deployment to libstack and removed the embedded
  Docker binary from the image; 2.43 removed the "Provision KaaS Cluster" feature,
  which this stack does not use. The database migrates on first start and is one-way:
  back up `./volumes/data/` first. No compose change; the socket proxy's permission set
  is unchanged. The agent in `core/portainer-agent/` moves to `2.45.3` in the same step.
  Sources: https://github.com/portainer/portainer/releases/tag/2.45.3,
  https://github.com/portainer/portainer/releases/tag/2.45.0,
  https://github.com/portainer/portainer/releases/tag/2.42.0,
  https://github.com/portainer/portainer/releases/tag/2.41.0
- Moved `lscr.io/linuxserver/socket-proxy` to `3.4.7` on 2026-11-05 (LinuxServer build
  `3.4.7-r0-ls104` of 2026-10-27), patch releases of the HAProxy 3.4 package it is
  built on, not run on a host at this tag. The LinuxServer builds 3.4.5 to 3.4.7 list
  no changes of their own, only the package update, so the permission variables are
  unchanged. Source: https://github.com/linuxserver/docker-socket-proxy/releases

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
