# Upstream Reference

## Source

- **Project:** https://uptime.kuma.pet
- **GitHub:** https://github.com/louislam/uptime-kuma
- **Docker Hub:** https://hub.docker.com/r/louislam/uptime-kuma
- **License:** MIT
- **Origin:** Hong Kong · Louis Lam · non-EU
- **Based on version:** `1.23.17`
- **Last checked:** 2026-05-03

## What we use

- Official `louislam/uptime-kuma` image (v1 stable — v2 is in beta as of 2026-05)
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

- v1 (current): stable, feature-complete, `1.23.x` is the latest stable branch
- v2 (beta as of 2026-05): full rewrite with multi-user support — wait for stable before upgrading
- Upgrading from v1 to v2 will require data migration

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
