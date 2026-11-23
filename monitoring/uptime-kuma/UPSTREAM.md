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
- **Last verified:** 2026-11-08 (2.5.9) — over IPv4: the stack healthy and `/` redirecting a new instance to `/setup-database` before and after `down`/`up`, the refused client answered `403`; the setup and a monitor were not created (docs/labs/stack-refresh/2026-11-08-results.md)

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
- Moved to `2.5.8` on 2026-10-31. `2.5.8` fixes
  GHSA-v2p3-6f5h-6hhf (remote code execution, admin only) and drops TLS from the
  TCP Port monitor: an existing TLS TCP monitor becomes a plain TCP monitor, with
  no migration step. `2.5.7` moves the image to Node.js 22.23.4, which distrusts
  the leaked eMudhra CA. Upstream's advisories of October 2026 —
  GHSA-98hr-q8q8-5j23 (rootless privilege escalation) and GHSA-wf2j-5mc7-5c4w
  (ping badge denial of service) — name no fixed version on the list page and
  were not read further.
- Moved to `2.5.9` on 2026-11-05. A patch release
  with no breaking change and no migration: bug fixes (runtime timeout fallback,
  push monitor retries, status page refresh timer, recurring maintenance timezone)
  and dependency updates. It fixes GHSA-86ch-2247-gr56 (RSS cache poisoning) and
  replaces the outdated `apicache` with `http-cache-semantics` for it.
- Moved to `2.5.12` on 2026-11-23 (released 2026-11-17). Three patch releases with no
  breaking change and no migration. `2.5.10` moves the image to Node.js 22.23.5, the Node.js
  security release of November 2026 (high-severity issues upstream says could reach Uptime
  Kuma). `2.5.11` fixes GHSA-437w-j82f-9vjh, remote code execution through a regression in an
  upstream package, reachable by an admin only; upstream withholds the details and severity for
  seven days, and the advisory was not yet published on 2026-11-23. `2.5.12` sandboxes a
  library upstream calls dangerous (#8187) and updates dependencies. An instance upgraded from
  2.5.9 with an admin and two HTTP monitors keeps both: login answers and the monitor list
  returns them, the healthcheck passes and the log carries no error (local stack, 2026-11-23).
  Sources: https://github.com/louislam/uptime-kuma/releases/tag/2.5.10,
  https://github.com/louislam/uptime-kuma/releases/tag/2.5.11,
  https://github.com/louislam/uptime-kuma/releases/tag/2.5.12

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
