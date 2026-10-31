# Upstream Reference

## Source

- **Project:** https://uptime.kuma.pet
- **GitHub:** https://github.com/louislam/uptime-kuma
- **Docker Hub:** https://hub.docker.com/r/louislam/uptime-kuma
- **License:** MIT
- **Decision facts checked:** not yet
- **Origin:** Hong Kong · Louis Lam · non-EU
- **Domain:** Monitoring
- **Role:** Uptime monitoring with a status page and many notification channels
- **Based on version:** `2.5.8`
- **Last verified:** 2026-09-13 (2.5.4) — patch recreated on a live host, healthy, route unchanged. 2026-09-08 (2.5.3) — v0.8.0 host session: clean start on SQLite, owner account from the setup page, ntfy notification with an access token, a TCP monitor on a container on `proxy-public`; stopping that container produced the down alert on an iPhone within twenty seconds, starting it the up alert.

## What we use

- Official `louislam/uptime-kuma` image
- Built-in SQLite database (stored in `./volumes/data/`)
- No external database service required
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 3001:3001`** | Blueprint routing standard |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **Healthcheck on `/api/entry-page`** | Proper readiness gate |
| **`access-vpn` default access** | Monitoring dashboards should not be public |

## Version notes

- `2.x` carries breaking changes against `1.x`. Upstream publishes a migration
  guide for an existing v1 instance:
  https://github.com/louislam/uptime-kuma/wiki/Migration-From-v1-To-v2
- Moved to `2.5.8` on 2026-10-31, not run on a host at this tag. `2.5.8` fixes
  GHSA-v2p3-6f5h-6hhf (remote code execution, admin only) and drops TLS from the
  TCP Port monitor: an existing TLS TCP monitor becomes a plain TCP monitor, with
  no migration step. `2.5.7` moves the image to Node.js 22.23.4, which distrusts
  the leaked eMudhra CA. Upstream's advisories of October 2026 —
  GHSA-98hr-q8q8-5j23 (rootless privilege escalation) and GHSA-wf2j-5mc7-5c4w
  (ping badge denial of service) — name no fixed version on the list page and
  were not read further.

## Upgrade checklist

1. Check [Uptime Kuma releases](https://github.com/louislam/uptime-kuma/releases)
2. Back up:

   ```bash
   cp -r volumes/data/ uptime-kuma-backup-$(date +%Y%m%d)/
   ```

3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Verify: monitors are active, notification channels functional

## Useful commands

```bash
# Shell into the container
docker compose exec app sh

# View SQLite DB size
docker compose exec app du -sh /app/data/kuma.db
```
