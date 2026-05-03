# Upstream Reference

## Source

- **Project:** https://changedetection.io
- **GitHub:** https://github.com/dgtlmoon/changedetection.io
- **Registry:** `ghcr.io/dgtlmoon/changedetection.io`
- **License:** Apache-2.0
- **Based on version:** `0.55.3`
- **Last checked:** 2026-05-03

## What we use

- Official `ghcr.io/dgtlmoon/changedetection.io` image
- Built-in datastore (JSON files in `./volumes/datastore/`)
- Optional browser/Playwright service for JavaScript-rendered pages (commented out by default)
- Traefik labels for HTTPS routing

## What we changed vs. upstream examples

| Change from upstream | Reason |
|---|---|
| **Traefik labels instead of `-p 5000:5000`** | Blueprint routing standard |
| **`security_opt: no-new-privileges:true`** | Baseline hardening |
| **`acc-tailscale` default access** | Change tracking targets may include internal services |
| **Browser service commented out** | Optional — only needed for JS-heavy sites; adds ~1 GB RAM |

## Browser / Playwright support

For sites that require JavaScript rendering (SPAs, dynamic content), uncomment the `browser` service in `docker-compose.yml`:

```yaml
browser:
  image: dgtlmoon/sockpuppetbrowser:latest
  # or use playwright:
  # image: mcr.microsoft.com/playwright:latest
```

Then set **"Request via browser steps"** in the watch settings for affected URLs.

## Upgrade checklist

1. Check [changedetection.io releases](https://github.com/dgtlmoon/changedetection.io/releases)
2. Back up:
   ```bash
   cp -r volumes/datastore/ changedetection-backup-$(date +%Y%m%d)/
   ```
3. Bump `APP_TAG` in `.env`
4. `docker compose pull && docker compose up -d`
5. Verify: existing watches are intact, notifications still fire

## Useful commands

```bash
# Shell into the container
docker compose exec app bash

# Export all watches as OPML (for backup/migration)
# Available in the UI: Settings → Export
```
