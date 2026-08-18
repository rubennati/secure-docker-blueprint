# Upstream Reference

## Source

- **Project:** https://uptime.kuma.pet
- **GitHub:** https://github.com/louislam/uptime-kuma
- **Docker Hub:** https://hub.docker.com/r/louislam/uptime-kuma
- **License:** MIT
- **Origin:** Hong Kong · Louis Lam · non-EU
- **Based on version:** `2.4.0`
- **Last checked:** 2026-08-18

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
| **`acc-tailscale` default access** | Monitoring dashboards should not be public |

## Version notes

- `2.x` carries breaking changes against `1.x`. Upstream publishes a migration
  guide for an existing v1 instance:
  https://github.com/louislam/uptime-kuma/wiki/Migration-From-v1-To-v2

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
