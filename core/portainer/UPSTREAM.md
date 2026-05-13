# Upstream Reference

## Source

- **Image:** https://hub.docker.com/r/portainer/portainer-ce
- **GitHub:** https://github.com/portainer/portainer
- **Docs:** https://docs.portainer.io/
- **License:** zlib
- **Origin:** New Zealand · Portainer.io Ltd · non-EU
- **Based on version:** `2.39.1` (Community Edition)
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
